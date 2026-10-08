"""
This script feeds the COG (optimized) layer meta data to the database.
"""
import os
import psycopg2
import subprocess
import json
import rasterio
from pathlib import Path

from raster_utils import compute_band_range, generate_band_vrts, parse_band_date_convention, prepare_multiband_source

# ── Paths (work inside container AND on host, Windows or Linux) ──────────────
# Script lives at:  data/register_layers.py
# Container maps:   ./data → /app
# So:  __file__ parent = "data/" on host, "/app" in container — same structure.

_SCRIPT_DIR = Path(__file__).resolve().parent   # data/  (host) or /app/ (container)
# _SCRIPT_DIR = Path(os.getcwd()).resolve()

RASTER_DIR        = _SCRIPT_DIR / "data_files" / "Raster"
OPTIMIZED_DIR     = _SCRIPT_DIR / "data_files" / "Optimized_Raster"
UNCATEGORIZED     = "Uncategorized"

# Path as seen by the raster-server container (its volume mount is also ./data → /data)
def raster_server_path(rel_path: Path) -> str:
    return f"/data/data_files/Optimized_Raster/{rel_path.as_posix()}"


def relative_to_raster(tif: Path) -> Path:
    """Path of a raster relative to RASTER_DIR, e.g. 'aspect/foo.tif'.
    Files sitting directly in RASTER_DIR (no category folder) are bucketed
    under UNCATEGORIZED so every registered layer still has a category."""
    rel = tif.relative_to(RASTER_DIR)
    if len(rel.parts) == 1:
        return Path(UNCATEGORIZED) / rel
    return rel

# ── DB connection ─────────────────────────────────────────────────────────────
DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise ValueError("DATABASE_URL environment variable is not set")


def get_raster_metadata(file_path: Path):
    """Uses gdalinfo CLI to extract the WGS84 bounding box."""
    try:
        result = subprocess.run(
            ["gdalinfo", "-json", str(file_path)],
            capture_output=True, text=True, check=True
        )
        info = json.loads(result.stdout)

        extent = info.get("wgs84Extent", {}).get("coordinates", [[]])[0]
        if not extent:
            return None

        poly_str = ", ".join([f"{c[0]} {c[1]}" for c in extent])
        return {"bbox": f"POLYGON(({poly_str}))"}

    except Exception as e:
        print(f"❌ Error parsing {file_path.name}: {e}")
        return None


def optimize_to_cog(src: Path, dst: Path, force: bool = False) -> bool:
    """Convert a GeoTIFF to an optimized, tiled GeoTIFF using gdal_translate.

    Multi-band sources (e.g. a daily time series for a year) get a synthetic
    "mean" band prepended, then every original band is preserved after it —
    TiTiler's `bidx` tile parameter lets the frontend pick whichever one it
    wants. A raster that already has a single band passes through unchanged.

    Single-band output uses GDAL's COG driver as before. Multi-band output
    deliberately does NOT use the COG driver: that driver hardcodes
    INTERLEAVE=PIXEL, which stores every band's value for a pixel together —
    so reading just one band out of a 366-band file still means decompressing
    all 366 bands' worth of data per tile (measured ~1.3-1.5s per tile,
    enough to make the map feel hung). Instead, multi-band output is built as
    a classic tiled GeoTIFF with INTERLEAVE=BAND (each band fully separable
    on disk) plus `gdaladdo` for overviews — functionally equivalent to a COG
    for TiTiler's purposes, but ~7-10x faster for single-band reads out of a
    many-band file (measured ~0.15-0.2s per tile after this change).

    If `force` is True, an existing `dst` is deleted and rebuilt instead of
    being skipped — used to regenerate files produced by an older version of
    this pipeline (e.g. the old single-band-only squash, or the PIXEL-
    interleaved multi-band COG from before this fix).
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        if not force:
            print(f"  ↳ Already optimized, skipping conversion: {dst.name}")
            return True
        dst.unlink()

    mean_tmp = dst.parent / f"_{dst.stem}.band_mean_tmp.tif"
    try:
        conversion_src = prepare_multiband_source(src, mean_tmp)
    except Exception as e:
        print(f"❌ Could not read {src.name}, skipping: {e}")
        return False

    is_multiband = conversion_src == mean_tmp

    try:
        if is_multiband:
            subprocess.run([
                "gdal_translate",
                "-of", "GTiff",
                "-co", "TILED=YES",
                "-co", "BLOCKXSIZE=512",
                "-co", "BLOCKYSIZE=512",
                "-co", "INTERLEAVE=BAND",
                "-co", "COMPRESS=DEFLATE",
                str(conversion_src), str(dst)
            ], check=True, capture_output=True)
            subprocess.run([
                "gdaladdo", "-r", "average", str(dst), "2", "4", "8"
            ], check=True, capture_output=True)
        else:
            subprocess.run([
                "gdal_translate",
                "-of", "COG",
                "-co", "COMPRESS=DEFLATE",
                "-co", "OVERVIEW_RESAMPLING=AVERAGE",
                str(conversion_src), str(dst)
            ], check=True, capture_output=True)

        print(f"  ↳ Optimized → {dst.name}")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ COG conversion failed for {src.name}: {e.stderr}")
        return False
    finally:
        if conversion_src == mean_tmp and mean_tmp.exists():
            mean_tmp.unlink()


def _is_stale_timeseries_output(src: Path, optimized: Path) -> bool:
    """True if an already-optimized file needs rebuilding because `src` is a
    genuine multi-band (time-series) source but `optimized` doesn't reflect
    the current pipeline shape — either it's still the old single-mean-band
    squash (band count doesn't match src's real band count + 1), or it's
    multi-band but still PIXEL-interleaved (the COG driver's hardcoded
    layout, which makes reading one band out of many require decompressing
    all of them — see optimize_to_cog's docstring).

    Single-band sources are NEVER flagged here: an optimized single-band
    file's band count (1) is indistinguishable from the old pre-feature
    squash output on its own, so staleness only makes sense relative to the
    source's own band count, not the optimized file in isolation.
    """
    if not optimized.exists():
        return False
    try:
        with rasterio.open(src) as src_ds:
            src_band_count = src_ds.count
        if src_band_count <= 1:
            return False  # static raster — never subject to the time-series shape
        with rasterio.open(optimized) as ds:
            if ds.count != src_band_count + 1:
                return True
            return ds.tags(ns="IMAGE_STRUCTURE").get("INTERLEAVE") != "BAND"
    except Exception:
        return True


def register_rasters():
    tifs = list(RASTER_DIR.rglob("*.tif"))
    if not tifs:
        print(f"⚠️  No .tif files found in {RASTER_DIR}")
        return

    print(f"📂 Found {len(tifs)} rasters in Raster/ folder (across all category subfolders)")
    print(f"   Source:      {RASTER_DIR}")
    print(f"   Destination: {OPTIMIZED_DIR}\n")

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    success, skipped = 0, 0

    for tif in tifs:
        rel_path  = relative_to_raster(tif)
        category  = rel_path.parts[0]
        optimized = OPTIMIZED_DIR / rel_path
        print(f"▶ Processing: {rel_path}")

        # Step 1: Convert to COG into Optimized_Raster/<category>/. Source
        # rasters with more than one real band are only ever squashed to the
        # old single/mean-only shape by an earlier version of this pipeline —
        # force a rebuild so they get the full band stack instead. Single-band
        # sources are never flagged, so aspect/etc. are left alone (fast).
        force_rebuild = _is_stale_timeseries_output(tif, optimized)
        if not optimize_to_cog(tif, optimized, force=force_rebuild):
            skipped += 1
            continue

        # Step 2: Extract metadata from the optimized file
        meta = get_raster_metadata(optimized)
        if not meta:
            print(f"⚠️  Skipping {rel_path}: no spatial metadata found.")
            skipped += 1
            continue

        # Step 2b: Real (nodata-excluded) value range across all bands, used
        # for the frontend's per-layer TiTiler rescale instead of a
        # one-size-fits-all default. Scanning every band keeps the color
        # scale stable as a user scrubs between timesteps.
        value_range = compute_band_range(optimized)
        min_value, max_value = value_range if value_range else (None, None)

        # Step 2c: Band/time metadata. Band 1 is the synthetic "mean" band
        # (count > 1) or the only band (count == 1) — never has a parseable
        # date. Bands 2..N are the real timesteps, whose descriptions are
        # checked against the `<var>_<year>_<day-of-year>` convention.
        with rasterio.open(optimized) as ds:
            band_count = ds.count
            descriptions = ds.descriptions
        if band_count > 1:
            band_start_date, band_date_step_days = parse_band_date_convention(list(descriptions[1:]))
        else:
            band_start_date, band_date_step_days = None, None

        # Step 2d: One single-band VRT per band, so the frontend's time
        # slider can request a day's tile without TiTiler warping all
        # `band_count` bands just to serve one — see docs/vrt_explainer.md.
        # No-op for single-band layers; cheap no-op for already-fresh VRTs.
        generate_band_vrts(optimized, band_count)

        # Step 3: Register in database
        # slug is prefixed with category so identically-named files in
        # different category folders don't collide on the UNIQUE slug column.
        slug         = f"{category}_{tif.stem}".lower()
        display_name = tif.stem.replace("_", " ").title()
        server_path  = raster_server_path(rel_path)

        query = """
            INSERT INTO layer_metadata (
                slug, display_name, category, layer_type, file_path, bbox,
                min_value, max_value, band_count, band_start_date, band_date_step_days
            )
            VALUES (%s, %s, %s, %s, %s, ST_GeomFromText(%s, 4326), %s, %s, %s, %s, %s)
            ON CONFLICT (slug) DO UPDATE SET
                category             = EXCLUDED.category,
                file_path            = EXCLUDED.file_path,
                bbox                 = EXCLUDED.bbox,
                min_value            = EXCLUDED.min_value,
                max_value            = EXCLUDED.max_value,
                band_count           = EXCLUDED.band_count,
                band_start_date      = EXCLUDED.band_start_date,
                band_date_step_days  = EXCLUDED.band_date_step_days;
        """
        cur.execute(query, (
            slug, display_name, category, "raster", server_path, meta["bbox"],
            min_value, max_value, band_count, band_start_date, band_date_step_days,
        ))
        print(f"✅ Registered: {slug} (category: {category}, range: {min_value}..{max_value}, "
              f"bands: {band_count}, start: {band_start_date}, step_days: {band_date_step_days})")
        success += 1

    conn.commit()
    cur.close()
    conn.close()

    print(f"\n🚀 Done! {success} registered, {skipped} skipped.")


if __name__ == "__main__":
    register_rasters()

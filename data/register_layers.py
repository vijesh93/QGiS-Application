"""
This script feeds the COG (optimized) layer meta data to the database.
"""
import os
import psycopg2
import subprocess
import json
import rasterio
from pathlib import Path

from raster_utils import compute_band_range, generate_band_vrts, is_stale_timeseries_output, parse_band_date_convention

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

        # Step 1: Verify this raster is already properly optimized —
        # registration never does conversion work itself (that's
        # cog_optimizer.py's job, via raster_utils.optimize_to_cog). A file
        # that's missing or stale gets skipped, not silently (re)built here:
        # doing the conversion inline used to make `register_layers.py`
        # redo the heaviest part of the pipeline on every run (and, on
        # memory-constrained machines, was a real cause of it getting
        # OOM-killed) — and registering an unoptimized/stale raster's
        # metadata would be actively wrong (e.g. a `bidx`/VRT band layout
        # that doesn't match what's actually on disk).
        if not optimized.exists():
            print(f"⚠️  Skipping {rel_path}: not optimized yet — run the optimize "
                  f"step first (cog_optimizer.py, or setup_layers.py without --skip-optimize).")
            skipped += 1
            continue
        if is_stale_timeseries_output(tif, optimized):
            print(f"⚠️  Skipping {rel_path}: optimized file is stale (doesn't match "
                  f"the source's band layout) — re-run the optimize step.")
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

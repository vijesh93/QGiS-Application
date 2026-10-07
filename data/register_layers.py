"""
This script feeds the COG (optimized) layer meta data to the database.
"""
import os
import psycopg2
import subprocess
import json
from pathlib import Path

from raster_utils import compute_band_range, prepare_single_band_source

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


def optimize_to_cog(src: Path, dst: Path) -> bool:
    """Convert a GeoTIFF to Cloud Optimized GeoTIFF using gdal_translate.

    Multi-band sources (e.g. a daily time series for a year) are collapsed
    to a single band (annual mean) first, since TiTiler/the frontend expect
    one band per registered layer. A raster that already has a single band
    passes through unchanged.
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        print(f"  ↳ Already optimized, skipping conversion: {dst.name}")
        return True

    mean_tmp = dst.parent / f"_{dst.stem}.band_mean_tmp.tif"
    try:
        conversion_src = prepare_single_band_source(src, mean_tmp)
    except Exception as e:
        print(f"❌ Could not read {src.name}, skipping: {e}")
        return False

    try:
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

        # Step 1: Convert to COG into Optimized_Raster/<category>/
        if not optimize_to_cog(tif, optimized):
            skipped += 1
            continue

        # Step 2: Extract metadata from the optimized file
        meta = get_raster_metadata(optimized)
        if not meta:
            print(f"⚠️  Skipping {rel_path}: no spatial metadata found.")
            skipped += 1
            continue

        # Step 2b: Real (nodata-excluded) value range, used for the frontend's
        # per-layer TiTiler rescale instead of a one-size-fits-all default.
        value_range = compute_band_range(optimized)
        min_value, max_value = value_range if value_range else (None, None)

        # Step 3: Register in database
        # slug is prefixed with category so identically-named files in
        # different category folders don't collide on the UNIQUE slug column.
        slug         = f"{category}_{tif.stem}".lower()
        display_name = tif.stem.replace("_", " ").title()
        server_path  = raster_server_path(rel_path)

        query = """
            INSERT INTO layer_metadata (slug, display_name, category, layer_type, file_path, bbox, min_value, max_value)
            VALUES (%s, %s, %s, %s, %s, ST_GeomFromText(%s, 4326), %s, %s)
            ON CONFLICT (slug) DO UPDATE SET
                category  = EXCLUDED.category,
                file_path = EXCLUDED.file_path,
                bbox      = EXCLUDED.bbox,
                min_value = EXCLUDED.min_value,
                max_value = EXCLUDED.max_value;
        """
        cur.execute(query, (slug, display_name, category, "raster", server_path, meta["bbox"], min_value, max_value))
        print(f"✅ Registered: {slug} (category: {category}, range: {min_value}..{max_value})")
        success += 1

    conn.commit()
    cur.close()
    conn.close()

    print(f"\n🚀 Done! {success} registered, {skipped} skipped.")


if __name__ == "__main__":
    register_rasters()

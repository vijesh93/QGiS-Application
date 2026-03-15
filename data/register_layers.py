"""
This script feeds the COG (optimized) layer meta data to the database.
"""
import os
import psycopg2
import subprocess
import json
from pathlib import Path

# ── Paths (work inside container AND on host, Windows or Linux) ──────────────
# Script lives at:  data/register_layers.py
# Container maps:   ./data → /app
# So:  __file__ parent = "data/" on host, "/app" in container — same structure.

_SCRIPT_DIR = Path(__file__).resolve().parent   # data/  (host) or /app/ (container)
RASTER_DIR        = _SCRIPT_DIR / "data_files" / "Raster"
OPTIMIZED_DIR     = _SCRIPT_DIR / "data_files" / "Optimized_Raster"

# Path as seen by the raster-server container (its volume mount is also ./data → /data)
def raster_server_path(filename: str) -> str:
    return f"/data/data_files/Optimized_Raster/{filename}"

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
    """Convert a GeoTIFF to Cloud Optimized GeoTIFF using gdal_translate."""
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            print(f"  ↳ Already optimized, skipping conversion: {dst.name}")
            return True

        subprocess.run([
            "gdal_translate",
            "-of", "COG",
            "-co", "COMPRESS=DEFLATE",
            "-co", "OVERVIEW_RESAMPLING=AVERAGE",
            str(src), str(dst)
        ], check=True, capture_output=True)

        print(f"  ↳ Optimized → {dst.name}")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ COG conversion failed for {src.name}: {e.stderr}")
        return False


def register_rasters():
    tifs = list(RASTER_DIR.glob("*.tif"))
    if not tifs:
        print(f"⚠️  No .tif files found in {RASTER_DIR}")
        return

    print(f"📂 Found {len(tifs)} rasters in Raster/ folder")
    print(f"   Source:      {RASTER_DIR}")
    print(f"   Destination: {OPTIMIZED_DIR}\n")

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    success, skipped = 0, 0

    for tif in tifs:
        optimized = OPTIMIZED_DIR / tif.name
        print(f"▶ Processing: {tif.name}")

        # Step 1: Convert to COG into Optimized_Raster/
        if not optimize_to_cog(tif, optimized):
            skipped += 1
            continue

        # Step 2: Extract metadata from the optimized file
        meta = get_raster_metadata(optimized)
        if not meta:
            print(f"⚠️  Skipping {tif.name}: no spatial metadata found.")
            skipped += 1
            continue

        # Step 3: Register in database
        slug         = tif.stem
        display_name = slug.replace("_", " ").title()
        category = slug.split('_')[0]
        server_path  = raster_server_path(tif.name)

        query = """
            INSERT INTO layer_metadata (slug, display_name, category, layer_type, file_path, bbox)
            VALUES (%s, %s, %s, %s, %s, ST_GeomFromText(%s, 4326))
            ON CONFLICT (slug) DO UPDATE SET
                file_path = EXCLUDED.file_path,
                bbox      = EXCLUDED.bbox;
        """
        cur.execute(query, (slug, display_name, category, "raster", server_path, meta["bbox"]))
        print(f"✅ Registered: {slug}")
        success += 1

    conn.commit()
    cur.close()
    conn.close()

    print(f"\n🚀 Done! {success} registered, {skipped} skipped.")


if __name__ == "__main__":
    register_rasters()

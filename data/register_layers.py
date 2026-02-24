"""
This script feeds the COG (optimized) layer meta data to the database.
"""
import os
import psycopg2
import subprocess
import json
from pathlib import Path


# Get DB connection from environment
DB_URL = os.getenv("DATABASE_URL")
RASTER_DIR = Path("/app/data_files/Optimized_Raster")


def get_raster_metadata(file_path):
    """Uses gdalinfo CLI to get the BBOX and metadata."""
    try:
        # Call gdalinfo and get JSON output
        cmd = ["gdalinfo", "-json", str(file_path)]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        info = json.loads(result.stdout)
        
        # Extract BBOX from wgs84Extent
        # TiTiler and Mapbox love WGS84 (EPSG:4326)
        extent = info.get("wgs84Extent", {}).get("coordinates", [[]])[0]
        if not extent:
            return None
        
        # Format for PostGIS ST_GeomFromText
        # Coordinates in extent are usually [lon, lat]
        poly_str = ", ".join([f"{c[0]} {c[1]}" for c in extent])
        bbox_wkt = f"POLYGON(({poly_str}))"
        
        return {"bbox": bbox_wkt}
    except Exception as e:
        print(f"❌ Error parsing {file_path.name}: {e}")
        return None


def register_rasters():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    tifs = list(RASTER_DIR.glob("*.tif"))
    print(f"📂 Found {len(tifs)} rasters to register...")

    for tif in tifs:
        slug = tif.stem
        display_name = slug.replace('_', ' ').title()
        # Path as seen by the RASTER-SERVER container
        raster_server_path = f"/data/data_files/Optimized_Raster/{tif.name}"
        
        meta = get_raster_metadata(tif)
        if not meta:
            print(f"⚠️ Skipping {tif.name}: No spatial metadata found.")
            continue

        query = """
            INSERT INTO layer_metadata (slug, display_name, category, layer_type, file_path, bbox)
            VALUES (%s, %s, %s, %s, %s, ST_GeomFromText(%s, 4326))
            ON CONFLICT (slug) DO UPDATE SET 
                file_path = EXCLUDED.file_path,
                bbox = EXCLUDED.bbox;
        """
        cur.execute(query, (slug, display_name, 'Environment', 'raster', raster_server_path, meta['bbox']))
        print(f"✅ Registered: {slug}")

    conn.commit()
    cur.close()
    conn.close()
    print("\n🚀 Database population complete!")


if __name__ == "__main__":
    register_rasters()

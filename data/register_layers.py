import os
import psycopg2
from pathlib import Path


# Use the environment variables Docker already provides
DB_URL = os.getenv("DATABASE_URL")
RASTER_DIR = Path("/app/data_files/Optimized_Raster")


def register_rasters():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    tifs = list(RASTER_DIR.glob("*.tif"))
    print(f"📂 Found {len(tifs)} rasters to register...")

    for tif in tifs:
        slug = tif.stem  # filename without .tif
        # Logic to make display name prettier (e.g., aspectcosine_1KM -> Aspect Cosine 1KM)
        display_name = slug.replace('_', ' ').title()
        
        # We point TiTiler to the path INSIDE the raster-server container
        internal_path = f"/data/data_files/Optimized_Raster/{tif.name}"

        query = """
            INSERT INTO layer_metadata (slug, display_name, category, layer_type, file_path)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (slug) DO NOTHING;
        """
        cur.execute(query, (slug, display_name, 'Elevation', 'raster', internal_path))

    conn.commit()
    cur.close()
    conn.close()
    print("✅ Database populated!")


if __name__ == "__main__":
    register_rasters()

import rasterio
from sqlalchemy import create_engine, text
from pathlib import Path


# Use the path where the OPTIMIZED files live
OPTIMIZED_DIR = Path("/app/data_files/Optimized_Raster")
DB_URL = os.getenv("DATABASE_URL")
engine = create_engine(DB_URL)


def register_layer(file_path: Path):
    """Only extracts metadata and saves to DB."""
    with rasterio.open(file_path) as src:
        bounds = src.bounds
        srid = src.crs.to_epsg() or 4326
        name = file_path.stem.lower() # No more 'optimized_' prefix to strip
        
        # TiTiler path: how the raster-server container sees the file
        # If TiTiler maps ./data to /data, the path is:
        internal_path = f"/data/data_files/Optimized_Raster/{file_path.name}"

        query = text("""
            INSERT INTO layer_metadata 
            (name, display_name, category, file_path, geometry_type, srid, 
             bbox_xmin, bbox_ymin, bbox_xmax, bbox_ymax)
            VALUES 
            (:name, :display, :cat, :path, 'RASTER', :srid, :x1, :y1, :x2, :y2)
            ON CONFLICT (name) DO UPDATE SET file_path = EXCLUDED.file_path;
        """)

        with engine.connect() as conn:
            conn.execute(query, {
                "name": name,
                "display": name.replace("_", " ").title(),
                "cat": "Optimized Raster",
                "path": internal_path,
                "srid": srid,
                "x1": bounds.left, "y1": bounds.bottom,
                "x2": bounds.right, "y2": bounds.top
            })
            conn.commit()
    print(f"🚀 Registered {name} in database.")


if __name__ == "__main__":
    tiffs = list(OPTIMIZED_DIR.glob("*.tif"))
    print(f"📂 Scanning {len(tiffs)} optimized files for database registration...")
    for tiff in tiffs:
        try:
            register_layer(tiff)
        except Exception as e:
            print(f"❌ Error registering {tiff.name}: {e}")
            
import os
import rasterio
from sqlalchemy import create_url, create_engine, text
from rio_cogeo.cogeo import cog_validate, cog_translate
from rio_cogeo.profiles import cog_profiles
from pathlib import Path


# Database connection
DB_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@db:5432/geoportal")
engine = create_engine(DB_URL)


def process_to_cog(input_path: Path) -> Path:
    """Ensures the TIFF is optimized for web streaming."""
    output_path = input_path.parent / f"optimized_{input_path.name}"
    
    # Check if already a COG to save time
    is_valid, _, _ = cog_validate(str(input_path))
    
    if is_valid:
        print(f"✅ {input_path.name} is already optimized.")
        return input_path
    
    print(f"⚙️ Optimizing {input_path.name} to COG...")
    output_profile = cog_profiles.get("deflate")
    cog_translate(
        input_path,
        output_path,
        output_profile,
        quiet=True
    )
    return output_path


def register_layer(file_path: Path):
    """Extracts metadata and saves to layer_metadata table."""
    with rasterio.open(file_path) as src:
        bounds = src.bounds
        srid = src.crs.to_epsg() or 4326
        name = file_path.stem.replace("optimized_", "").lower()
        
        # Use relative path for the container-to-container communication
        # Note: TiTiler sees files at /app/data/ inside its own container
        internal_path = f"/app/data/{file_path.name}"

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
                "cat": "Uncategorized",
                "path": internal_path,
                "srid": srid,
                "x1": bounds.left, "y1": bounds.bottom,
                "x2": bounds.right, "y2": bounds.top
            })
            conn.commit()
    print(f"🚀 Registered {name} in database.")


if __name__ == "__main__":
    # Scan the directory
    data_folder = Path("./Example_download")
    tiffs = list(data_folder.glob("*.tif"))
    
    for tiff in tiffs:
        if "optimized_" in tiff.name: continue # Skip already processed
        try:
            opt_path = process_to_cog(tiff)
            register_layer(opt_path)
        except Exception as e:
            print(f"❌ Error processing {tiff.name}: {e}")
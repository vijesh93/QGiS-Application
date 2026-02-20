import json
import psycopg2
from sqlalchemy import create_engine
import geopandas as gpd # You'll need to add 'geopandas' to requirements.txt


# Database connection string
# Note: Use 'localhost' if running from Windows, 'db' if running inside Docker
DB_URL = "postgresql://admin:password@localhost:5432/geoportal"

def import_geojson(file_path):
    # Read the data using GeoPandas
    df = gpd.read_file(file_path)
    
    # Ensure it's in the right coordinate system (WGS84)
    df = df.to_crs(epsg=4326)
    
    # Create SQLAlchemy engine
    engine = create_engine(DB_URL)
    
    # Upload to PostGIS
    # 'if_exists=replace' will create the table for you automatically!
    df.to_postgis("nature_reserves_bw", engine, if_exists='replace', index=False)
    print("Successfully imported nature reserves to PostGIS!")

if __name__ == "__main__":
    import_geojson("nature_reserves.json")
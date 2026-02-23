import requests
import os
from pathlib import Path

# Configuration
TITILER_ENDPOINT = "http://raster-server:80/cog/validate"
# The path as seen by the HOST (for the script to find files)
DATA_DIR_HOST = Path("data_files/Optimized_Raster")
# The path as seen by the CONTAINER (for TiTiler to access them)
DATA_DIR_CONTAINER = "/data/data_files/Optimized_Raster"


def check_rasters():
    if not DATA_DIR_HOST.exists():
        print(f"❌ Error: Directory {DATA_DIR_HOST} not found.")
        return

    tifs = list(DATA_DIR_HOST.glob("*.tif")) + list(DATA_DIR_HOST.glob("*.tiff"))
    
    if not tifs:
        print("Empty folder. No .tif files found.")
        return

    print(f"🧐 Checking {len(tifs)} files for COG compliance...\n")

    for tif_path in tifs:
        # Construct the internal container path that TiTiler understands
        container_path = f"{DATA_DIR_CONTAINER}/{tif_path.name}"
        
        try:
            response = requests.get(TITILER_ENDPOINT, params={"url": container_path})
            response.raise_for_status()
            data = response.json()
            
            # The key TiTiler actually uses to confirm validity:
            is_valid = data.get("COG") == True and data.get("COG_errors") is None
            
            print(f"Full Validation: {data.get('validation')}")
            status = data.get("status")

            if is_valid:
                print(f"✅ [VALID] {tif_path.name}")
            else:
                print(f"❌ [INVALID] {tif_path.name}")
                for error in data.get("validation", {}).get("errors", []):
                    print(f"   - Error: {error}")
                for warn in data.get("validation", {}).get("warnings", []):
                    print(f"   - Warning: {warn}")
                    
        except requests.exceptions.RequestException as e:
            print(f"⚠️  Communication Error with TiTiler for {tif_path.name}: {e}")


if __name__ == "__main__":
    check_rasters()

"""
The Optimization Script (data/optimizer.py)
This script uses gdalinfo to check for COG status and gdal_translate to fix them. 
Using the internal GDAL tools is more robust than calling the TiTiler API for this specific task.
"""

import os
import subprocess
import json
from pathlib import Path
import requests


RAW_DIR = Path("data_files/Raster")
OUT_DIR = Path("data_files/Optimized_Raster")


def is_cog(file_path):
    """Checks if a file is already a COG using gdalinfo."""
    """try:
        cmd = ["gdalinfo", "-json", str(file_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        info = json.loads(result.stdout)
        # Look for the COG layout metadata
        return any("LAYOUT=COG" in str(md) for md in info.get("metadata", {}).values())
    except:"""
    return False


def optimize():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tifs = list(RAW_DIR.glob("*.tif")) + list(RAW_DIR.glob("*.tiff"))
    print(tifs)

    print(f"🚀 Starting optimization scan on {len(tifs)} files...")

    for tif in tifs:
        out_file = OUT_DIR / tif.name
        
        if out_file.exists():
            print(f"⏩ Skipping {tif.name}, optimized version already exists.")
            continue

        if is_cog(tif):
            print(f"✅ {tif.name} is already a COG. Copying to optimized folder...")
            subprocess.run(["cp", str(tif), str(out_file)])
        else:
            print(f"🛠️  Optimizing {tif.name}...")
            
            # Step 1: Build internal overviews (pyramids)
            # -r average is good for continuous data (elevations/aspect)
            # print("   > Building overviews...")
            # subprocess.run(["gdaladdo", "-r", "average", str(tif), "2", "4", "8", "16", "32"])
            print(f"🛠️  Optimizing {tif.name}...")
            # Convert to COG
            cmd = [
                "gdal_translate", str(tif), str(out_file),
                "-of", "COG",
                "-co", "COMPRESS=DEFLATE",
                "-co", "BLOCKSIZE=512",
                "-co", "OVERVIEWS=AUTO",
                "-co", "RESAMPLING=AVERAGE",
                "-co", "TILING=YES",
                "-co", "NUM_THREADS=ALL_CPUS"
            ]

            subprocess.run(cmd)
            print(f"🏁 Finished {tif.name}")


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
    optimize()
    check_rasters()

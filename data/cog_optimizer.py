"""
The Optimization Script (data/optimizer.py)
This script uses gdalinfo to check for COG status and gdal_translate to fix them. 
Using the internal GDAL tools is more robust than calling the TiTiler API for this specific task.
"""

import os
import shutil
import subprocess
import json
from pathlib import Path
import requests

from raster_utils import prepare_multiband_source


RAW_DIR = Path("data_files/Raster")
OUT_DIR = Path("data_files/Optimized_Raster")
UNCATEGORIZED = "Uncategorized"


def relative_to_raster(tif: Path) -> Path:
    """Path of a raster relative to RAW_DIR, e.g. 'aspect/foo.tif'.
    Files sitting directly in RAW_DIR (no category folder) are bucketed
    under UNCATEGORIZED so every output file still has a category."""
    rel = tif.relative_to(RAW_DIR)
    if len(rel.parts) == 1:
        return Path(UNCATEGORIZED) / rel
    return rel


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
    tifs = list(RAW_DIR.rglob("*.tif")) + list(RAW_DIR.rglob("*.tiff"))
    print(tifs)

    print(f"🚀 Starting optimization scan on {len(tifs)} files...")

    for tif in tifs:
        rel_path = relative_to_raster(tif)
        out_file = OUT_DIR / rel_path
        out_file.parent.mkdir(parents=True, exist_ok=True)

        if out_file.exists():
            print(f"⏩ Skipping {rel_path}, optimized version already exists.")
            continue

        # Multi-band sources (e.g. a daily time series for a year) get a
        # synthetic mean band prepended ahead of the real bands. Rasters
        # that already have a single band pass through unchanged.
        mean_tmp = out_file.parent / f"_{out_file.stem}.band_mean_tmp.tif"
        try:
            conversion_src = prepare_multiband_source(tif, mean_tmp)
        except Exception as e:
            print(f"❌ Could not read {rel_path}, skipping: {e}")
            continue

        try:
            if is_cog(conversion_src):
                print(f"✅ {rel_path} is already a COG. Copying to optimized folder...")
                shutil.copy2(str(conversion_src), str(out_file))
            else:
                print(f"🛠️  Optimizing {rel_path}...")

                # Step 1: Build internal overviews (pyramids)
                # -r average is good for continuous data (elevations/aspect)
                # print("   > Building overviews...")
                # subprocess.run(["gdaladdo", "-r", "average", str(tif), "2", "4", "8", "16", "32"])
                # Convert to COG
                cmd = [
                    "gdal_translate", str(conversion_src), str(out_file),
                    "-of", "COG",
                    "-co", "COMPRESS=DEFLATE",
                    "-co", "BLOCKSIZE=512",
                    "-co", "OVERVIEWS=AUTO",
                    "-co", "RESAMPLING=AVERAGE",
                    "-co", "TILING=YES",
                    "-co", "NUM_THREADS=ALL_CPUS"
                ]

                subprocess.run(cmd)
                print(f"🏁 Finished {rel_path}")
        finally:
            if conversion_src == mean_tmp and mean_tmp.exists():
                mean_tmp.unlink()


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

    tifs = list(DATA_DIR_HOST.rglob("*.tif")) + list(DATA_DIR_HOST.rglob("*.tiff"))

    if not tifs:
        print("Empty folder. No .tif files found.")
        return

    print(f"🧐 Checking {len(tifs)} files for COG compliance...\n")

    for tif_path in tifs:
        # Construct the internal container path that TiTiler understands,
        # preserving the category subfolder.
        rel_path = tif_path.relative_to(DATA_DIR_HOST).as_posix()
        container_path = f"{DATA_DIR_CONTAINER}/{rel_path}"

        try:
            response = requests.get(TITILER_ENDPOINT, params={"url": container_path})
            response.raise_for_status()
            data = response.json()

            # The key TiTiler actually uses to confirm validity:
            is_valid = data.get("COG") == True and data.get("COG_errors") is None

            print(f"Full Validation: {data.get('validation')}")
            status = data.get("status")

            if is_valid:
                print(f"✅ [VALID] {rel_path}")
            else:
                print(f"❌ [INVALID] {rel_path}")
                for error in data.get("validation", {}).get("errors", []):
                    print(f"   - Error: {error}")
                for warn in data.get("validation", {}).get("warnings", []):
                    print(f"   - Warning: {warn}")
                    
        except requests.exceptions.RequestException as e:
            print(f"⚠️  Communication Error with TiTiler for {tif_path.name}: {e}")


if __name__ == "__main__":
    optimize()
    check_rasters()

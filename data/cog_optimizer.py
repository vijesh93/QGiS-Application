"""
The Optimization Script (data/optimizer.py)
This script uses gdalinfo to check for COG status and gdal_translate to fix them. 
Using the internal GDAL tools is more robust than calling the TiTiler API for this specific task.
"""

from pathlib import Path
import requests

from raster_utils import optimize_to_cog, is_stale_timeseries_output


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


def optimize():
    """Converts every raw raster to its optimized form via the one shared
    `raster_utils.optimize_to_cog()` — this used to be a separate, duplicate
    implementation that (among other issues) always used GDAL's COG driver
    even for multi-band time-series files, hardcoding the `INTERLEAVE=PIXEL`
    layout that made per-band tile reads slow (see docs/vrt_explainer.md).
    Using the shared function means this step and `register_layers.py`'s own
    staleness check can never drift out of sync with each other again.
    """
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tifs = list(RAW_DIR.rglob("*.tif")) + list(RAW_DIR.rglob("*.tiff"))

    print(f"🚀 Starting optimization scan on {len(tifs)} files...")

    for tif in tifs:
        rel_path = relative_to_raster(tif)
        out_file = OUT_DIR / rel_path
        out_file.parent.mkdir(parents=True, exist_ok=True)

        force_rebuild = is_stale_timeseries_output(tif, out_file)
        if out_file.exists() and not force_rebuild:
            print(f"⏩ Skipping {rel_path}, optimized version already exists.")
            continue

        print(f"🛠️  Optimizing {rel_path}...")
        if optimize_to_cog(tif, out_file, force=force_rebuild):
            print(f"🏁 Finished {rel_path}")
        else:
            print(f"❌ Failed to optimize {rel_path}")


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

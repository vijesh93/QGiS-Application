import os
import rasterio
from pathlib import Path
from typing import Dict, Any, List
import numpy as np


def get_tiff_metadata(file_path: str) -> Dict[str, Any]:
    """
    Opens a TIFF file and extracts key metadata for DB injection.
    """
    with rasterio.open(file_path) as src:
        meta = {
            "filename": os.path.basename(file_path),
            "width": src.width,
            "height": src.height,
            "count": src.count,  # Number of bands (e.g., RGB=3)
            "crs": src.crs.to_string() if src.crs else "Unknown",
            "bounds": {
                "left": src.bounds.left,
                "bottom": src.bounds.bottom,
                "right": src.bounds.right,
                "top": src.bounds.top,
            },
            "driver": src.driver,
            "nodata": src.nodata
        }
    return meta


def scan_data_directory(directory: str) -> List[Path]:
    """
    Finds all .tif and .tiff files in the specified folder.
    """
    valid_extensions = ('.tif', '.tiff', '.TIF', '.TIFF')
    path = Path(directory)
    return [p for p in path.glob('**/*') if p.suffix in valid_extensions]


def explore_tiff(file_path: str, read_raw: bool = False):
    with rasterio.open(file_path) as src:
        print(f"=== File: {src.name} ===")
        
        # 1. Spatial Metadata
        print(f"Bands: {src.count}")
        print(f"Width/Height: {src.width}x{src.height}")
        print(f"CRS: {src.crs}")
        
        # The Affine Transform: Maps pixel (row, col) -> (lon, lat)
        # It looks like: [width of pixel, rotation, upper-left X, rotation, height of pixel, upper-left Y]
        print(f"Transform (Affine):\n{src.transform}")

        if read_raw:
            # Read the first band (index 1)
            # This is where the heavy memory usage happens
            data_array = src.read(1) 
            
            print("\n=== Raw Data Analysis ===")
            print(f"Data Type: {data_array.dtype}")
            print(f"Min Value: {np.min(data_array)}")
            print(f"Max Value: {np.max(data_array)}")
            print(f"Average Value: {np.mean(data_array):.2f}")

            # Look at a small 5x5 slice of pixels from the top-left corner
            print("\nTop-Left 5x5 Pixel Grid (Raw Values):")
            print(data_array[0:5, 0:5])

            # Coordinate Lookup: What is the GPS coord of the top-left pixel?
            lon, lat = src.xy(0, 0) # (row 0, col 0)
            print(f"\nCoordinate of pixel [0,0]: {lon}, {lat}")


if __name__ == "__main__":
    # Define your internal data folder
    DATA_DIR = "./data_files/Raster" 

    print(f"--- Scanning directory: {DATA_DIR} ---")
    tiff_files = scan_data_directory(DATA_DIR)
    print(f"Found {len(tiff_files)} TIFF files.\n")

    for tiff_path in tiff_files:
        try:
            metadata = get_tiff_metadata(str(tiff_path))
            print(f"File: {metadata['filename']}")
            print(f"  - Resolution: {metadata['width']}x{metadata['height']}")
            print(f"  - CRS: {metadata['crs']}")
            print(f"  - Bounds: {metadata['bounds']}")
            print("-" * 30)
        except Exception as e:
            print(f"Error reading {tiff_path.name}: {e}")
    
    # For last file:
    # Spatial Metadata
    with rasterio.open(tiff_path) as src:
        print(f"=== File: {src.name} ===")
        print(f"Bands: {src.count}")
        print(f"Width/Height: {src.width}x{src.height}")
        print(f"CRS: {src.crs}")
        
        # The Affine Transform: Maps pixel (row, col) -> (lon, lat)
        # It looks like: [width of pixel, rotation, upper-left X, rotation, height of pixel, upper-left Y]
        print(f"Transform (Affine):\n{src.transform}")
        data_array = src.read(1) 
        print("\n=== Raw Data Analysis ===")
        print(f"Data Type: {data_array.dtype}")
        print(f"Min Value: {np.min(data_array)}")
        print(f"Max Value: {np.max(data_array)}")
        print(f"Average Value: {np.mean(data_array):.2f}")

        # Look at a small 5x5 slice of pixels from the top-left corner
        print("\nTop-Left 5x5 Pixel Grid (Raw Values):")
        print(data_array[0:5, 0:5])

        # Coordinate Lookup: What is the GPS coord of the top-left pixel?
        lon, lat = src.xy(0, 0) # (row 0, col 0)
        print(f"\nCoordinate of pixel [0,0]: {lon}, {lat}")
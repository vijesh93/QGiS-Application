import os
import requests
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

# Create a directory to store downloads
script_dir = os.path.dirname(os.path.abspath(__file__))          # data/data_downloader/
data_dir   = os.path.dirname(script_dir)                          # data/
download_dir = os.path.join(data_dir, "data_files", "Raster")    # data/data_files/Raster/
os.makedirs(download_dir, exist_ok=True)

# List of 1KM resolution files from the document
urls_1km = [
    "https://hs.pangaea.de/model/SRTM/aspect/aspectcosine_1KMma_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/aspect/aspectcosine_1KMmd_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/aspect/aspectcosine_1KMmi_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/aspect/aspectcosine_1KMmn_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/aspect/aspectcosine_1KMsd_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/aspect/aspectsine_1KMma_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/aspect/aspectsine_1KMmd_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/aspect/aspectsine_1KMmi_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/aspect/aspectsine_1KMmn_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/aspect/aspectsine_1KMsd_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/aspect/eastness_1KMma_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/aspect/eastness_1KMmd_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/aspect/eastness_1KMmi_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/aspect/eastness_1KMmn_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/aspect/eastness_1KMsd_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/aspect/northness_1KMma_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/aspect/northness_1KMmd_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/aspect/northness_1KMmi_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/aspect/northness_1KMmn_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/aspect/northness_1KMsd_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/elevation/elevation_1KMma_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/elevation/elevation_1KMmd_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/elevation/elevation_1KMmi_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/elevation/elevation_1KMmn_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/elevation/elevation_1KMsd_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/roughness/roughness_1KMma_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/roughness/roughness_1KMmd_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/roughness/roughness_1KMmi_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/roughness/roughness_1KMmn_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/roughness/roughness_1KMsd_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/slope/slope_1KMma_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/slope/slope_1KMmd_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/slope/slope_1KMmi_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/slope/slope_1KMmn_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/slope/slope_1KMsd_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/tpi/tpi_1KMma_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/tpi/tpi_1KMmd_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/tpi/tpi_1KMmi_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/tpi/tpi_1KMmn_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/tpi/tpi_1KMsd_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/tri/tri_1KMma_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/tri/tri_1KMmd_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/tri/tri_1KMmi_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/tri/tri_1KMmn_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/tri/tri_1KMsd_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/vrm/vrm_1KMma_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/vrm/vrm_1KMmd_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/vrm/vrm_1KMmi_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/vrm/vrm_1KMmn_SRTM.tif",
    "https://hs.pangaea.de/model/SRTM/vrm/vrm_1KMsd_SRTM.tif"
]

def download_file(url):
    try:
        # Extract filename from URL
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path)
        filepath = os.path.join(download_dir, filename)

        # Skip if file already exists
        if os.path.exists(filepath):
            print(f"File already exists: {filename}")
            return filename, True

        print(f"Downloading: {filename}")

        # Stream the download to handle large files
        response = requests.get(url, stream=True)
        response.raise_for_status()

        # Save the file
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        return filename, True
    except Exception as e:
        print(f"Error downloading {url}: {str(e)}")
        return url, False

def main():
    print(f"Starting download of {len(urls_1km)} 1KM resolution files...")
    print(f"Files will be saved to: {os.path.abspath(download_dir)}")

    # Use ThreadPoolExecutor for concurrent downloads (adjust max_workers as needed)
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(download_file, url) for url in urls_1km]

        success_count = 0
        for future in as_completed(futures):
            filename, success = future.result()
            if success:
                success_count += 1

    print(f"\nDownload complete!")
    print(f"Successfully downloaded {success_count}/{len(urls_1km)} files")

if __name__ == "__main__":
    main()

import os
import time
import requests
from urllib.parse import urlparse

# ── Paths ─────────────────────────────────────────────────────────────────────
script_dir   = os.path.dirname(os.path.abspath(__file__))   # data/data_downloader/
data_dir     = os.path.dirname(script_dir)                  # data/
download_dir = os.path.join(data_dir, "data_files", "Raster")
os.makedirs(download_dir, exist_ok=True)

# ── Settings ──────────────────────────────────────────────────────────────────
MAX_RETRIES   = 5       # retry each file up to 5 times on 503
RETRY_DELAY   = 10      # seconds to wait between retries (doubles each attempt)
REQUEST_DELAY = 2       # seconds to wait between each file (avoids rate limiting)

# ── URLs ──────────────────────────────────────────────────────────────────────
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
    "https://hs.pangaea.de/model/SRTM/vrm/vrm_1KMsd_SRTM.tif",
]


def download_file(url: str) -> tuple[str, bool]:
    """Download a single file with exponential backoff retry on 503."""
    parsed   = urlparse(url)
    filename = os.path.basename(parsed.path)
    filepath = os.path.join(download_dir, filename)

    # Skip if already fully downloaded
    if os.path.exists(filepath):
        print(f"  ⏩ Already exists, skipping: {filename}")
        return filename, True

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"  ⬇️  Downloading ({attempt}/{MAX_RETRIES}): {filename}")
            response = requests.get(url, stream=True, timeout=60)
            response.raise_for_status()

            # Write to a temp file first — avoids leaving corrupt partial files
            tmp_path = filepath + ".tmp"
            with open(tmp_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)

            os.rename(tmp_path, filepath)
            print(f"  ✅ Done: {filename}")
            return filename, True

        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else "?"
            if status == 503 and attempt < MAX_RETRIES:
                delay = RETRY_DELAY * (2 ** (attempt - 1))  # 10s, 20s, 40s, 80s
                print(f"  ⚠️  503 from server — waiting {delay}s before retry...")
                time.sleep(delay)
            else:
                print(f"  ❌ Failed after {attempt} attempts: {filename} — {e}")
                # Clean up temp file if it exists
                if os.path.exists(filepath + ".tmp"):
                    os.remove(filepath + ".tmp")
                return filename, False

        except Exception as e:
            print(f"  ❌ Unexpected error for {filename}: {e}")
            if os.path.exists(filepath + ".tmp"):
                os.remove(filepath + ".tmp")
            return filename, False

    return filename, False


def main():
    print(f"Starting sequential download of {len(urls_1km)} files")
    print(f"Saving to: {os.path.abspath(download_dir)}")
    print(f"Delay between files: {REQUEST_DELAY}s  |  Max retries: {MAX_RETRIES}\n")

    failed = []
    success_count = 0

    for i, url in enumerate(urls_1km, 1):
        print(f"[{i:02d}/{len(urls_1km)}]")
        filename, ok = download_file(url)
        if ok:
            success_count += 1
        else:
            failed.append(url)

        # Polite delay between requests — avoids triggering rate limit
        if i < len(urls_1km):
            time.sleep(REQUEST_DELAY)

    print(f"\n{'='*50}")
    print(f"✅ Successfully downloaded: {success_count}/{len(urls_1km)}")

    if failed:
        print(f"❌ Failed ({len(failed)} files):")
        for url in failed:
            print(f"   {url}")
        print(f"\nRe-run the script to retry — existing files are skipped automatically.")
    else:
        print("🎉 All files downloaded successfully!")


if __name__ == "__main__":
    main()
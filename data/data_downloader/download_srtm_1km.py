#!/usr/bin/env python3
"""
Bulk download 1km resolution SRTM topographic variables from PANGAEA
Dataset: https://doi.org/10.1594/PANGAEA.867114
"""

import os
import requests
from pathlib import Path
from typing import List
import time

def parse_data_file(filename: str) -> List[dict]:
    """
    Parse the tab-delimited file containing URLs and metadata
    """
    files_to_download = []
    
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
        # Skip header lines (look for the data start)
        data_start = 0
        for i, line in enumerate(lines):
            if line.startswith('File name\t'):
                data_start = i + 1
                break
        
        # Parse data lines
        for line in lines[data_start:]:
            if not line.strip():
                continue
            
            parts = line.strip().split('\t')
            if len(parts) >= 4:
                file_info = {
                    'name': parts[0],
                    'format': parts[1],
                    'size_kb': parts[2],
                    'url': parts[3]
                }
                files_to_download.append(file_info)
    
    return files_to_download

def filter_1km_files(files: List[dict]) -> List[dict]:
    """
    Filter files to only include 1km resolution variables
    """
    return [f for f in files if '_1KM' in f['name']]

def download_file(url: str, output_dir: Path, filename: str) -> bool:
    """
    Download a single file with progress indication
    """
    try:
        print(f"Downloading: {filename}")
        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()
        
        output_path = output_dir / filename
        total_size = int(response.headers.get('content-length', 0))
        
        with open(output_path, 'wb') as f:
            if total_size == 0:
                f.write(response.content)
            else:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        progress = (downloaded / total_size) * 100
                        print(f"  Progress: {progress:.1f}%", end='\r')
        
        print(f"  ✓ Completed: {filename}")
        return True
        
    except Exception as e:
        print(f"  ✗ Error downloading {filename}: {str(e)}")
        return False

def main():
    """
    Main function to download all 1km resolution SRTM files
    """
    # Configuration
    input_file = "SRTM_list-of-links-to-files.txt"
    output_dir = Path("SRTM_1KM_data")
    
    # Create output directory structure
    output_dir.mkdir(exist_ok=True)
    categories = ['aspect', 'elevation', 'roughness', 'slope', 'tpi', 'tri', 'vrm']
    for cat in categories:
        (output_dir / cat).mkdir(exist_ok=True)
    
    print("="*70)
    print("SRTM 1km Resolution Topographic Variables Downloader")
    print("Dataset: https://doi.org/10.1594/PANGAEA.867114")
    print("="*70)
    print()
    
    # Parse the data file
    print(f"Reading file list from: {input_file}")
    all_files = parse_data_file(input_file)
    print(f"Total files in dataset: {len(all_files)}")
    
    # Filter for 1km resolution
    files_1km = filter_1km_files(all_files)
    print(f"1km resolution files to download: {len(files_1km)}")
    print()
    
    # Calculate total download size
    total_size_kb = sum(int(f['size_kb']) for f in files_1km if f['size_kb'].isdigit())
    total_size_mb = total_size_kb / 1024
    total_size_gb = total_size_mb / 1024
    print(f"Estimated total download size: {total_size_gb:.2f} GB")
    print()
    
    # Confirm download
    response = input("Do you want to proceed with the download? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("Download cancelled.")
        return
    
    print()
    print("Starting downloads...")
    print()
    
    # Download files
    success_count = 0
    failed_files = []
    
    for i, file_info in enumerate(files_1km, 1):
        # Extract category from file name
        name_parts = file_info['name'].split(' | ')
        if len(name_parts) >= 2:
            category = name_parts[1].strip()
            filename = name_parts[2].strip() + '.tif'
            category_dir = output_dir / category
        else:
            category_dir = output_dir
            filename = file_info['name'] + '.tif'
        
        print(f"[{i}/{len(files_1km)}] ", end='')
        
        if download_file(file_info['url'], category_dir, filename):
            success_count += 1
        else:
            failed_files.append(filename)
        
        # Be nice to the server
        time.sleep(1)
        print()
    
    # Summary
    print()
    print("="*70)
    print("Download Summary")
    print("="*70)
    print(f"Successfully downloaded: {success_count}/{len(files_1km)} files")
    
    if failed_files:
        print(f"\nFailed downloads ({len(failed_files)}):")
        for f in failed_files:
            print(f"  - {f}")
    
    print()
    print(f"Files saved to: {output_dir.absolute()}")
    print()
    print("Citation:")
    print("Amatulli, G. et al. (2018): A suite of global, cross-scale")
    print("topographic variables for environmental and biodiversity modeling.")
    print("Scientific Data, 5, 180040, https://doi.org/10.1038/sdata.2018.40")

if __name__ == "__main__":
    main()

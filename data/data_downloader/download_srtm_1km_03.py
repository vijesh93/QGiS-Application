#!/usr/bin/env python3
"""
Bulk download 1km resolution SRTM topographic variables from PANGAEA
Dataset: https://doi.org/10.1594/PANGAEA.867114
"""

import os
import re
import requests
from pathlib import Path
from typing import List
import time
import argparse

def sanitize_filename(filename: str) -> str:
    """
    Remove invalid characters from filename for Windows compatibility
    """
    # Remove or replace invalid characters: < > : " / \ | ? *
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, '_', filename)
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip('. ')
    return sanitized

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
                original_name = parts[0]
                sanitized_name = sanitize_filename(original_name)
                
                file_info = {
                    'name': sanitized_name,
                    'original_name': original_name,
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

def get_category_and_filename(original_name: str, sanitized_name: str) -> tuple:
    """
    Extract category and clean filename from original name
    """
    # Try to extract from pattern "SRTM | category | variable"
    match = re.search(r'SRTM\s*\|\s*(\w+)\s*\|\s*(.+)', original_name)
    if match:
        category = match.group(1).strip().lower()
        variable = match.group(2).strip()
        filename = sanitize_filename(variable) + '.tif'
        return category, filename
    
    # Fallback: use sanitized name
    return 'other', sanitized_name + '.tif'

def check_existing_files(output_dir: Path, files_1km: List[dict]) -> tuple:
    """
    Check which files already exist and which are missing
    Returns: (existing_files, missing_files)
    """
    existing = []
    missing = []
    
    for file_info in files_1km:
        category, filename = get_category_and_filename(
            file_info['original_name'], 
            file_info['name']
        )
        category_dir = output_dir / category
        file_path = category_dir / filename
        
        if file_path.exists():
            existing.append({**file_info, 'category': category, 'filename': filename})
        else:
            missing.append({**file_info, 'category': category, 'filename': filename})
    
    return existing, missing

def download_file(url: str, output_path: Path, filename: str) -> bool:
    """
    Download a single file with progress indication
    """
    try:
        print(f"Downloading: {filename}")
        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()
        
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
        
        print(f"\n  ✓ Completed: {filename}")
        return True
        
    except Exception as e:
        print(f"\n  ✗ Error downloading {filename}: {str(e)}")
        # Clean up partial download
        if output_path.exists():
            output_path.unlink()
        return False

def list_missing_files(output_dir: Path, files_1km: List[dict]):
    """
    List all missing files without downloading
    """
    existing, missing = check_existing_files(output_dir, files_1km)
    
    print()
    print("="*70)
    print("File Status Report")
    print("="*70)
    print(f"✓ Existing files: {len(existing)}/{len(files_1km)}")
    print(f"✗ Missing files: {len(missing)}/{len(files_1km)}")
    print()
    
    if missing:
        print("Missing files by category:")
        print("-" * 70)
        
        # Group by category
        by_category = {}
        for file_info in missing:
            cat = file_info['category']
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(file_info['filename'])
        
        for category, filenames in sorted(by_category.items()):
            print(f"\n{category.upper()} ({len(filenames)} files):")
            for fname in sorted(filenames):
                print(f"  - {fname}")
    else:
        print("✓ All files are present!")
    
    print()

def main():
    """
    Main function to download all 1km resolution SRTM files
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Bulk download 1km resolution SRTM topographic variables from PANGAEA',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download all files
  python download_srtm_1km.py

  # Download only missing files
  python download_srtm_1km.py --missing-only

  # List missing files without downloading
  python download_srtm_1km.py --list-missing

  # Custom input/output
  python download_srtm_1km.py -i myfile.txt -o my_output_dir
        """
    )
    parser.add_argument(
        '--input', '-i',
        type=str,
        default='SRTM_list-of-links-to-files.txt',
        help='Input file with URLs (default: SRTM_list-of-links-to-files.txt)'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='SRTM_1KM_data',
        help='Output directory (default: SRTM_1KM_data)'
    )
    parser.add_argument(
        '--missing-only', '-m',
        action='store_true',
        help='Download only missing files (skip existing ones)'
    )
    parser.add_argument(
        '--list-missing', '-l',
        action='store_true',
        help='List missing files without downloading'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=1.0,
        help='Delay between downloads in seconds (default: 1.0)'
    )
    
    args = parser.parse_args()
    
    # Configuration
    input_file = args.input
    output_dir = Path(args.output)
    
    # Create output directory structure
    output_dir.mkdir(exist_ok=True)
    categories = ['aspect', 'elevation', 'roughness', 'slope', 'tpi', 'tri', 'vrm', 'other']
    for cat in categories:
        (output_dir / cat).mkdir(exist_ok=True)
    
    print("="*70)
    print("SRTM 1km Resolution Topographic Variables Downloader")
    print("Dataset: https://doi.org/10.1594/PANGAEA.867114")
    print("="*70)
    print()
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"❌ Error: Input file '{input_file}' not found!")
        return
    
    # Parse the data file
    print(f"Reading file list from: {input_file}")
    all_files = parse_data_file(input_file)
    print(f"Total files in dataset: {len(all_files)}")
    
    # Filter for 1km resolution
    files_1km = filter_1km_files(all_files)
    print(f"1km resolution files: {len(files_1km)}")
    print()
    
    # Check existing files
    existing_files, missing_files = check_existing_files(output_dir, files_1km)
    
    print(f"✓ Already downloaded: {len(existing_files)} files")
    print(f"✗ Missing: {len(missing_files)} files")
    print()
    
    # Handle list-missing mode
    if args.list_missing:
        list_missing_files(output_dir, files_1km)
        return
    
    # Determine which files to download
    if args.missing_only:
        files_to_download = missing_files
        print("Mode: Download missing files only")
    else:
        files_to_download = [
            {**f, 'category': get_category_and_filename(f['original_name'], f['name'])[0],
             'filename': get_category_and_filename(f['original_name'], f['name'])[1]}
            for f in files_1km
        ]
        print("Mode: Download all files (will skip existing)")
    
    if not files_to_download:
        print("✓ All files already downloaded!")
        return
    
    # Calculate total download size
    total_size_kb = sum(
        float(f['size_kb']) for f in files_to_download 
        if f['size_kb'].replace('.', '').isdigit()
    )
    total_size_gb = total_size_kb / (1024 * 1024)
    print(f"Estimated download size: {total_size_gb:.2f} GB ({len(files_to_download)} files)")
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
    skipped_count = 0
    
    start_time = time.time()
    
    for i, file_info in enumerate(files_to_download, 1):
        category = file_info['category']
        filename = file_info['filename']
        category_dir = output_dir / category
        file_path = category_dir / filename
        
        print(f"[{i}/{len(files_to_download)}] ", end='')
        
        # Skip if file already exists
        if file_path.exists():
            print(f"⏭️  Skipping (exists): {filename}")
            skipped_count += 1
        else:
            if download_file(file_info['url'], file_path, filename):
                success_count += 1
            else:
                failed_files.append(filename)
            
            # Be nice to the server
            time.sleep(args.delay)
        
        print()
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    # Summary
    print()
    print("="*70)
    print("Download Summary")
    print("="*70)
    print(f"✓ Successfully downloaded: {success_count} files")
    print(f"⏭️  Skipped (already exist): {skipped_count} files")
    print(f"Total processed: {success_count + skipped_count}/{len(files_to_download)} files")
    print(f"Time elapsed: {elapsed_time/60:.2f} minutes")
    
    if failed_files:
        print(f"\n❌ Failed downloads ({len(failed_files)}):")
        for f in failed_files:
            print(f"  - {f}")
        print(f"\nTo retry failed downloads, run:")
        print(f"  python download_srtm_1km.py --missing-only")
    
    print()
    print(f"📁 Files saved to: {output_dir.absolute()}")
    print()
    print("📚 Citation:")
    print("Amatulli, G. et al. (2018): A suite of global, cross-scale")
    print("topographic variables for environmental and biodiversity modeling.")
    print("Scientific Data, 5, 180040, https://doi.org/10.1038/sdata.2018.40")

if __name__ == "__main__":
    main()

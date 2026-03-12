#!/usr/bin/env python3
"""
Bulk download 1km resolution SRTM topographic variables from PANGAEA
Dataset: https://doi.org/10.1594/PANGAEA.867114
With multi-threaded downloads for improved speed
"""

import os
import re
import requests
from pathlib import Path
from typing import List
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import argparse

# Thread-safe print lock
print_lock = Lock()

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

def extract_category(filename: str) -> str:
    """
    Extract category from filename
    Format: "SRTM | category | variable_resolution_SRTM"
    """
    # Try to extract from the pattern "SRTM | category |"
    match = re.search(r'SRTM\s*\|\s*(\w+)\s*\|', filename)
    if match:
        return match.group(1).lower()
    
    # Fallback: look for known categories in the filename
    categories = ['aspect', 'elevation', 'roughness', 'slope', 'tpi', 'tri', 'vrm',
                  'aspectcosine', 'aspectsine', 'eastness', 'northness']
    
    filename_lower = filename.lower()
    for cat in categories:
        if cat in filename_lower:
            # Map specific variables to their parent category
            if cat in ['aspectcosine', 'aspectsine', 'eastness', 'northness']:
                return 'aspect'
            return cat
    
    # Default fallback
    return 'other'

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

def download_file(url: str, output_dir: Path, filename: str, thread_id: int = 0) -> tuple:
    """
    Download a single file with progress indication
    Returns: (success: bool, filename: str, error_message: str)
    """
    output_path = output_dir / filename
    
    # Skip if file already exists
    if output_path.exists():
        with print_lock:
            print(f"[Thread {thread_id}] ⏭️  Skipping (already exists): {filename}")
        return (True, filename, None)
    
    try:
        with print_lock:
            print(f"[Thread {thread_id}] ⬇️  Downloading: {filename}")
        
        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        
        with open(output_path, 'wb') as f:
            if total_size == 0:
                f.write(response.content)
            else:
                downloaded = 0
                chunk_size = 8192
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
        
        with print_lock:
            print(f"[Thread {thread_id}] ✅ Completed: {filename}")
        
        return (True, filename, None)
        
    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        with print_lock:
            print(f"[Thread {thread_id}] ❌ Failed: {filename} - {error_msg}")
        
        # Clean up partial download
        if output_path.exists():
            output_path.unlink()
        
        return (False, filename, error_msg)
    
    except Exception as e:
        error_msg = str(e)
        with print_lock:
            print(f"[Thread {thread_id}] ❌ Error: {filename} - {error_msg}")
        
        if output_path.exists():
            output_path.unlink()
        
        return (False, filename, error_msg)

def download_worker(file_info: dict, output_dir: Path, thread_id: int) -> tuple:
    """
    Worker function for thread pool
    """
    # Extract category from original filename
    category = extract_category(file_info['original_name'])
    
    # Use sanitized filename
    filename = file_info['name']
    
    # Create category subdirectory
    category_dir = output_dir / category
    category_dir.mkdir(parents=True, exist_ok=True)
    
    # Download the file
    return download_file(file_info['url'], category_dir, filename, thread_id)

def main():
    """
    Main function to orchestrate the download process
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Bulk download 1km resolution SRTM topographic variables from PANGAEA'
    )
    parser.add_argument(
        '--threads', '-t',
        type=int,
        default=4,
        help='Number of concurrent download threads (default: 4, recommended: 4-8)'
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
        default='srtm_1km_data',
        help='Output directory (default: srtm_1km_data)'
    )
    
    args = parser.parse_args()
    
    # Configuration
    INPUT_FILE = args.input
    OUTPUT_DIR = Path(args.output)
    NUM_THREADS = args.threads
    
    print("="*70)
    print("SRTM 1km Resolution Variables - Bulk Download")
    print("="*70)
    print(f"Multi-threaded download with {NUM_THREADS} concurrent threads")
    print()
    
    # Check if input file exists
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Error: Input file '{INPUT_FILE}' not found!")
        print("Please ensure the tab-delimited file with URLs is in the current directory.")
        return
    
    # Parse the data file
    print(f"📄 Parsing input file: {INPUT_FILE}")
    all_files = parse_data_file(INPUT_FILE)
    print(f"   Found {len(all_files)} total files")
    
    # Filter for 1km resolution files
    files_1km = filter_1km_files(all_files)
    print(f"   Filtered to {len(files_1km)} files at 1km resolution")
    print()
    
    if not files_1km:
        print("❌ No 1km resolution files found!")
        return
    
    # Calculate total size
    total_size_kb = sum(float(f['size_kb']) for f in files_1km if f['size_kb'].replace('.', '').isdigit())
    total_size_gb = total_size_kb / (1024 * 1024)
    
    print(f"📊 Total download size: ~{total_size_gb:.2f} GB")
    print(f"📁 Output directory: {OUTPUT_DIR.absolute()}")
    print()
    
    # Confirmation
    response = input(f"Ready to download {len(files_1km)} files using {NUM_THREADS} threads. Continue? (y/n): ")
    if response.lower() != 'y':
        print("Download cancelled.")
        return
    
    print()
    print("="*70)
    print("Starting downloads...")
    print("="*70)
    print()
    
    start_time = time.time()
    
    # Download files using thread pool
    success_count = 0
    failed_files = []
    
    with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
        # Submit all download tasks
        future_to_file = {
            executor.submit(download_worker, file_info, OUTPUT_DIR, i % NUM_THREADS): file_info
            for i, file_info in enumerate(files_1km)
        }
        
        # Process completed downloads
        for future in as_completed(future_to_file):
            file_info = future_to_file[future]
            try:
                success, filename, error = future.result()
                if success:
                    success_count += 1
                else:
                    failed_files.append((filename, error))
            except Exception as e:
                failed_files.append((file_info['name'], str(e)))
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    # Summary
    print()
    print("="*70)
    print("Download Summary")
    print("="*70)
    print(f"Successfully downloaded: {success_count}/{len(files_1km)} files")
    print(f"Total time: {elapsed_time/60:.2f} minutes ({elapsed_time:.1f} seconds)")
    print(f"Average speed: {len(files_1km)/elapsed_time*60:.1f} files/minute")
    
    if failed_files:
        print(f"\n❌ Failed downloads ({len(failed_files)}):")
        for filename, error in failed_files:
            print(f"  - {filename}")
            if error:
                print(f"    Error: {error}")
    
    print()
    print(f"📁 Files saved to: {OUTPUT_DIR.absolute()}")
    print()
    print("📚 Citation:")
    print("Amatulli, G. et al. (2018): A suite of global, cross-scale")
    print("topographic variables for environmental and biodiversity modeling.")
    print("Scientific Data, 5, 180040, https://doi.org/10.1038/sdata.2018.40")

if __name__ == "__main__":
    main()

"""
setup_layers.py  —  data/setup_layers.py

Full data pipeline orchestrator — pure Python, runs on Windows, Linux, macOS,
and inside the Docker container without any shell or bash dependency.

Steps:
    1. Download raw GeoTIFFs  (data_downloader/dowloader.py → data_files/Raster/)
    2. Optimize to COG        (cog_optimizer.py            → data_files/Optimized_Raster/)
    3. Validate COGs          (check_if_cog.py)
    4. Register in database   (register_layers.py)

Usage (inside container — recommended):
    docker exec -it geospatial-data-loader python setup_layers.py

Usage (on the host from the data/ folder):
    cd data
    python setup_layers.py

Options (pass as CLI args):
    --skip-download    Skip step 1
    --skip-optimize    Skip step 2
    --skip-validate    Skip step 3
    --only-register    Run step 4 only
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

# ── Locate scripts relative to THIS file — works everywhere ──────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
DOWNLOADER   = SCRIPT_DIR / "data_downloader" / "dowloader.py"
OPTIMIZER    = SCRIPT_DIR / "cog_optimizer.py"
VALIDATOR    = SCRIPT_DIR / "check_if_cog.py"
REGISTRAR    = SCRIPT_DIR / "register_layers.py"
RASTER_DIR   = SCRIPT_DIR / "data_files" / "Raster"
OPTIMIZED_DIR= SCRIPT_DIR / "data_files" / "Optimized_Raster"

PYTHON = sys.executable   # same interpreter that's running this script


# ── Colours (disabled automatically on Windows if not supported) ──────────────
def _supports_colour():
    return sys.stdout.isatty() and os.name != "nt" or os.environ.get("FORCE_COLOR")

_C = _supports_colour()
BLUE   = "\033[1;34m" if _C else ""
GREEN  = "\033[0;32m" if _C else ""
YELLOW = "\033[1;33m" if _C else ""
RED    = "\033[0;31m" if _C else ""
BOLD   = "\033[1m"    if _C else ""
NC     = "\033[0m"    if _C else ""


# ── Helpers ───────────────────────────────────────────────────────────────────
def header(title: str):
    bar = "═" * 44
    print(f"\n{BOLD}{BLUE}{bar}{NC}")
    print(f"{BOLD}{BLUE}  {title}{NC}")
    print(f"{BOLD}{BLUE}{bar}{NC}")

def ok(msg):   print(f"{GREEN}✅  {msg}{NC}")
def warn(msg): print(f"{YELLOW}⚠️   {msg}{NC}")
def fail(msg):
    print(f"{RED}❌  {msg}{NC}")
    sys.exit(1)

def count_tifs(directory: Path) -> int:
    if not directory.exists():
        return 0
    return len(list(directory.glob("*.tif")) + list(directory.glob("*.tiff")))

def run(script: Path, label: str) -> bool:
    """Run a Python script as a subprocess. Returns True on success."""
    print(f"\n{BOLD}▶ Running {script.name}...{NC}\n")
    result = subprocess.run(
        [PYTHON, str(script)],
        cwd=str(SCRIPT_DIR),   # always run from data/ so relative paths work
    )
    if result.returncode != 0:
        warn(f"{label} exited with code {result.returncode}")
        return False
    return True


# ── Pre-flight checks ─────────────────────────────────────────────────────────
def preflight():
    print(f"\n{BOLD}🌍 Baden-Württemberg Geoportal — Layer Setup Pipeline{NC}")
    print(f"   Script dir : {SCRIPT_DIR}")
    print(f"   Python     : {PYTHON}")
    print(f"   Started    : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Check all scripts exist
    for s in [DOWNLOADER, OPTIMIZER, VALIDATOR, REGISTRAR]:
        if not s.exists():
            fail(f"Script not found: {s}\n   Make sure you're running from the data/ folder.")

    # Check DATABASE_URL
    if not os.environ.get("DATABASE_URL"):
        fail(
            "DATABASE_URL is not set.\n"
            "   Inside container : it is injected automatically by docker-compose.\n"
            "   On host          : export DATABASE_URL=postgresql://user:pass@localhost:5432/geoportal"
        )
    ok("DATABASE_URL is set")

    # Ensure directories exist
    RASTER_DIR.mkdir(parents=True, exist_ok=True)
    OPTIMIZED_DIR.mkdir(parents=True, exist_ok=True)
    ok("Data directories ready")


# ── Pipeline steps ────────────────────────────────────────────────────────────
def step_download():
    header("Step 1 / 4 — Download raw GeoTIFFs")
    existing = count_tifs(RASTER_DIR)
    if existing > 0:
        warn(f"{existing} files already in Raster/ — downloader will skip existing files.")

    if not run(DOWNLOADER, "Downloader"):
        fail("Download failed. Check your network connection and proxy settings.")

    total = count_tifs(RASTER_DIR)
    ok(f"Download complete — {total} files in data_files/Raster/")
    return total


def step_optimize():
    header("Step 2 / 4 — Convert to Cloud Optimized GeoTIFF")
    raster_count = count_tifs(RASTER_DIR)
    if raster_count == 0:
        fail("No .tif files in data_files/Raster/. Run without --skip-download first.")

    if not run(OPTIMIZER, "COG Optimizer"):
        fail("Optimization failed.")

    total = count_tifs(OPTIMIZED_DIR)
    ok(f"Optimization complete — {total} COGs in data_files/Optimized_Raster/")
    return total


def step_validate():
    header("Step 3 / 4 — Validate COGs via TiTiler")
    cog_count = count_tifs(OPTIMIZED_DIR)
    if cog_count == 0:
        fail("No .tif files in data_files/Optimized_Raster/. Run without --skip-optimize first.")

    # Quick reachability check before running the full validator
    try:
        import urllib.request
        inside_docker = Path("/.dockerenv").exists()
        titiler_base  = (
            "http://raster-server:80"
            if inside_docker
            else os.environ.get("TITILER_HOST_URL", "http://localhost:8080")
        )
        urllib.request.urlopen(f"{titiler_base}/healthz", timeout=5)
        ok(f"TiTiler reachable at {titiler_base}")
        run(VALIDATOR, "COG Validator")
    except Exception:
        warn("TiTiler not reachable — skipping validation.")
        warn("Tiles may not serve correctly. Check the raster-server container.")


def step_register():
    header("Step 4 / 4 — Register layer metadata in PostGIS")
    cog_count = count_tifs(OPTIMIZED_DIR)
    if cog_count == 0:
        fail("No .tif files in data_files/Optimized_Raster/. Cannot register.")

    if not run(REGISTRAR, "Layer Registrar"):
        fail("Registration failed. Check DATABASE_URL and that the db container is healthy.")


# ── Summary ───────────────────────────────────────────────────────────────────
def summary():
    bar = "═" * 44
    print(f"\n{BOLD}{GREEN}{bar}{NC}")
    print(f"{BOLD}{GREEN}  🚀 Pipeline complete!{NC}")
    print(f"{BOLD}{GREEN}{bar}{NC}")
    print(f"   Raw rasters    : {count_tifs(RASTER_DIR)} files in data_files/Raster/")
    print(f"   Optimized COGs : {count_tifs(OPTIMIZED_DIR)} files in data_files/Optimized_Raster/")
    print(f"\n   Open the app → {BOLD}http://localhost:3000{NC}\n")


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="GeoPortal layer setup pipeline")
    parser.add_argument("--skip-download", action="store_true", help="Skip download step")
    parser.add_argument("--skip-optimize", action="store_true", help="Skip COG optimization step")
    parser.add_argument("--skip-validate", action="store_true", help="Skip COG validation step")
    parser.add_argument("--only-register", action="store_true", help="Only run the registration step")
    args = parser.parse_args()

    if args.only_register:
        args.skip_download = True
        args.skip_optimize = True
        args.skip_validate = True

    preflight()

    if not args.skip_download:
        step_download()
    else:
        warn("Skipping download (--skip-download)")

    if not args.skip_optimize:
        step_optimize()
    else:
        warn("Skipping optimization (--skip-optimize)")

    if not args.skip_validate:
        step_validate()
    else:
        warn("Skipping validation (--skip-validate)")

    step_register()
    summary()


if __name__ == "__main__":
    main()
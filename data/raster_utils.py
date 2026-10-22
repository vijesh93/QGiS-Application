"""
Shared helpers used before COG conversion.

Some source rasters (e.g. a daily time series for a whole year) carry many
bands in a single file instead of one band per layer. The pipeline keeps
every band exactly as it appears in the source, in order, so the frontend
can let a user scrub through individual timesteps (via TiTiler's `bidx`
tile parameter) — band 1 of the optimized output is simply the first real
band of the source, nothing synthetic is added.
"""

import re
import subprocess
from datetime import date, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

import rasterio

_BAND_DATE_RE = re.compile(r"^([A-Za-z]+)_(\d{4})_(\d{3})$")


def compute_band_range(path: Path) -> Optional[Tuple[float, float]]:
    """Returns (min, max) of the real (nodata-excluded) values across ALL bands.

    Used to give each registered layer its own TiTiler rescale window instead
    of a hardcoded one — a layer whose values don't happen to fall in [-1, 1]
    renders as a flat, undetailed color otherwise. Scanning every band (not
    just band 1) keeps this range valid, and the color scale stable, no
    matter which band/timestep a user has scrubbed to. Returns None if the
    raster has no valid (non-nodata) pixels at all.

    Accumulated one tile at a time rather than one whole band at a time: a
    full-band read of a 1KM raster (43200x14400 float32) allocates ~2.5 GB
    for the data, ~0.6 GB more for the mask, and as much again to extract
    the valid values via `.compressed()` — enough for the OOM killer to
    SIGKILL the process inside the data-loader container (surfacing as
    "exited with code -9"), independent of band count — a single-band file
    at this resolution hits it on its own, which a per-band (not per-tile)
    loop can't help with. Blockwise accumulation via `ds.block_windows()`
    yields exactly the same min/max but never holds more than one tile
    (e.g. 512x512) in memory, regardless of the raster's overall dimensions.
    """
    with rasterio.open(path) as ds:
        band_min, band_max = None, None
        for b in range(1, ds.count + 1):
            for _, window in ds.block_windows(b):
                block = ds.read(b, window=window, masked=True)
                if block.count() == 0:
                    continue
                lo, hi = float(block.min()), float(block.max())
                band_min = lo if band_min is None else min(band_min, lo)
                band_max = hi if band_max is None else max(band_max, hi)
        if band_min is None:
            return None
        return band_min, band_max


def parse_band_date_convention(descriptions: List[Optional[str]]) -> Tuple[Optional[date], Optional[int]]:
    """Derives (start_date, step_days) from a sequence of real-band descriptions.

    Expects the `<variable>_<year>_<day-of-year>` convention (e.g.
    `pr_2026_001` .. `pr_2026_365`): same variable, same year, and a constant
    day-of-year step across every band, in order. Returns (None, None) if the
    descriptions don't match (missing, inconsistent variable/year, or
    irregular step) — callers fall back to plain band-index labeling.
    """
    if not descriptions:
        return None, None

    parsed = []
    for desc in descriptions:
        if not desc:
            return None, None
        m = _BAND_DATE_RE.match(desc)
        if not m:
            return None, None
        parsed.append((m.group(1), int(m.group(2)), int(m.group(3))))

    variable, year, _ = parsed[0]
    if any(p[0] != variable or p[1] != year for p in parsed):
        return None, None

    doys = [p[2] for p in parsed]
    if len(doys) > 1:
        steps = {b - a for a, b in zip(doys, doys[1:])}
        if len(steps) != 1:
            return None, None
        step_days = steps.pop()
    else:
        step_days = 1

    start_date = date(year, 1, 1) + timedelta(days=doys[0] - 1)
    return start_date, step_days


def optimize_to_cog(src: Path, dst: Path, force: bool = False) -> bool:
    """Convert a GeoTIFF to an optimized, tiled GeoTIFF using gdal_translate.

    Every band of `src` is preserved, in order, with its original
    description — TiTiler's `bidx` tile parameter lets the frontend pick
    whichever one it wants. No synthetic band is added or removed.

    Single-band output uses GDAL's COG driver as before. Multi-band output
    deliberately does NOT use the COG driver: that driver hardcodes
    INTERLEAVE=PIXEL, which stores every band's value for a pixel together —
    so reading just one band out of a 366-band file still means decompressing
    all 366 bands' worth of data per tile (measured ~1.3-1.5s per tile,
    enough to make the map feel hung). Instead, multi-band output is built as
    a classic tiled GeoTIFF with INTERLEAVE=BAND (each band fully separable
    on disk) plus `gdaladdo` for overviews — functionally equivalent to a COG
    for TiTiler's purposes, but ~7-10x faster for single-band reads out of a
    many-band file (measured ~0.15-0.2s per tile after this change).

    `src` is converted straight to `dst` — no temp file, no extra read pass.

    If `force` is True, an existing `dst` is deleted and rebuilt instead of
    being skipped — used to regenerate files produced by an older version of
    this pipeline (e.g. the old mean-band convention, or the PIXEL-
    interleaved multi-band COG from before the INTERLEAVE fix).

    This is the one place raw→optimized conversion happens — both
    `cog_optimizer.py` (the pipeline's dedicated optimize step) and anything
    else that needs to (re)produce an optimized file call this, rather than
    each keeping its own copy of the conversion logic.
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        if not force:
            print(f"  ↳ Already optimized, skipping conversion: {dst.name}")
            return True
        dst.unlink()

    try:
        with rasterio.open(src) as ds:
            is_multiband = ds.count > 1
    except Exception as e:
        print(f"❌ Could not read {src.name}, skipping: {e}")
        return False

    try:
        if is_multiband:
            subprocess.run([
                "gdal_translate",
                "-of", "GTiff",
                "-co", "TILED=YES",
                "-co", "BLOCKXSIZE=512",
                "-co", "BLOCKYSIZE=512",
                "-co", "INTERLEAVE=BAND",
                "-co", "COMPRESS=DEFLATE",
                str(src), str(dst)
            ], check=True, capture_output=True)
            subprocess.run([
                "gdaladdo", "-r", "average", str(dst), "2", "4", "8"
            ], check=True, capture_output=True)
        else:
            subprocess.run([
                "gdal_translate",
                "-of", "COG",
                "-co", "COMPRESS=DEFLATE",
                "-co", "OVERVIEW_RESAMPLING=AVERAGE",
                str(src), str(dst)
            ], check=True, capture_output=True)

        print(f"  ↳ Optimized → {dst.name}")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ COG conversion failed for {src.name}: {e.stderr}")
        return False


def is_stale_timeseries_output(src: Path, optimized: Path) -> bool:
    """True if an already-optimized file needs rebuilding because `src` is a
    genuine multi-band (time-series) source but `optimized` doesn't reflect
    the current pipeline shape — either its band count doesn't match src's
    own band count (e.g. it still carries an old synthetic mean band from a
    previous version of this pipeline), or it's multi-band but still
    PIXEL-interleaved (the COG driver's hardcoded layout, which makes
    reading one band out of many require decompressing all of them — see
    optimize_to_cog's docstring).

    Single-band sources are NEVER flagged here: an optimized single-band
    file's band count (1) is indistinguishable from the old pre-feature
    squash output on its own, so staleness only makes sense relative to the
    source's own band count, not the optimized file in isolation.

    Also used by `register_layers.py` to decide whether an already-present
    optimized file is actually safe to register as-is, or should be skipped
    (not silently re-optimized) when the optimize step was never run.
    """
    if not optimized.exists():
        return False
    try:
        with rasterio.open(src) as src_ds:
            src_band_count = src_ds.count
        if src_band_count <= 1:
            return False  # static raster — never subject to the time-series shape
        with rasterio.open(optimized) as ds:
            if ds.count != src_band_count:
                return True
            return ds.tags(ns="IMAGE_STRUCTURE").get("INTERLEAVE") != "BAND"
    except Exception:
        return True


_VRT_ABS_SOURCE_RE = re.compile(r'<SourceFilename relativeToVRT="0">[^<]*</SourceFilename>')


def generate_band_vrts(optimized_path: Path, band_count: int) -> None:
    """Writes one single-band GDAL VRT per band of `optimized_path`.

    Why: TiTiler's reader (rio-tiler) always builds a WarpedVRT over the
    *entire* source dataset before reading, no matter which single `bidx` is
    requested — so picking one band out of a 366-band file still pays the
    cost of reprojecting all 366 (confirmed ~550-950ms per tile, vs ~30-80ms
    for a genuinely single-band file). A VRT that itself only exposes one
    band sidesteps this entirely, since there's then only ever one band for
    rio-tiler to warp. See docs/vrt_explainer.md for the full writeup.

    Skipped entirely when `band_count <= 1` — a static raster has nothing to
    split out. Idempotent and self-contained: a VRT already newer than
    `optimized_path` is left alone, so calling this on every registration
    run is cheap once everything is up to date — only a missing VRT or a
    rebuilt `optimized_path` triggers real work.

    Each VRT is named `<stem>_band{n:03d}.vrt` and written next to
    `optimized_path`. `gdal_translate` always writes its `SourceFilename` as
    an absolute path, which isn't portable across containers that mount the
    data directory at different paths (`data-loader`: `/app`,
    `raster-server`: `/data`) — so it's rewritten here to a bare relative
    filename, valid as long as the VRT stays next to its source (guaranteed
    by construction above).
    """
    if band_count <= 1:
        return

    src_mtime = optimized_path.stat().st_mtime

    for n in range(1, band_count + 1):
        vrt_path = optimized_path.with_name(f"{optimized_path.stem}_band{n:03d}.vrt")
        if vrt_path.exists() and vrt_path.stat().st_mtime >= src_mtime:
            continue

        try:
            subprocess.run(
                ["gdal_translate", "-of", "VRT", "-b", str(n), str(optimized_path), str(vrt_path)],
                check=True, capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Failed to generate band VRT {vrt_path.name} for {optimized_path.name}: {e.stderr}"
            ) from e

        text = vrt_path.read_text()
        text = _VRT_ABS_SOURCE_RE.sub(
            f'<SourceFilename relativeToVRT="1">{optimized_path.name}</SourceFilename>',
            text,
        )
        vrt_path.write_text(text)

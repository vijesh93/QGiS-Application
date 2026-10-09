"""
Shared helpers used before COG conversion.

Some source rasters (e.g. a daily time series for a whole year) carry many
bands in a single file instead of one band per layer. Earlier, those got
collapsed to a single across-band mean before COG conversion. The pipeline
now keeps every band so the frontend can let a user scrub through individual
timesteps (via TiTiler's `bidx` tile parameter), and additionally prepends a
synthetic "mean" band ahead of the real ones so a newly-activated layer still
defaults to the same smooth annual-overview look it always has, before the
user touches a time control.

A raster that already has exactly one band is returned unchanged — nothing
to average, nothing to prepend.
"""

import re
import subprocess
from datetime import date, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
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
    """
    with rasterio.open(path) as ds:
        band_min, band_max = None, None
        for b in range(1, ds.count + 1):
            data = ds.read(b, masked=True)
            valid = data.compressed()
            if valid.size == 0:
                continue
            lo, hi = float(valid.min()), float(valid.max())
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


def prepare_multiband_source(src: Path, tmp_path: Path) -> Path:
    """Returns a Path to a COG-ready version of `src` with a mean band prepended.

    If `src` has exactly one band, `src` itself is returned untouched (static
    rasters never get a synthetic mean band — there's nothing to average).

    If it has more than one band, writes a `(count + 1)`-band file to
    `tmp_path`: band 1 is the nodata-aware mean across all source bands (no
    description), bands 2..count+1 are the original bands unchanged, each
    carrying over its source `description` so e.g. `pr_2026_001` lands on
    band 2. The caller owns `tmp_path` and is responsible for deleting it
    once conversion is done — compare the return value against `tmp_path` to
    know whether a temporary file was actually created.

    Streams one band at a time (two passes over `src`: one to accumulate the
    mean, one to copy bands through) rather than loading every band into
    memory at once — a many-band file (e.g. 366 daily bands) previously had
    to fit entirely in RAM simultaneously as a masked array, which could use
    several hundred MB to multiple GB for one file and was a real cause of
    the pipeline getting OOM-killed on memory-constrained machines. Peak
    memory here is roughly one band plus two single-band accumulator arrays,
    regardless of how many bands the file has.
    """
    with rasterio.open(src) as ds:
        if ds.count <= 1:
            return src

        nodata = ds.nodata if ds.nodata is not None else float("nan")

        # Pass 1: nodata-aware running sum + valid-pixel count, one band at
        # a time — equivalent to the old masked `data.mean(axis=0)` but
        # without ever holding more than one band in memory.
        sum_ = np.zeros((ds.height, ds.width), dtype="float64")
        count = np.zeros((ds.height, ds.width), dtype="int32")
        for b in range(1, ds.count + 1):
            band = ds.read(b, masked=True)
            sum_ += np.ma.filled(band, 0.0).astype("float64")
            count += (~np.ma.getmaskarray(band)).astype("int32")

        with np.errstate(invalid="ignore", divide="ignore"):
            mean = np.where(count > 0, sum_ / count, nodata).astype("float32")

        profile = ds.profile.copy()
        profile.update(driver="GTiff", count=ds.count + 1, dtype="float32", nodata=nodata)

        tmp_path.parent.mkdir(parents=True, exist_ok=True)
        descriptions = ds.descriptions
        with rasterio.open(tmp_path, "w", **profile) as out:
            out.write(mean, 1)
            out.set_band_description(1, "mean")

            # Pass 2: copy each source band straight through to its output
            # slot, one band at a time.
            for i in range(1, ds.count + 1):
                band = ds.read(i, masked=True)
                band_filled = np.ma.filled(band, nodata)
                out.write(band_filled, i + 1)
                if descriptions[i - 1]:
                    out.set_band_description(i + 1, descriptions[i - 1])

    return tmp_path


def optimize_to_cog(src: Path, dst: Path, force: bool = False) -> bool:
    """Convert a GeoTIFF to an optimized, tiled GeoTIFF using gdal_translate.

    Multi-band sources (e.g. a daily time series for a year) get a synthetic
    "mean" band prepended, then every original band is preserved after it —
    TiTiler's `bidx` tile parameter lets the frontend pick whichever one it
    wants. A raster that already has a single band passes through unchanged.

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

    If `force` is True, an existing `dst` is deleted and rebuilt instead of
    being skipped — used to regenerate files produced by an older version of
    this pipeline (e.g. the old single-band-only squash, or the PIXEL-
    interleaved multi-band COG from before this fix).

    This is the one place raw→optimized conversion happens — both
    `cog_optimizer.py` (the pipeline's dedicated optimize step) and anything
    else that needs to (re)produce an optimized file call this, rather than
    each keeping its own copy of the conversion logic (two copies is how the
    `INTERLEAVE=PIXEL` bug above ended up fixed in one place and not the
    other for a while).
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        if not force:
            print(f"  ↳ Already optimized, skipping conversion: {dst.name}")
            return True
        dst.unlink()

    mean_tmp = dst.parent / f"_{dst.stem}.band_mean_tmp.tif"
    try:
        conversion_src = prepare_multiband_source(src, mean_tmp)
    except Exception as e:
        print(f"❌ Could not read {src.name}, skipping: {e}")
        return False

    is_multiband = conversion_src == mean_tmp

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
                str(conversion_src), str(dst)
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
                str(conversion_src), str(dst)
            ], check=True, capture_output=True)

        print(f"  ↳ Optimized → {dst.name}")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ COG conversion failed for {src.name}: {e.stderr}")
        return False
    finally:
        if conversion_src == mean_tmp and mean_tmp.exists():
            mean_tmp.unlink()


def is_stale_timeseries_output(src: Path, optimized: Path) -> bool:
    """True if an already-optimized file needs rebuilding because `src` is a
    genuine multi-band (time-series) source but `optimized` doesn't reflect
    the current pipeline shape — either it's still the old single-mean-band
    squash (band count doesn't match src's real band count + 1), or it's
    multi-band but still PIXEL-interleaved (the COG driver's hardcoded
    layout, which makes reading one band out of many require decompressing
    all of them — see optimize_to_cog's docstring).

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
            if ds.count != src_band_count + 1:
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

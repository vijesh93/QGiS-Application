"""
Shared helpers used before COG conversion.

Some source rasters (e.g. a daily time series for a whole year) carry many
bands in a single file instead of one band per layer. The rest of the
pipeline (TiTiler tile requests, the frontend's colormap/rescale handling)
assumes one band per registered layer, so multi-band sources are collapsed
to a single band here via an across-band mean before they're handed to
gdal_translate for COG conversion.

A raster that already has exactly one band is returned unchanged — this
keeps the pipeline generic for any future single-band drops without extra
flags or configuration.
"""

from pathlib import Path

import numpy as np
import rasterio


def prepare_single_band_source(src: Path, tmp_path: Path) -> Path:
    """Returns a Path to a single-band version of `src`, ready for gdal_translate.

    If `src` has exactly one band, `src` itself is returned untouched.
    If it has more than one band, the mean across all bands (nodata-aware)
    is written to `tmp_path` and that path is returned instead. The caller
    owns `tmp_path` and is responsible for deleting it once conversion is
    done — compare the return value against `tmp_path` to know whether a
    temporary file was actually created.
    """
    with rasterio.open(src) as ds:
        if ds.count <= 1:
            return src

        data = ds.read(masked=True)
        mean = data.mean(axis=0, dtype="float64").astype("float32")

        nodata = ds.nodata if ds.nodata is not None else float("nan")
        mean_filled = np.ma.filled(mean, nodata)

        profile = ds.profile.copy()
        profile.update(driver="GTiff", count=1, dtype="float32", nodata=nodata)

        tmp_path.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(tmp_path, "w", **profile) as out:
            out.write(mean_filled, 1)

    return tmp_path

# Per-band VRTs: why the time slider needed them

This explains a performance fix applied to the time-series raster layers (e.g. `pr_2026.tif`, a 366-band file: band 1 is a synthetic "mean" band, bands 2-366 are real daily values). If you're new to this codebase and the time slider, read this before touching `data/raster_utils.py`'s `generate_band_vrts()`, `frontend/src/api/layersApi.js`'s `buildBandVrtPath()`, or `frontend/src/features/map/MapView.jsx`'s `buildLayerTileUrl()`.

## What a GDAL VRT is

A `.vrt` ("Virtual Raster") is a small XML file that *describes* a raster instead of containing pixel data. It can say things like "this dataset has 1 band, and that band's pixels come from band 50 of `pr_2026.tif`, located at this path." GDAL, `rasterio`, and TiTiler can all open and read a `.vrt` exactly as if it were a real raster file — the indirection is transparent to anything that reads it. Building one is nearly instantaneous (no pixel data is copied, just a few KB of XML referencing the real file).

## The problem: TiTiler was slow on multi-band files, regardless of which band was requested

The time slider lets a user pick a day, which used to translate to a `bidx` (band index) query parameter on the tile request — e.g. "give me band 50 of `pr_2026.tif`." This measured at **~550-950ms per tile**, flat across every band and zoom level tested, versus **~30-80ms** for a genuinely single-band raster.

### Why: `rio-tiler` (which TiTiler is built on) always warps the whole dataset

Serving a reprojected tile requires a "warp" step (reprojecting the source CRS into the tile grid's CRS). The library TiTiler uses for this, `rio-tiler`, does this by wrapping the opened dataset in a `rasterio.vrt.WarpedVRT`:

```python
# rio_tiler/io/rasterio.py:120 (installed version: rio-tiler 9.4.6)
WarpedVRT(self.dataset, **vrt_options)
```

`self.dataset` here is the *entire* opened file — all 366 bands — not just the one band actually requested via `bidx`. Constructing a `WarpedVRT` sets up the reprojection machinery across every band in the dataset; only afterwards does `rio-tiler` read out the single band that was asked for. So reading band 50 out of a 366-band file still pays the cost of warping all 366 bands, every single time. This was confirmed directly, bypassing TiTiler/FastAPI entirely:

```python
# ~1.0-1.3s, regardless of which bidx:
with rasterio.open("pr_2026.tif") as src:
    with WarpedVRT(src, crs="EPSG:3857") as vrt:
        vrt.read(indexes=50, window=window)

# ~3ms:
with rasterio.open("pr_2026_band050_standalone.tif") as src:  # a real standalone single-band file
    with WarpedVRT(src, crs="EPSG:3857") as vrt:
        vrt.read(indexes=1, window=window)
```

There is no `rio-tiler` reader option to restrict which bands get wrapped before warping — this is how the `Reader` class is built, not a misconfiguration on our side. It's also the most likely explanation for a separately-observed symptom: TiTiler's memory climbing over a session of slider-scrubbing never fully released — every "one band" request was secretly processing data for all 366.

One thing this ruled out along the way: it is **not** a CRS-reprojection cost. `pr_2026.tif` is in EPSG:3035 (a true projected CRS); a standalone single-band extraction in that *same* EPSG:3035 CRS was just as fast (~30-80ms) as a reference single-band EPSG:4326 file. Reprojection itself is cheap — warping 366 bands to get 1 is what's expensive.

## The fix: give TiTiler a file that only has 1 band to warp

If the *file itself* only exposes one band, `WarpedVRT` only ever has one band to warp — there's nothing extra to pay for. So for every band of a multi-band layer, the pipeline now writes a tiny single-band `.vrt` pointing at just that band of the real file:

```bash
gdal_translate -of VRT -b 50 pr_2026.tif pr_2026_band050.vrt
```

Requesting a tile against `pr_2026_band050.vrt` instead of `pr_2026.tif?bidx=50` dropped the same tile request back down to **~35-75ms** — confirmed through the real TiTiler HTTP endpoint, not just the lower-level `rasterio` repro above.

### The portability gotcha

`gdal_translate` writes the VRT's `SourceFilename` as an **absolute path** by default. That breaks across this app's containers, because `./data` is mounted at different paths in different services: `/app` in `data-loader`, `/data` in `raster-server` (TiTiler). An absolute path baked in by whichever container generated the VRT wouldn't resolve in the other one.

The fix rewrites `SourceFilename` to a bare relative filename with `relativeToVRT="1"`, and always writes the VRT into the *same directory* as its source `.tif`. A relative reference like that resolves correctly no matter which container (or mount prefix) opens it, as long as the two files stay next to each other — which the naming/placement convention below guarantees by construction.

## The naming convention (must stay in sync on both ends)

Every band `n` (1..`band_count`, including the synthetic mean band at `n=1`) gets a VRT named `<stem>_band{n:03d}.vrt`, written next to its source optimized `.tif`. E.g. `pr_2026.tif`'s band 50 → `pr_2026_band050.vrt`, same directory.

This convention is implemented **twice**, once per language, and both must agree:
- **Write side** (Python, pipeline): `data/raster_utils.py`'s `generate_band_vrts()`, called from `data/register_layers.py` right after a layer's `band_count` is known.
- **Read side** (JS, frontend): `frontend/src/api/layersApi.js`'s `buildBandVrtPath(cogPath, band)`, called from `frontend/src/features/map/MapView.jsx`'s `buildLayerTileUrl()` whenever `layer.bandCount > 1`.

If you ever change the padding width, the `_band` separator, or where VRTs live relative to their source, update both functions together — nothing enforces they match except this convention.

Band 1 (the mean band) gets a VRT too, not just the real days — so a multi-band layer's tile requests *never* touch the big multi-band file directly, not even on first activation before the slider is touched.

## Why bands aren't separate database rows

A "layer" in `layer_metadata` stays exactly what it was before this fix: one row per dataset (e.g. `year_2026_pr_2026`), one sidebar entry, one legend row, one time slider. Bands remain a *sub-selection within* that one layer — exactly like the `bidx` parameter they replaced — never their own row.

No new database column, table, or API field was added for this. The per-band VRT path is fully deterministic from data already in the row (`file_path` + a band index the frontend already computes for the slider), so it's *computed* identically on both ends rather than stored anywhere. A more explicit alternative — a stored path template, or a child table mapping `(layer_id, band_index) → vrt_path` — was considered and rejected: it would add schema surface for something a simple, already-enforced naming convention fully solves, since every band from 1 to `band_count` always gets a VRT with no gaps or exceptions.

## Single-band layers are completely unaffected

`generate_band_vrts()` returns immediately when `band_count <= 1`. Static single-band rasters (e.g. `aspect/*`) never get any VRTs generated, and `buildLayerTileUrl()` only takes the VRT path when `layer.bandCount > 1` — otherwise it uses `layer.cog_path` directly, exactly as before this fix existed.

## Further reading

The full diagnostic trail — exact benchmark numbers, the `/cog/info` and `/cog/statistics` checks that ruled out dataset-open cost, the rejected hypotheses, and the raw investigation as it happened — is in `docs/temp.md`. This document is the summary; that one is the lab notebook.

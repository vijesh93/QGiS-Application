// api/layersApi.js

const BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

// TiTiler URL — browser calls this directly (not via Vite proxy).
// In dev: set VITE_TITILER_URL in .env file.
// In prod: set VITE_TITILER_URL to public TiTiler URL.
const TITILER_URL = import.meta.env.VITE_TITILER_URL;

// Reduces a layer's GeoJSON bbox polygon (`extent`, from the backend's
// ST_AsGeoJSON(bbox) — the layer's own raster file's real extent, not any
// assumed region) to a MapLibre raster-source `bounds` array
// [west, south, east, north], so MapLibre never requests tiles outside a
// layer's real data extent. Returns null when extent is missing (defensive
// only — every registered layer has one today), so the source falls back
// to MapLibre's default (no restriction) rather than breaking.
function extentToBounds(extent) {
  const ring = extent?.coordinates?.[0];
  if (!ring || ring.length === 0) return null;
  const lons = ring.map((c) => c[0]);
  const lats = ring.map((c) => c[1]);
  return [Math.min(...lons), Math.min(...lats), Math.max(...lons), Math.max(...lats)];
}

// ─── Normalise layer shape ───────────────────────────────────────────────────
function normaliseLayer(raw) {
  return {
    ...raw,
    name:        raw.display_name,
    cog_path:    raw.file_path,
    minZoom:     raw.min_zoom    ?? 0,
    maxZoom:     raw.max_zoom    ?? 22,
    isActive:    raw.is_active   ?? true,
    subcategory: raw.subcategory || '',
    description: raw.description || '',
    resolution:  raw.resolution  || null,
    year:        raw.year        || null,
    minValue:    raw.min_value   ?? null,
    maxValue:    raw.max_value   ?? null,
    bandCount:       raw.band_count          ?? 1,
    bandStartDate:   raw.band_start_date     ?? null,
    bandDateStepDays: raw.band_date_step_days ?? null,
    bandLabels:      raw.band_labels         ?? null,
    bandMode:        raw.band_mode           || 'sequence',
    bounds:      extentToBounds(raw.extent),
    tile_url:    null,
  };
}

export async function fetchCategories() {
  const r = await fetch(`${BASE_URL}/layers/categories`);
  if (!r.ok) throw new Error(`Failed to fetch categories: ${r.statusText}`);
  return r.json();
}

export async function fetchLayers() {
  const categories = await fetchCategories();
  const results = await Promise.all(
    categories.map((c) =>
      fetch(`${BASE_URL}/layers/?category=${encodeURIComponent(c.category)}`)
        .then((r) => { if (!r.ok) throw new Error(`Failed: ${c.category}`); return r.json(); })
    )
  );
  return results.flat().map(normaliseLayer);
}

export async function fetchRasterInventory() {
  const r = await fetch(`${BASE_URL}/layers/rasters/count`);
  if (!r.ok) throw new Error(`Failed to fetch raster count`);
  const data = await r.json();
  return { count: data.total_rasters };
}

// ─── Build TiTiler tile URL ──────────────────────────────────────────────────
// The browser calls TiTiler DIRECTLY on the host port (e.g. localhost:8080).
// This avoids any proxy encoding issues entirely.
//
// Final URL example:
//   http://localhost:{TITILER_PORT}/cog/tiles/WebMercatorQuad/{z}/{x}/{y}.png
//     ?url=/data/data_files/Optimized_Raster/aspectcosine_1KMma_SRTM.tif
//     &rescale=-1,1
//     &colormap_name=viridis
//     &bidx=2
//
// IMPORTANT: No encoding on url= or rescale= — plain string concatenation only.
//
// `bidx` selects which band a time-series layer's tiles come from (1..N are
// all real timesteps/values — see band_count/band_start_date/band_labels on
// the layer). Omitted entirely for single-band layers, so they're unaffected.
export function buildTileUrl(cogPath, rescale = '-1,1', colormap = 'viridis', bidx = null) {
  const bidxParam = bidx != null ? `&bidx=${bidx}` : '';
  return `${TITILER_URL}/cog/tiles/WebMercatorQuad/{z}/{x}/{y}.png?url=${cogPath}&rescale=${rescale}&colormap_name=${colormap}${bidxParam}`;
}

// Per-band VRT path for a multi-band/time-series layer, mirroring
// data/raster_utils.py's generate_band_vrts() naming convention exactly:
// `<stem>_band{NNN}.vrt`, co-located with its source .tif. Requesting tiles
// against this instead of `cogPath` + `bidx` avoids TiTiler/rio-tiler
// warping every band of the source file just to serve one — see
// docs/vrt_explainer.md. These two naming conventions must stay in sync.
export function buildBandVrtPath(cogPath, band) {
  const padded = String(band).padStart(3, '0');
  return cogPath.replace(/\.tif$/i, `_band${padded}.vrt`);
}

// ─── Point query (pixel values at a clicked location) ───────────────────────
// Used by the map's click-to-inspect popup. Queries the layer's main COG
// (not a per-band VRT — point queries need every band at once; VRTs are
// single-band-only, built solely for the time-slider's tile-serving
// performance fix, see buildBandVrtPath above), so one request returns
// every band's value in one shot.
//
// Returns the raw `values` array (positionally correct: band 1, band 2,
// ... — confirmed against gdalinfo), or null on ANY failure: a 404 (click
// outside this layer's real data extent despite passing the coarse
// `bounds` rectangle check — a bbox is a rectangle, real raster coverage
// can be smaller/irregular within it), a TiTiler error, or a network
// error. Deliberately never throws — a failed point query just means "no
// data here", not something that should crash the click handler or leave
// a popup stuck loading.
//
// NOTE: never read `band_descriptions` from this endpoint's response —
// confirmed buggy (repeats the last band's real description for every
// entry, cross-checked against gdalinfo and against /cog/info, which DOES
// return correct per-band descriptions). Only `values` is trustworthy
// here; zip it against the layer's own DB-sourced `bandLabels` instead.
export async function fetchPixelValues(cogPath, lng, lat) {
  try {
    const r = await fetch(`${TITILER_URL}/cog/point/${lng},${lat}?url=${cogPath}`);
    if (!r.ok) return null;
    const data = await r.json();
    return Array.isArray(data?.values) ? data.values : null;
  } catch {
    return null;
  }
}
// api/layersApi.js

const BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

// TiTiler URL — browser calls this directly (not via Vite proxy).
// In dev: set VITE_TITILER_URL=http://localhost:8080 in your .env file.
// In prod: set VITE_TITILER_URL to your public TiTiler URL.
const TITILER_URL = import.meta.env.VITE_TITILER_URL || 'http://localhost:8080';

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
//   http://localhost:8080/cog/tiles/WebMercatorQuad/{z}/{x}/{y}.png
//     ?url=/data/data_files/Optimized_Raster/aspectcosine_1KMma_SRTM.tif
//     &rescale=-1,1
//     &colormap_name=viridis
//
// IMPORTANT: No encoding on url= or rescale= — plain string concatenation only.
//
export function buildTileUrl(cogPath, rescale = '-1,1', colormap = 'viridis') {
  return `${TITILER_URL}/cog/tiles/WebMercatorQuad/{z}/{x}/{y}.png?url=${cogPath}&rescale=${rescale}&colormap_name=${colormap}`;
}
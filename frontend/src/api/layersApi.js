// api/layersApi.js
// Communicates with the FastAPI backend at /api/v1/

const BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

/**
 * Fetch all layer metadata from the backend.
 * Returns a list of layer objects with id, name, category, subcategory,
 * cog_path, tile_url, description, etc.
 */
export async function fetchLayers() {
  const response = await fetch(`${BASE_URL}/layers`);
  if (!response.ok) {
    throw new Error(`Failed to fetch layers: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Fetch layers filtered by category.
 */
export async function fetchLayersByCategory(category) {
  const response = await fetch(
    `${BASE_URL}/layers?category=${encodeURIComponent(category)}`
  );
  if (!response.ok) {
    throw new Error(`Failed to fetch layers by category: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Fetch metadata for a single layer by ID.
 */
export async function fetchLayerById(layerId) {
  const response = await fetch(`${BASE_URL}/layers/${layerId}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch layer ${layerId}: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Fetch all unique categories (for building the sidebar hierarchy).
 */
export async function fetchCategories() {
  const response = await fetch(`${BASE_URL}/layers/categories`);
  if (!response.ok) {
    // Fallback: derive categories from all layers
    const layers = await fetchLayers();
    const cats = [...new Set(layers.map((l) => l.category).filter(Boolean))];
    return cats.map((c) => ({ name: c }));
  }
  return response.json();
}

/**
 * Build a TiTiler tile URL for a given COG path.
 * TiTiler is accessible via the backend proxy or directly.
 *
 * Template:  /cog/tiles/{z}/{x}/{y}.png?url={cog_path}
 */
export function buildTileUrl(cogPath) {
  const tiTilerBase =
    process.env.REACT_APP_TITILER_URL || '/titiler';
  return `${tiTilerBase}/cog/tiles/{z}/{x}/{y}.png?url=${encodeURIComponent(cogPath)}`;
}

/**
 * Scan the optimized raster directory via the backend and return
 * the count and list of COG files found.
 */
export async function fetchRasterInventory() {
  const response = await fetch(`${BASE_URL}/layers/rasters/count`);
  if (!response.ok) {
    throw new Error(`Failed to fetch raster inventory: ${response.statusText}`);
  }
  return response.json();
  // Expected shape: { count: 500, files: ["path/to/file.tif", ...] }
}

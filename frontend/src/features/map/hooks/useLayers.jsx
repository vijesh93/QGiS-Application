// hooks/useLayers.js
// Manages all layer state: fetching, toggling, opacity, search

import { useState, useEffect, useCallback, useMemo } from 'react';
import { fetchLayers, fetchRasterInventory } from '../../../api/layersApi';

export function useLayers() {
  const [allLayers, setAllLayers] = useState([]);
  const [activeLayers, setActiveLayers] = useState({}); // { [layerId]: true/false }
  const [opacities, setOpacities] = useState({});        // { [layerId]: 0-100 }
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [rasterCount, setRasterCount] = useState(null);
  const [expandedCategories, setExpandedCategories] = useState({});

  // Load layers from backend on mount
  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const [layers, inventory] = await Promise.allSettled([
          fetchLayers(),
          fetchRasterInventory(),
        ]);

        if (layers.status === 'fulfilled') {
          const data = layers.value;
          setAllLayers(data);

          // Initialize opacities to 80% and all inactive
          const initOpacity = {};
          const initActive = {};
          const initExpanded = {};
          data.forEach((l) => {
            initOpacity[l.id] = 80;
            initActive[l.id] = false;
            if (l.category) initExpanded[l.category] = true;
          });
          setOpacities(initOpacity);
          setActiveLayers(initActive);
          setExpandedCategories(initExpanded);
        } else {
          throw layers.reason;
        }

        if (inventory.status === 'fulfilled') {
          setRasterCount(inventory.value.count);
        }
      } catch (err) {
        setError(err.message || 'Failed to load layers');
        // Use mock data for development if API is not available
        const mockLayers = generateMockLayers();
        setAllLayers(mockLayers);
        const initOpacity = {};
        const initActive = {};
        const initExpanded = {};
        mockLayers.forEach((l) => {
          initOpacity[l.id] = 80;
          initActive[l.id] = false;
          if (l.category) initExpanded[l.category] = true;
        });
        setOpacities(initOpacity);
        setActiveLayers(initActive);
        setExpandedCategories(initExpanded);
        setRasterCount(500);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  // Toggle a layer's visibility on/off
  const toggleLayer = useCallback((layerId) => {
    setActiveLayers((prev) => ({ ...prev, [layerId]: !prev[layerId] }));
  }, []);

  // Set opacity for a specific layer (0–100)
  const setLayerOpacity = useCallback((layerId, value) => {
    setOpacities((prev) => ({ ...prev, [layerId]: value }));
  }, []);

  // Toggle category collapse/expand
  const toggleCategory = useCallback((category) => {
    setExpandedCategories((prev) => ({
      ...prev,
      [category]: !prev[category],
    }));
  }, []);

  // Deactivate all layers
  const clearAllLayers = useCallback(() => {
    setActiveLayers((prev) => {
      const cleared = {};
      Object.keys(prev).forEach((k) => (cleared[k] = false));
      return cleared;
    });
  }, []);

  // Filtered + grouped layers for sidebar rendering
  const groupedLayers = useMemo(() => {
    const q = searchQuery.toLowerCase();
    const filtered = allLayers.filter(
      (l) =>
        !q ||
        l.name?.toLowerCase().includes(q) ||
        l.category?.toLowerCase().includes(q) ||
        l.subcategory?.toLowerCase().includes(q) ||
        l.description?.toLowerCase().includes(q)
    );

    // Group by category → subcategory
    const groups = {};
    filtered.forEach((layer) => {
      const cat = layer.category || 'Uncategorised';
      const sub = layer.subcategory || '';
      if (!groups[cat]) groups[cat] = {};
      if (!groups[cat][sub]) groups[cat][sub] = [];
      groups[cat][sub].push(layer);
    });
    return groups;
  }, [allLayers, searchQuery]);

  const activeCount = useMemo(
    () => Object.values(activeLayers).filter(Boolean).length,
    [activeLayers]
  );

  const activeLayersList = useMemo(
    () => allLayers.filter((l) => activeLayers[l.id]),
    [allLayers, activeLayers]
  );

  return {
    allLayers,
    activeLayers,
    opacities,
    loading,
    error,
    searchQuery,
    setSearchQuery,
    rasterCount,
    groupedLayers,
    expandedCategories,
    activeCount,
    activeLayersList,
    toggleLayer,
    setLayerOpacity,
    toggleCategory,
    clearAllLayers,
  };
}

// ─── Mock data for development without backend ─────────────────────────────
function generateMockLayers() {
  const categories = {
    Topography: {
      'Digital Elevation': ['DEM 1m', 'DEM 5m', 'DEM 10m', 'Hillshade', 'Slope Map', 'Aspect Map'],
      'Surface Models': ['DSM Urban', 'DSM Forest', 'nDSM Vegetation'],
    },
    'Land Use': {
      Agricultural: ['Cropland 2023', 'Vineyards', 'Orchards', 'Pastures', 'Fallow Land'],
      'Urban Areas': ['Settlements', 'Industrial Zones', 'Commercial Areas', 'Transport Infrastructure'],
      'Forest & Nature': ['Broadleaf Forest', 'Coniferous Forest', 'Mixed Forest', 'Wetlands', 'Heath'],
    },
    Hydrology: {
      'Surface Water': ['Rivers & Streams', 'Lakes & Reservoirs', 'Floodplains 100yr', 'Floodplains 10yr'],
      Groundwater: ['Groundwater Depth', 'Aquifer Zones', 'Protection Areas'],
    },
    Geology: {
      'Soil Types': ['Loam', 'Clay', 'Sandy Soil', 'Peat', 'Rock Outcrops'],
      Lithology: ['Quaternary', 'Tertiary', 'Mesozoic', 'Paleozoic'],
    },
    Climate: {
      Temperature: ['Mean Annual Temp', 'Summer Temp', 'Winter Temp', 'Heat Days'],
      Precipitation: ['Annual Rainfall', 'Winter Precipitation', 'Drought Index'],
    },
    Infrastructure: {
      Transport: ['Motorways', 'Federal Roads', 'Rail Network', 'Cycling Paths'],
      Energy: ['Power Grid', 'Wind Turbines', 'Solar Installations'],
    },
  };

  const layers = [];
  let id = 1;

  Object.entries(categories).forEach(([cat, subs]) => {
    Object.entries(subs).forEach(([sub, names]) => {
      names.forEach((name) => {
        layers.push({
          id: `layer_${id++}`,
          name,
          category: cat,
          subcategory: sub,
          description: `${name} raster layer for Baden-Württemberg`,
          cog_path: `/data/rasters/${cat.toLowerCase().replace(/\s/g, '_')}/${name.toLowerCase().replace(/\s/g, '_')}.tif`,
          tile_url: null,
          year: 2020 + Math.floor(Math.random() * 4),
          resolution: ['1m', '5m', '10m', '25m'][Math.floor(Math.random() * 4)],
        });
      });
    });
  });

  return layers;
}

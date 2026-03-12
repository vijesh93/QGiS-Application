// src/features/map/hooks/useLayers.jsx

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { fetchLayers, fetchRasterInventory } from '../../../api/layersApi';

export function useLayers() {
  const [allLayers, setAllLayers]               = useState([]);
  const [activeLayers, setActiveLayers]         = useState({});
  const [opacities, setOpacities]               = useState({});
  const [loading, setLoading]                   = useState(true);
  const [error, setError]                       = useState(null);
  const [searchQuery, setSearchQuery]           = useState('');
  const [rasterCount, setRasterCount]           = useState(null);
  const [expandedCategories, setExpandedCategories] = useState({});

  // ── Load layers on mount ───────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        setLoading(true);
        const [layers, inventory] = await Promise.allSettled([
          fetchLayers(),
          fetchRasterInventory(),
        ]);

        if (cancelled) return;

        if (layers.status === 'fulfilled') {
          const data = layers.value;
          setAllLayers(data);

          const initOpacity  = {};
          const initActive   = {};
          const initExpanded = {};
          data.forEach((l) => {
            initOpacity[l.id]  = 80;
            initActive[l.id]   = false;
            if (l.category) initExpanded[l.category] = true;
          });
          // Batch all three state updates — React 18 batches these automatically
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
        if (cancelled) return;
        setError(err.message || 'Failed to load layers');
        setRasterCount(0);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();
    return () => { cancelled = true; };
  }, []);

  // ── Stable callbacks — these never change identity ─────────────────────
  const toggleLayer = useCallback((layerId) => {
    setActiveLayers((prev) => ({ ...prev, [layerId]: !prev[layerId] }));
  }, []);

  const setLayerOpacity = useCallback((layerId, value) => {
    setOpacities((prev) => ({ ...prev, [layerId]: value }));
  }, []);

  const toggleCategory = useCallback((category) => {
    setExpandedCategories((prev) => ({ ...prev, [category]: !prev[category] }));
  }, []);

  const clearAllLayers = useCallback(() => {
    setActiveLayers((prev) => Object.fromEntries(Object.keys(prev).map((k) => [k, false])));
  }, []);

  // ── Derived state — memoised to avoid unnecessary recalculations ───────
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

  // ── activeLayersList: stable reference when content hasn't changed ─────
  // Without this, every call to setOpacities (e.g. moving opacity slider)
  // would create a new array → trigger MapView's sync useEffect → flicker.
  const activeLayersListRef = useRef([]);
  const activeLayersList = useMemo(() => {
    const next = allLayers.filter((l) => activeLayers[l.id]);
    // Only return a new array reference if the actual layer IDs changed
    const prev = activeLayersListRef.current;
    const sameIds =
      prev.length === next.length &&
      prev.every((l, i) => l.id === next[i].id);
    if (sameIds) return prev; // same reference → MapView sync effect won't re-run
    activeLayersListRef.current = next;
    return next;
  }, [allLayers, activeLayers]);

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

// ── Mock data fallback ─────────────────────────────────────────────────────
function generateMockLayers() {
  return [
    { id: 'mock_1', name: 'Aspectcosine 1KMma', category: 'Environment', subcategory: 'Aspect',
      description: '', cog_path: '', tile_url: null, minZoom: 0, maxZoom: 12 },
    { id: 'mock_2', name: 'Aspectcosine 1KMmi', category: 'Environment', subcategory: 'Aspect',
      description: '', cog_path: '', tile_url: null, minZoom: 0, maxZoom: 12 },
    { id: 'mock_3', name: 'Eastness 1KMma', category: 'Environment', subcategory: 'Eastness',
      description: '', cog_path: '', tile_url: null, minZoom: 0, maxZoom: 12 },
  ];
}
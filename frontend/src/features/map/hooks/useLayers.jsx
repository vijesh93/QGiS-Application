// src/features/map/hooks/useLayers.jsx

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { fetchLayers, fetchRasterInventory } from '../../../api/layersApi';

export function useLayers() {
  const [allLayers, setAllLayers]               = useState([]);
  const [activeLayers, setActiveLayers]         = useState({});
  const [opacities, setOpacities]               = useState({});
  const [selectedBands, setSelectedBands]       = useState({});
  const [loading, setLoading]                   = useState(true);
  const [error, setError]                       = useState(null);
  const [searchQuery, setSearchQuery]           = useState('');
  const [rasterCount, setRasterCount]           = useState(null);
  const [expandedCategories, setExpandedCategories] = useState({});
  // The one layer (if any) the user explicitly pinned to render above every
  // other active layer — see bringLayerToTop(). Exclusive by design: only
  // one layer can hold this at a time, which is exactly what makes "the
  // topmost layer" (both the physical map stacking and the pixel-value
  // click popup's target) unambiguous when several layers overlap.
  const [topmostLayerId, setTopmostLayerId]     = useState(null);
  // Real activation order of currently-active layers (oldest first, most
  // recently activated last) — mirrors exactly what MapLibre's own stacking
  // already does, since MapView only ever calls addLayer() at the moment a
  // layer is activated, which always renders it above everything already
  // present. This is DELIBERATELY separate from activeLayersList (the
  // panel's fixed display order): without this, "the default topmost
  // layer" could only be guessed from activeLayersList's fixed order, which
  // does not necessarily match which layer was actually activated most
  // recently — e.g. activating a layer that's earlier in that fixed order
  // after one that's later in it would make the two disagree about which
  // one is really on top. Tracking real order here keeps both the
  // pixel-popup's no-pin fallback and the "default topmost" UI highlight
  // (see MapPage.jsx/ActiveLayersLegend.jsx) accurate instead of
  // coincidentally-usually-right.
  const [zOrder, setZOrder] = useState([]);

  // Kept current for stable callbacks (applyMasterPercentage) that must read
  // the latest values without changing identity on every layer/toggle change.
  const allLayersRef    = useRef([]);
  const activeLayersRef = useRef({});
  useEffect(() => { allLayersRef.current = allLayers; }, [allLayers]);
  useEffect(() => { activeLayersRef.current = activeLayers; }, [activeLayers]);

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
          const initBand     = {};
          data.forEach((l) => {
            initOpacity[l.id]  = 80;
            initActive[l.id]   = false;
            initBand[l.id]     = 1; // band 1 = first timestep (or the only band)
            if (l.category) initExpanded[l.category] = true;
          });
          // Batch all state updates — React 18 batches these automatically
          setOpacities(initOpacity);
          setActiveLayers(initActive);
          setExpandedCategories(initExpanded);
          setSelectedBands(initBand);
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
    const wasActive = activeLayersRef.current[layerId];
    setActiveLayers((prev) => ({ ...prev, [layerId]: !prev[layerId] }));
    if (wasActive) {
      // Being turned off — release the "bring to top" pin if it was this
      // layer's (reactivating it later shouldn't silently restore special
      // treatment the user never re-requested), and drop it from zOrder.
      setTopmostLayerId((prev) => (prev === layerId ? null : prev));
      setZOrder((prev) => prev.filter((id) => id !== layerId));
    } else {
      // Being turned on — it's now the most-recently-activated layer,
      // i.e. the new default topmost, exactly matching where MapView's
      // sync effect is about to render it (map.addLayer() always appends
      // above everything already present).
      setZOrder((prev) => (prev.includes(layerId) ? prev : [...prev, layerId]));
    }
  }, []);

  // Pins `layerId` as the one layer rendered above every other active
  // layer (both on the map and as the pixel-value click popup's target —
  // see activeLayersList below and MapView.jsx's layer-order effect).
  // Toggle behavior: clicking the already-pinned layer's button again
  // releases the pin, falling back to the default (unpinned) order.
  const bringLayerToTop = useCallback((layerId) => {
    setTopmostLayerId((prev) => (prev === layerId ? null : layerId));
  }, []);

  const setLayerOpacity = useCallback((layerId, value) => {
    setOpacities((prev) => ({ ...prev, [layerId]: value }));
  }, []);

  const setLayerBand = useCallback((layerId, bandIndex) => {
    setSelectedBands((prev) => ({ ...prev, [layerId]: bandIndex }));
  }, []);

  // Maps a 0-100% master position independently onto each active multi-band
  // layer's own band range: 0% = band 1 (first timestep) for every layer,
  // 100% = each layer's own last band. Layers with bandCount <= 1, and
  // distribution-mode layers (band_mode === 'distribution', e.g. median/
  // p17/p83/... statistics), are left untouched — the former have nothing
  // to scrub, the latter must always stay pinned to band 1 (the map-click
  // popup is how their other bands surface, never the slider).
  const applyMasterPercentage = useCallback((pct) => {
    setSelectedBands((prev) => {
      const next = { ...prev };
      allLayersRef.current.forEach((layer) => {
        if (!activeLayersRef.current[layer.id]) return;
        if (!layer.bandCount || layer.bandCount <= 1) return;
        if (layer.bandMode === 'distribution') return;
        const band = 1 + Math.round((pct / 100) * (layer.bandCount - 1));
        next[layer.id] = Math.min(layer.bandCount, Math.max(1, band));
      });
      return next;
    });
  }, []);

  const toggleCategory = useCallback((category) => {
    setExpandedCategories((prev) => ({ ...prev, [category]: !prev[category] }));
  }, []);

  const clearAllLayers = useCallback(() => {
    setActiveLayers((prev) => Object.fromEntries(Object.keys(prev).map((k) => [k, false])));
    setZOrder([]);
    setTopmostLayerId(null);
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
    // Subcategories otherwise render in whatever order the API happened to
    // return them in (DB/filesystem traversal order, not alphabetical) —
    // re-sort so e.g. BIO01/BIO05/BIO06/BIO12 always appear in a predictable
    // order. `numeric: true` sorts BIO2 before BIO10 (not lexicographically).
    Object.keys(groups).forEach((cat) => {
      const sortedSub = {};
      Object.keys(groups[cat])
        .sort((a, b) => a.localeCompare(b, undefined, { numeric: true }))
        .forEach((sub) => {
          sortedSub[sub] = groups[cat][sub];
        });
      groups[cat] = sortedSub;
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
  //
  // This is also the Active Layers panel's display order — deliberately
  // NEVER reordered by topmostLayerId. An earlier version moved the pinned
  // layer to the end of this array, which doubled as "which layer is
  // topmost" for MapView, but that made a layer visibly jump to the bottom
  // of its own list the moment you pinned it — confusing, since pinning is
  // about map stacking, not where the layer sits in this list. MapView now
  // takes topmostLayerId as its own separate prop and moves that layer on
  // the actual map without touching this array at all; list position and
  // map z-order are independent, as they should be.
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

  // Real-order layer objects (oldest-activated first), for MapView's
  // pixel-popup fallback to walk when no layer is explicitly pinned.
  const zOrderedLayers = useMemo(
    () => zOrder.map((id) => allLayers.find((l) => l.id === id)).filter(Boolean),
    [zOrder, allLayers]
  );

  // The layer that's topmost right now with no explicit pin — the most
  // recently activated one still active, or null if nothing's active yet.
  // Exposed so the UI can highlight "this is currently on top" even before
  // the user ever clicks a "TOP" badge, not just after pinning one.
  const defaultTopmostLayerId = zOrderedLayers.length
    ? zOrderedLayers[zOrderedLayers.length - 1].id
    : null;

  // Whether the master time control has anything to actually do right now.
  // applyMasterPercentage already silently no-ops for single-band and
  // distribution-mode (median/p17/p83/...) layers — dragging the slider
  // with only those active would visibly do nothing, which is more
  // confusing than just not showing a control that can't act on anything.
  // Sequence-mode multi-band layers (today: none active by default, since
  // the old time-series/near-medium-far data was retired — see the Nov
  // 2026 KliMP re-delivery) are the only thing this control affects.
  const hasActiveSequenceLayer = useMemo(
    () => activeLayersList.some((l) => l.bandCount > 1 && l.bandMode !== 'distribution'),
    [activeLayersList]
  );

  return {
    allLayers,
    activeLayers,
    opacities,
    selectedBands,
    loading,
    error,
    searchQuery,
    setSearchQuery,
    rasterCount,
    groupedLayers,
    expandedCategories,
    activeCount,
    activeLayersList,
    zOrderedLayers,
    topmostLayerId,
    defaultTopmostLayerId,
    hasActiveSequenceLayer,
    bringLayerToTop,
    toggleLayer,
    setLayerOpacity,
    setLayerBand,
    applyMasterPercentage,
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
import React, { useEffect, useRef, useState } from 'react';
import maplibregl from 'maplibre-gl';
import { buildTileUrl, buildBandVrtPath, fetchPixelValues } from '../../api/layersApi';
import PixelValuePopup from '../../components/PixelValuePopup';

const toMapId = (id) => `layer_${id}`;

// True if `lng,lat` falls inside `bounds` ([west,south,east,north]), or
// always true when bounds is null/undefined — matches the "no restriction"
// meaning MapView already gives a null bounds everywhere else (see the
// `...(layer.bounds ? { bounds: layer.bounds } : {})` source option below).
function coversPoint(bounds, lng, lat) {
  if (!bounds) return true;
  const [west, south, east, north] = bounds;
  return lng >= west && lng <= east && lat >= south && lat <= north;
}

// Resolves which active layer is "topmost" at a given point — the single
// source of truth for this, used both by the click handler (to open a new
// popup) and by the pin-change effect below (to re-target an already-open
// one), so the two can never disagree about what "topmost" means.
//
// Priority order:
//  1. An explicit pin (topmostLayerId) wins if it's active and covers this
//     point — that's the whole point of pinning, regardless of where it
//     falls in zOrderedLayers (list position and map stacking are
//     deliberately independent — see useLayers.jsx).
//  2. Otherwise, zOrderedLayers — real activation order, oldest first —
//     walked end-to-start, so the most-recently-activated layer whose
//     bounds (coarse, rectangular) cover the point wins. This mirrors
//     exactly what MapLibre's own stacking already does (map.addLayer()
//     always appends above everything present).
// Returns null if nothing active covers this point.
function resolveTopmostLayer(zOrderedLayers, pinnedId, lng, lat) {
  if (pinnedId != null) {
    const pinned = zOrderedLayers.find((l) => l.id === pinnedId);
    if (pinned && coversPoint(pinned.bounds, lng, lat)) return pinned;
  }
  for (let i = zOrderedLayers.length - 1; i >= 0; i--) {
    if (coversPoint(zOrderedLayers[i].bounds, lng, lat)) return zOrderedLayers[i];
  }
  return null;
}

// Rough footprint used only to keep the popup from overflowing the map
// container on clicks near an edge — doesn't need to be exact, just in
// the right ballpark.
const POPUP_WIDTH_ESTIMATE  = 280;
const POPUP_HEIGHT_ESTIMATE = 180;
const POPUP_OFFSET = 12;

// Plain DOM element for the pixel-value marker — a maplibregl.Marker isn't
// a React component, so this can't be styled via JSX. A small ringed dot
// in the same accent yellow (#FFFC00) the popup already uses for values,
// with a dark border so it stays visible against any raster colormap
// underneath. pointerEvents: 'none' so the marker itself never blocks a
// later click on the same spot (it has no interactive purpose — dragging
// it would desync it from the popup's actual query point).
function createMarkerElement() {
  const el = document.createElement('div');
  el.style.width = '14px';
  el.style.height = '14px';
  el.style.borderRadius = '50%';
  el.style.background = '#FFFC00';
  el.style.border = '2px solid #2A2623';
  el.style.boxShadow = '0 0 0 2px rgba(255,252,0,0.45), 0 2px 6px rgba(0,0,0,0.6)';
  el.style.pointerEvents = 'none';
  return el;
}

// Builds this layer's tile URL, including its own rescale and (when it's a
// multi-band/time-series layer) the currently-selected band. Multi-band
// layers are requested against a per-band VRT (see buildBandVrtPath) rather
// than the big multi-band file + `bidx` — the VRT exposes exactly one band,
// so TiTiler never warps the other N-1 bands just to serve this one (see
// docs/vrt_explainer.md).
function buildLayerTileUrl(layer, selectedBand) {
  const rescale = (layer.minValue != null && layer.maxValue != null)
    ? `${layer.minValue},${layer.maxValue}`
    : undefined;
  if (layer.bandCount > 1) {
    const vrtPath = buildBandVrtPath(layer.cog_path, selectedBand ?? 1);
    return buildTileUrl(vrtPath, rescale, undefined, null);
  }
  return buildTileUrl(layer.cog_path, rescale, undefined, null);
}

// We keep opacities/selectedBands in refs (not just props) so their effects
// don't cause the add/remove sync effect to re-run.
const MapView = ({ BaseMapTransparency, activeLayersList, zOrderedLayers, opacities, selectedBands, topmostLayerId }) => {
  const mapContainer     = useRef(null);
  const mapRef           = useRef(null);
  const mapReadyRef      = useRef(false);   // true once 'load' has fired
  const addedLayers      = useRef(new Set());
  const opacitiesRef     = useRef(opacities);
  const selectedBandsRef = useRef(selectedBands);
  const zOrderedLayersRef = useRef(zOrderedLayers);
  const topmostLayerIdRef = useRef(topmostLayerId);
  const lastBandRef      = useRef({});      // mapId → last-applied bidx, to skip no-op updates
  const pendingSyncRef   = useRef(null);    // queued sync call waiting for map load
  const clickSeqRef      = useRef(0);       // guards against a stale point-query response
                                             // landing after a newer click superseded it
  const markerRef        = useRef(null);    // the single maplibregl.Marker marking whichever
                                             // pixel the popup (if any) is currently showing
  const pixelPopupRef    = useRef(null);    // mirrors pixelPopup state, read (not written) by
                                             // the "re-target on topmost change" effect below

  // Pixel-value popup state: null when no popup is shown, otherwise
  // { x, y, layer, values, loading, error }. `values` holds every band's
  // value (fetched once, in one point query) regardless of band_mode — the
  // popup re-derives which row(s) to show from `layer.bandMode` and the
  // live `selectedBands` prop, so moving the time slider while the popup
  // is open re-indexes into the already-fetched `values` with no refetch.
  const [pixelPopup, setPixelPopup] = useState(null);

  // Detaches the pixel marker (if any) from the map without discarding the
  // Marker instance — it's cheap to re-attach via .setLngLat().addTo(map)
  // on the next click, so there's no need to recreate the DOM element
  // every time the popup closes and reopens.
  const removeMarker = () => {
    if (markerRef.current) {
      markerRef.current.remove();
    }
  };

  // Keep opacitiesRef/selectedBandsRef/zOrderedLayersRef current without
  // triggering effects
  useEffect(() => {
    opacitiesRef.current = opacities;
  });
  useEffect(() => {
    selectedBandsRef.current = selectedBands;
  });
  useEffect(() => {
    zOrderedLayersRef.current = zOrderedLayers;
  });
  useEffect(() => {
    topmostLayerIdRef.current = topmostLayerId;
  });
  useEffect(() => {
    pixelPopupRef.current = pixelPopup;
  });

  // Auto-dismiss the popup if its layer gets toggled off (or otherwise
  // drops out of activeLayersList) while it's open — showing a popup for a
  // layer that's no longer on the map would be confusing.
  useEffect(() => {
    if (pixelPopup && !activeLayersList.some((l) => l.id === pixelPopup.layer.id)) {
      setPixelPopup(null);
      removeMarker();
    }
  }, [activeLayersList, pixelPopup]);

  // ── Init map (runs exactly once) ───────────────────────────────────────
  useEffect(() => {
    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: {
        version: 8,
        sources: {
          osm: {
            type: 'raster',
            tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
            tileSize: 256,
            attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
          },
        },
        layers: [{ id: 'osm-layer', type: 'raster', source: 'osm' }],
      },
      center: [9.18, 48.77],
      zoom: 8,
    });

    map.addControl(new maplibregl.NavigationControl({ showCompass: true }), 'top-right');
    map.addControl(new maplibregl.ScaleControl({ maxWidth: 120, unit: 'metric' }), 'bottom-right');

    // ── Click-to-inspect: topmost active layer covering the clicked point ──
    // Zero active layers, or none covering this point, is a silent no-op:
    // no popup, nothing to show, no change from today's click behavior.
    map.on('click', (e) => {
      const zOrdered = zOrderedLayersRef.current;
      if (!zOrdered || zOrdered.length === 0) return;

      const { lng, lat } = e.lngLat;
      const topmost = resolveTopmostLayer(zOrdered, topmostLayerIdRef.current, lng, lat);
      if (!topmost) return;

      const seq = ++clickSeqRef.current;
      const containerEl = mapContainer.current;
      const maxX = containerEl ? Math.max(8, containerEl.clientWidth - POPUP_WIDTH_ESTIMATE - 8) : e.point.x;
      const maxY = containerEl ? Math.max(8, containerEl.clientHeight - POPUP_HEIGHT_ESTIMATE - 8) : e.point.y;

      // Mark the exact clicked coordinate so it's unambiguous which pixel
      // the popup's values came from. One Marker instance is reused across
      // clicks (just moved) rather than recreated each time.
      if (!markerRef.current) {
        markerRef.current = new maplibregl.Marker({ element: createMarkerElement(), anchor: 'center' });
      }
      markerRef.current.setLngLat([lng, lat]).addTo(map);

      // lng/lat are kept on the popup (not just used for this fetch) so
      // that later changing which layer is topmost — via the "TOP" button,
      // without a new map click — can re-query the same pixel against the
      // newly-topmost layer instead of leaving stale values on screen; see
      // the "re-target the open popup" effect below.
      setPixelPopup({
        x: Math.min(e.point.x + POPUP_OFFSET, maxX),
        y: Math.min(e.point.y + POPUP_OFFSET, maxY),
        lng, lat,
        layer: topmost,
        values: null,
        loading: true,
        error: false,
      });

      fetchPixelValues(topmost.cog_path, lng, lat).then((values) => {
        if (clickSeqRef.current !== seq) return; // superseded by a newer click
        setPixelPopup((prev) => (
          prev && prev.layer.id === topmost.id
            ? { ...prev, values, loading: false, error: values === null }
            : prev
        ));
      });
    });

    map.once('load', () => {
      mapReadyRef.current = true;
      mapRef.current = map;
      // If a sync was queued before the map finished loading, run it now
      if (pendingSyncRef.current) {
        pendingSyncRef.current();
        pendingSyncRef.current = null;
      }
    });

    return () => {
      mapReadyRef.current = false;
      if (markerRef.current) {
        markerRef.current.remove();
        markerRef.current = null;
      }
      map.remove();
      mapRef.current = null;
    };
  }, []); // ← empty deps: init once, never re-run

  // ── Base map transparency ──────────────────────────────────────────────
  useEffect(() => {
    if (!mapReadyRef.current || !mapRef.current) return;
    const map = mapRef.current;
    if (map.getLayer('osm-layer')) {
      map.setPaintProperty('osm-layer', 'raster-opacity', BaseMapTransparency / 100);
    }
  }, [BaseMapTransparency]);

  // ── Sync COG layers when active list changes ───────────────────────────
  useEffect(() => {
    const doSync = () => {
      const map = mapRef.current;
      if (!map) return;

      const activeMapIds = new Set(activeLayersList.map((l) => toMapId(l.id)));

      // Remove layers no longer active
      addedLayers.current.forEach((mapId) => {
        if (!activeMapIds.has(mapId)) {
          try {
            if (map.getLayer(mapId))  map.removeLayer(mapId);
            if (map.getSource(mapId)) map.removeSource(mapId);
          } catch (e) { /* ignore */ }
          addedLayers.current.delete(mapId);
        }
      });

      // Add newly activated layers
      activeLayersList.forEach((layer) => {
        const mapId = toMapId(layer.id);
        if (addedLayers.current.has(mapId)) return;

        // Each layer gets its own color stretch from its real data range
        // (falls back to buildTileUrl's default if not yet registered with a
        // min/max), and — for multi-band/time-series layers — its currently
        // selected band via bidx (defaults to band 1, the first timestep).
        const initialBand = selectedBandsRef.current[layer.id] ?? 1;
        const tileUrl = buildLayerTileUrl(layer, initialBand);
        console.log(`Adding "${layer.name}" → ${tileUrl}`);

        try {
          map.addSource(mapId, {
            type:     'raster',
            tiles:    [tileUrl],
            tileSize: 256,
            minzoom:  0,
            maxzoom:  22, // Let MapLibre request tiles at any zoom; TiTiler handles overviews
            // Stops MapLibre from requesting tiles outside this layer's real
            // data extent at all (panning/zooming elsewhere issues zero
            // requests for it) — see layersApi.js's extentToBounds().
            ...(layer.bounds ? { bounds: layer.bounds } : {}),
          });
          map.addLayer({
            id:     mapId,
            type:   'raster',
            source: mapId,
            paint: {
              'raster-opacity':       (opacitiesRef.current[layer.id] ?? 80) / 100,
              'raster-fade-duration': 300,
            },
          });
          addedLayers.current.add(mapId);
          lastBandRef.current[mapId] = initialBand;
          console.log(`✓ "${layer.name}" added`);
        } catch (err) {
          console.error(`✗ "${layer.name}" failed:`, err.message);
        }
      });
    };

    if (mapReadyRef.current) {
      // Map already loaded — sync immediately
      doSync();
    } else {
      // Map still loading — queue the sync; the 'load' handler above will call it
      pendingSyncRef.current = doSync;
    }
  }, [activeLayersList]); // ← only re-runs when the list of active layers actually changes

  // ── Keep the pinned layer (if any) physically on top ────────────────────
  // Only acts when the user has explicitly pinned a layer via the "TOP"
  // button (topmostLayerId) — with no pin, map stacking is left exactly as
  // MapLibre's natural insertion order already has it, unchanged from
  // before this feature existed. A brand-new layer already lands on top
  // for free (map.addLayer() always appends above everything existing),
  // but re-promoting an ALREADY-rendered layer — the pin button's actual
  // use case — needs an explicit moveLayer() call, since the sync effect
  // above skips any layer already in addedLayers. Runs after that effect
  // (declared later → same commit, later order) so it always sees the
  // layer it's about to move already added.
  useEffect(() => {
    if (!mapReadyRef.current || !mapRef.current) return;
    if (topmostLayerId == null) return;
    if (!activeLayersList.some((l) => l.id === topmostLayerId)) return;
    const map = mapRef.current;
    const mapId = toMapId(topmostLayerId);
    try {
      if (map.getLayer(mapId)) map.moveLayer(mapId); // no beforeId = move to very top
    } catch (e) { /* ignore */ }
  }, [activeLayersList, topmostLayerId]);

  // ── Re-target an already-open popup when "topmost" changes ──────────────
  // Without this, pinning a different layer via the "TOP" button (or simply
  // activating/deactivating layers, which shifts the natural z-order) left
  // an open popup showing stale values for whichever layer used to be
  // topmost — the only way to see another overlapping layer's values was to
  // click the map again. Re-resolves topmost at the SAME lng/lat the popup
  // is already anchored to (not a new click point) and, if that's actually
  // a different layer than what's currently shown, re-fetches for it.
  // zOrderedLayers is read directly (not via its ref) since this effect's
  // own dependency array already guarantees it's current whenever this
  // runs; pixelPopup is read via its ref instead, specifically so this
  // effect does NOT also fire on every popup update (only on a real
  // topmost-affecting change), which would otherwise re-run immediately
  // after its own setPixelPopup call below for no reason.
  useEffect(() => {
    const prevPopup = pixelPopupRef.current;
    if (!prevPopup) return; // no popup open — nothing to re-target

    const resolved = resolveTopmostLayer(zOrderedLayers, topmostLayerId, prevPopup.lng, prevPopup.lat);
    if (!resolved || resolved.id === prevPopup.layer.id) return; // unchanged

    const seq = ++clickSeqRef.current;
    setPixelPopup((p) => (p ? { ...p, layer: resolved, values: null, loading: true, error: false } : p));

    fetchPixelValues(resolved.cog_path, prevPopup.lng, prevPopup.lat).then((values) => {
      if (clickSeqRef.current !== seq) return; // superseded by a newer click/re-target
      setPixelPopup((p) => (
        p && p.layer.id === resolved.id
          ? { ...p, values, loading: false, error: values === null }
          : p
      ));
    });
  }, [topmostLayerId, zOrderedLayers]);

  // ── Update opacity on already-added layers ─────────────────────────────
  useEffect(() => {
    if (!mapReadyRef.current || !mapRef.current) return;
    const map = mapRef.current;

    addedLayers.current.forEach((mapId) => {
      const rawId  = mapId.replace('layer_', '');
      // opacities keyed by original id which may be number or string
      const opacity = opacities[rawId] ?? opacities[Number(rawId)] ?? 80;
      try {
        if (map.getLayer(mapId))
          map.setPaintProperty(mapId, 'raster-opacity', opacity / 100);
      } catch (e) { /* ignore */ }
    });
  }, [opacities]);

  // ── Swap tile band on already-added layers (time slider) ───────────────
  // Updates the source's tile URL template in place via setTiles() — no
  // remove/re-add, no flicker — only for layers whose resolved band index
  // actually changed since it was last applied.
  useEffect(() => {
    if (!mapReadyRef.current || !mapRef.current) return;
    const map = mapRef.current;

    activeLayersList.forEach((layer) => {
      if (!layer.bandCount || layer.bandCount <= 1) return;
      const mapId = toMapId(layer.id);
      if (!addedLayers.current.has(mapId)) return;

      const band = selectedBands[layer.id] ?? 1;
      if (lastBandRef.current[mapId] === band) return;

      try {
        const source = map.getSource(mapId);
        if (source) {
          source.setTiles([buildLayerTileUrl(layer, band)]);
          lastBandRef.current[mapId] = band;
        }
      } catch (e) { /* ignore */ }
    });
  }, [selectedBands, activeLayersList]);

  return (
    <>
      <div
        ref={mapContainer}
        style={{ flex: 1, height: '100%', width: '100%' }}
      />
      {pixelPopup && (
        <PixelValuePopup
          x={pixelPopup.x}
          y={pixelPopup.y}
          layer={pixelPopup.layer}
          selectedBand={selectedBands[pixelPopup.layer.id] ?? 1}
          values={pixelPopup.values}
          loading={pixelPopup.loading}
          error={pixelPopup.error}
          onClose={() => { setPixelPopup(null); removeMarker(); }}
        />
      )}
    </>
  );
};

export default MapView;
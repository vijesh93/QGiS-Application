import React, { useEffect, useRef, useCallback } from 'react';
import maplibregl from 'maplibre-gl';
import { buildTileUrl, buildBandVrtPath } from '../../api/layersApi';

const toMapId = (id) => `layer_${id}`;

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
const MapView = ({ BaseMapTransparency, activeLayersList, opacities, selectedBands }) => {
  const mapContainer     = useRef(null);
  const mapRef           = useRef(null);
  const mapReadyRef      = useRef(false);   // true once 'load' has fired
  const addedLayers      = useRef(new Set());
  const opacitiesRef     = useRef(opacities);
  const selectedBandsRef = useRef(selectedBands);
  const lastBandRef      = useRef({});      // mapId → last-applied bidx, to skip no-op updates
  const pendingSyncRef   = useRef(null);    // queued sync call waiting for map load

  // Keep opacitiesRef/selectedBandsRef current without triggering effects
  useEffect(() => {
    opacitiesRef.current = opacities;
  });
  useEffect(() => {
    selectedBandsRef.current = selectedBands;
  });

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
        // selected band via bidx (defaults to band 1, the "Mean" band).
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
    <div
      ref={mapContainer}
      style={{ flex: 1, height: '100%', width: '100%' }}
    />
  );
};

export default MapView;
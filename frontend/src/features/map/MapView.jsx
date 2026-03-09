import React, { useEffect, useRef, useCallback } from 'react';
import maplibregl from 'maplibre-gl';
import { buildTileUrl } from '../../api/layersApi';

const toMapId = (id) => `layer_${id}`;

// We keep opacities in a ref (not just prop) so the opacity effect
// doesn't cause the sync effect to re-run.
const MapView = ({ BaseMapTransparency, activeLayersList, opacities }) => {
  const mapContainer    = useRef(null);
  const mapRef          = useRef(null);
  const mapReadyRef     = useRef(false);   // true once 'load' has fired
  const addedLayers     = useRef(new Set());
  const opacitiesRef    = useRef(opacities);
  const pendingSyncRef  = useRef(null);    // queued sync call waiting for map load

  // Keep opacitiesRef current without triggering effects
  useEffect(() => {
    opacitiesRef.current = opacities;
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

        const tileUrl = buildTileUrl(layer.cog_path);
        console.log(`Adding "${layer.name}" → ${tileUrl}`);

        try {
          map.addSource(mapId, {
            type:     'raster',
            tiles:    [tileUrl],
            tileSize: 256,
            minzoom:  0,
            maxzoom:  22, // Let MapLibre request tiles at any zoom; TiTiler handles overviews
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

  return (
    <div
      ref={mapContainer}
      style={{ flex: 1, height: '100%', width: '100%' }}
    />
  );
};

export default MapView;
import React, { useEffect, useRef } from 'react';
import maplibregl from 'maplibre-gl';


const MapView = ({ transparency }) => {
  const mapContainer = useRef(null);
  const mapRef = useRef(null);

  useEffect(() => {
    mapRef.current = new maplibregl.Map({
      container: mapContainer.current,
      style: {
        version: 8,
        sources: {
          'osm': { type: 'raster', tiles: ['https://a.tile.openstreetmap.org/{z}/{x}/{y}.png'], tileSize: 256 }
        },
        layers: [{ id: 'osm-layer', type: 'raster', source: 'osm' }]
      },
      center: [9.18, 48.77],
      zoom: 8
    });
    return () => mapRef.current.remove();
  }, []);

  // Use another useEffect to react to transparency changes without reloading the whole map
  useEffect(() => {
    if (mapRef.current && mapRef.current.getLayer('osm-layer')) {
      mapRef.current.setPaintProperty('osm-layer', 'raster-opacity', transparency / 100);
    }
  }, [transparency]);

  return <div ref={mapContainer} style={{ flex: 1 }} />;
};

export default MapView;
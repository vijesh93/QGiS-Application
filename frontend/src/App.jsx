import React, { useEffect, useRef } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

function App() {
  const mapContainer = useRef(null);

  useEffect(() => {
    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: {
        version: 8,
        sources: {
          'osm': {
            type: 'raster',
            tiles: ['https://a.tile.openstreetmap.org/{z}/{x}/{y}.png'],
            tileSize: 256,
            attribution: '&copy; OpenStreetMap Contributors'
          }
        },
        layers: [
          {
            id: 'osm-layer',
            type: 'raster',
            source: 'osm'
          }
        ],
        center: [9.18, 48.77], // Center on Stuttgart, BW
        zoom: 8
      }
    });

    // Clean up on unmount
    return () => map.remove();
  }, []);

  return (
    <div style={{ width: '100vw', height: '100vh', display: 'flex' }}>
      <div style={{ width: '300px', background: '#f0f0f0', padding: '1rem' }}>
        <h2>BW Geoportal</h2>
        <p>450 Layers Loading...</p>
      </div>
      <div ref={mapContainer} style={{ flex: 1 }} />
    </div>
  );
}

export default App;
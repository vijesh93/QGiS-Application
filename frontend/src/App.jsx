import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import MapView from './features/map/MapView';
import 'maplibre-gl/dist/maplibre-gl.css';

function App() {
  const [transparency, setTransparency] = useState(100);

  return (
    <div style={{ width: '100vw', height: '100vh', display: 'flex' }}>
      <Sidebar transparency={transparency} setTransparency={setTransparency} />
      <MapView transparency={transparency} />
    </div>
  );
}

export default App;
import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import MapView from './features/map/MapView';
import { useLayers } from './features/map/hooks/useLayers'; // frontend\src\features\map\hooks\useLayers.js
import 'maplibre-gl/dist/maplibre-gl.css';


function App() {
  const [BaseMaptransparency, setBaseMapTransparency] = useState(100);
    const {
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
  } = useLayers();

  return (
    /*
      <Sidebar transparency={transparency} setTransparency={setTransparency} />      
      <MapView transparency={transparency} />
    */
    <div style={{ width: '100vw', height: '100vh', display: 'flex' }}>
      <Sidebar 
        BaseMapTransparency={BaseMaptransparency} 
        setBaseMapTransparency={setBaseMapTransparency} 
      />
      <MapView 
        BaseMapTransparency={BaseMaptransparency}
        activeLayersList={activeLayersList}
        opacities={opacities}
      />
    </div>
  );
}

export default App;
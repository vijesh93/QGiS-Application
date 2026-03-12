import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import MapView from './features/map/MapView';
import ActiveLayersLegend from './components/ActiveLayersLegend';
import { useLayers } from './features/map/hooks/useLayers';
import 'maplibre-gl/dist/maplibre-gl.css';

function App() {
  const [BaseMapTransparency, setBaseMapTransparency] = useState(100);

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
    <div style={{ width: '100vw', height: '100vh', display: 'flex' }}>
      <Sidebar
        BaseMapTransparency={BaseMapTransparency}
        setBaseMapTransparency={setBaseMapTransparency}
        groupedLayers={groupedLayers}
        activeLayers={activeLayers}
        opacities={opacities}
        loading={loading}
        error={error}
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        rasterCount={rasterCount}
        expandedCategories={expandedCategories}
        activeCount={activeCount}
        toggleLayer={toggleLayer}
        setLayerOpacity={setLayerOpacity}
        toggleCategory={toggleCategory}
        clearAllLayers={clearAllLayers}
      />
      <div style={{ flex: 1, position: 'relative', height: '100%' }}>
        <MapView
          BaseMapTransparency={BaseMapTransparency}
          activeLayersList={activeLayersList}
          opacities={opacities}
        />
        <ActiveLayersLegend
          activeLayersList={activeLayersList}
          opacities={opacities}
          setLayerOpacity={setLayerOpacity}
          toggleLayer={toggleLayer}
          allLayers={allLayers}
        />
      </div>
    </div>
  );
}

export default App;
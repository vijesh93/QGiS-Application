import { useState } from 'react';
import Sidebar from '../components/Sidebar';
import MapView from '../features/map/MapView';
import ActiveLayersLegend from '../components/ActiveLayersLegend';
import { useLayers } from '../features/map/hooks/useLayers';

// The main map view — split out from App.jsx so legal pages (which don't
// need layer data) don't also trigger useLayers()'s backend fetch.
function MapPage() {
  const [BaseMapTransparency, setBaseMapTransparency] = useState(100);
  const [masterTimePct, setMasterTimePct] = useState(0);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const {
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
    toggleLayer,
    setLayerOpacity,
    setLayerBand,
    applyMasterPercentage,
    toggleCategory,
    clearAllLayers,
  } = useLayers();

  // Moving the master slider updates its own displayed value and every
  // active multi-band layer's selected band at once.
  const handleMasterTimeChange = (pct) => {
    setMasterTimePct(pct);
    applyMasterPercentage(pct);
  };

  return (
    <div id="main-content" className="flex-1 min-h-0 flex">
      <Sidebar
        BaseMapTransparency={BaseMapTransparency}
        setBaseMapTransparency={setBaseMapTransparency}
        masterTimePct={masterTimePct}
        onMasterTimeChange={handleMasterTimeChange}
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
        collapsed={sidebarCollapsed}
        onToggleCollapsed={() => setSidebarCollapsed((c) => !c)}
      />
      <div style={{ flex: 1, position: 'relative', height: '100%' }}>
        <MapView
          BaseMapTransparency={BaseMapTransparency}
          activeLayersList={activeLayersList}
          opacities={opacities}
          selectedBands={selectedBands}
        />
        <ActiveLayersLegend
          activeLayersList={activeLayersList}
          opacities={opacities}
          setLayerOpacity={setLayerOpacity}
          selectedBands={selectedBands}
          setLayerBand={setLayerBand}
          toggleLayer={toggleLayer}
          allLayers={allLayers}
        />
      </div>
    </div>
  );
}

export default MapPage;

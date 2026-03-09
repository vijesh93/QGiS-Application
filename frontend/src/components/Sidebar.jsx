import React, { useState } from 'react';
import { Layers, Settings2, Search, X, ChevronDown, Eye, EyeOff } from 'lucide-react';

// One accent colour per category, cycling if there are more than 8 categories
const CATEGORY_COLORS = [
  '#4FC3F7', '#81C784', '#FFB74D', '#F48FB1',
  '#CE93D8', '#80DEEA', '#FFCC02', '#A5D6A7',
];

// ─────────────────────────────────────────────────────────────────────────────
// Main Sidebar component
// ─────────────────────────────────────────────────────────────────────────────
const Sidebar = ({
  // ── Base map controls (your existing props) ──
  BaseMapTransparency,
  setBaseMapTransparency,
  // ── Layer browser props (new, passed from App.jsx) ──
  groupedLayers,      // { [category]: { [subcategory]: layer[] } }
  activeLayers,       // { [layerId]: true/false }
  opacities,          // { [layerId]: 0-100 }
  loading,            // boolean — true while fetching from backend
  error,              // string | null — set if fetch failed (mock data used)
  searchQuery,        // string — current search text
  setSearchQuery,     // function — updates search text
  rasterCount,        // number | null — total COG files found
  expandedCategories, // { [category]: true/false }
  activeCount,        // number — how many layers are currently visible
  toggleLayer,        // function(layerId) — show/hide a layer
  setLayerOpacity,    // function(layerId, 0-100) — change a layer's opacity
  toggleCategory,     // function(category) — collapse/expand a category section
  clearAllLayers,     // function() — hide all layers at once
}) => {

  // Build a stable category → colour mapping so colours don't shift as
  // categories are filtered by search
  const allCategoryNames = Object.keys(groupedLayers);
  const catColor = {};
  allCategoryNames.forEach((cat, i) => {
    catColor[cat] = CATEGORY_COLORS[i % CATEGORY_COLORS.length];
  });

  return (
    <aside className="w-80 bg-slate-900 text-slate-100 h-screen flex flex-col shadow-xl z-10 flex-shrink-0">

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="p-5 border-b border-slate-700 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Layers className="text-blue-400" size={20} />
          <h1 className="text-lg font-bold tracking-tight">BW Geoportal</h1>
        </div>
        {/* Total raster count badge */}
        {rasterCount !== null && (
          <div className="flex flex-col items-end leading-none">
            <span className="text-blue-400 font-mono font-bold text-sm">
              {rasterCount.toLocaleString()}
            </span>
            <span className="text-slate-500 text-xs uppercase tracking-widest">layers</span>
          </div>
        )}
      </div>

      {/* ── Scrollable content ─────────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto flex flex-col">

        {/* ── Base Map Controls (your existing slider) ───────────────────── */}
        <div className="p-5 border-b border-slate-800">
          <div className="flex items-center gap-2 mb-3 text-slate-400">
            <Settings2 size={15} />
            <span className="text-xs font-semibold uppercase tracking-wider">Map Controls</span>
          </div>
          <div className="bg-slate-800 p-4 rounded-lg border border-slate-700">
            <label className="block text-sm font-medium mb-3">
              Base Map Transparency
            </label>
            <input
              type="range"
              className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
              min="0" max="100"
              value={BaseMapTransparency}
              onChange={(e) => setBaseMapTransparency(Number(e.target.value))}
            />
            <div className="flex justify-between text-xs text-slate-500 mt-2 font-mono">
              <span>0%</span>
              <span>{BaseMapTransparency}%</span>
              <span>100%</span>
            </div>
          </div>
        </div>

        {/* ── Layer Browser ──────────────────────────────────────────────── */}
        <div className="flex flex-col flex-1">

          {/* Search bar */}
          <div className="px-4 py-3 border-b border-slate-800">
            <div className="flex items-center gap-2 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 focus-within:border-blue-500 focus-within:ring-1 focus-within:ring-blue-500/20">
              <Search size={13} className="text-slate-500 flex-shrink-0" />
              <input
                type="text"
                placeholder="Search layers…"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="flex-1 bg-transparent border-none outline-none text-sm text-slate-200 placeholder-slate-500"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="text-slate-500 hover:text-slate-300 text-base leading-none"
                >
                  <X size={14} />
                </button>
              )}
            </div>
          </div>

          {/* Active layers summary bar */}
          {activeCount > 0 && (
            <div className="flex items-center gap-2 px-4 py-2 bg-blue-950/40 border-b border-slate-800">
              {/* Animated pulse dot */}
              <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse flex-shrink-0" />
              <span className="text-xs text-slate-400 flex-1">
                {activeCount} active layer{activeCount !== 1 ? 's' : ''}
              </span>
              <button
                onClick={clearAllLayers}
                className="text-xs text-slate-500 border border-slate-700 rounded px-2 py-0.5 hover:border-red-500 hover:text-red-400 transition-colors"
              >
                Clear all
              </button>
            </div>
          )}

          {/* Loading state */}
          {loading && (
            <div className="flex items-center gap-3 px-4 py-6 text-slate-500 text-sm">
              <div className="w-4 h-4 border-2 border-slate-700 border-t-blue-400 rounded-full animate-spin flex-shrink-0" />
              Loading layers…
            </div>
          )}

          {/* Error / offline notice */}
          {error && !loading && (
            <div className="flex items-center gap-2 px-4 py-2 text-amber-400 text-xs border-b border-slate-800 bg-amber-950/20">
              <span>⚠</span> Backend unavailable — showing demo data
            </div>
          )}

          {/* Empty search result */}
          {!loading && Object.keys(groupedLayers).length === 0 && (
            <p className="px-4 py-6 text-sm text-slate-500 text-center">
              No layers match your search.
            </p>
          )}

          {/* Category list */}
          {!loading && Object.entries(groupedLayers).map(([category, subgroups], catIndex) => {
            const isExpanded = expandedCategories[category] !== false;
            const color = catColor[category] || CATEGORY_COLORS[0];
            const totalInCat = Object.values(subgroups).flat().length;
            const activeInCat = Object.values(subgroups).flat()
              .filter((l) => activeLayers[l.id]).length;

            return (
              <CategorySection
                key={category}
                category={category}
                subgroups={subgroups}
                isExpanded={isExpanded}
                color={color}
                totalInCat={totalInCat}
                activeInCat={activeInCat}
                activeLayers={activeLayers}
                opacities={opacities}
                onToggleCategory={() => toggleCategory(category)}
                onToggleLayer={toggleLayer}
                onSetOpacity={setLayerOpacity}
              />
            );
          })}
        </div>
      </div>

      {/* ── Footer ─────────────────────────────────────────────────────────── */}
      <div className="px-4 py-3 border-t border-slate-800 flex gap-2 text-xs text-slate-600 font-mono">
        <span>Baden-Württemberg Geoportal</span>
        <span>·</span>
        <span>© {new Date().getFullYear()}</span>
      </div>
    </aside>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// CategorySection — one collapsible group (e.g. "Topography")
// ─────────────────────────────────────────────────────────────────────────────
function CategorySection({
  category, subgroups, isExpanded, color,
  totalInCat, activeInCat,
  activeLayers, opacities,
  onToggleCategory, onToggleLayer, onSetOpacity,
}) {
  return (
    <div className="border-b border-slate-800">
      {/* Category header button */}
      <button
        onClick={onToggleCategory}
        className="w-full flex items-center gap-2 px-4 py-2.5 text-left hover:bg-slate-800/60 transition-colors group"
      >
        {/* Coloured accent bar */}
        <span
          className="w-0.5 h-4 rounded-full flex-shrink-0"
          style={{ background: color }}
        />
        <span className="flex-1 text-xs font-semibold uppercase tracking-wider text-slate-400 group-hover:text-slate-200 transition-colors">
          {category}
        </span>
        {/* Active layer dot + count */}
        <span className="flex items-center gap-1 text-xs font-mono text-slate-500">
          {activeInCat > 0 && (
            <span
              className="w-1.5 h-1.5 rounded-full animate-pulse"
              style={{ background: color }}
            />
          )}
          {totalInCat}
        </span>
        {/* Chevron */}
        <ChevronDown
          size={14}
          className={`text-slate-600 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
        />
      </button>

      {/* Subcategory + layer rows */}
      {isExpanded && (
        <div className="pb-1">
          {Object.entries(subgroups).map(([subcategory, layers]) => (
            <div key={subcategory}>
              {/* Subcategory label (only shown if non-empty) */}
              {subcategory && (
                <div className="px-4 pl-7 pt-2 pb-1 text-xs font-semibold uppercase tracking-widest text-slate-600">
                  {subcategory}
                </div>
              )}
              {/* Individual layer rows */}
              {layers.map((layer) => (
                <LayerRow
                  key={layer.id}
                  layer={layer}
                  isActive={!!activeLayers[layer.id]}
                  opacity={opacities[layer.id] ?? 80}
                  accentColor={color}
                  onToggle={() => onToggleLayer(layer.id)}
                  onOpacityChange={(val) => onSetOpacity(layer.id, val)}
                />
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// LayerRow — a single layer with toggle checkbox and expandable opacity slider
// ─────────────────────────────────────────────────────────────────────────────
function LayerRow({ layer, isActive, opacity, accentColor, onToggle, onOpacityChange }) {
  // Controls whether the opacity slider panel is shown
  const [opacityOpen, setOpacityOpen] = useState(false);

  return (
    <div className={`transition-colors ${isActive ? 'bg-blue-950/20' : ''}`}>
      {/* Main row */}
      <div className="flex items-center gap-2 px-4 pl-7 py-1.5 hover:bg-slate-800/40 group">

        {/* Toggle checkbox */}
        <button
          onClick={onToggle}
          title={isActive ? 'Hide layer' : 'Show layer'}
          className={`w-4 h-4 rounded flex-shrink-0 border flex items-center justify-center transition-all ${
            isActive
              ? 'border-transparent'
              : 'border-slate-600 hover:border-slate-400 bg-transparent'
          }`}
          style={isActive ? { background: accentColor, boxShadow: `0 0 6px ${accentColor}66` } : {}}
        >
          {isActive && (
            <svg width="9" height="9" viewBox="0 0 10 10" fill="none">
              <path d="M2 5l2.5 2.5L8 3" stroke="white" strokeWidth="1.6"
                strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          )}
        </button>

        {/* Layer name + metadata tags */}
        <div className="flex-1 min-w-0">
          <span className="text-sm text-slate-300 block truncate">{layer.name}</span>
          <div className="flex gap-1 mt-0.5 flex-wrap">
            {layer.resolution && (
              <span className="text-slate-600 font-mono text-xs bg-slate-800 border border-slate-700 rounded px-1">
                {layer.resolution}
              </span>
            )}
            {layer.year && (
              <span className="text-slate-600 font-mono text-xs bg-slate-800 border border-slate-700 rounded px-1">
                {layer.year}
              </span>
            )}
          </div>
        </div>

        {/* Opacity button — only shown when the layer is active */}
        {isActive && (
          <button
            onClick={() => setOpacityOpen(!opacityOpen)}
            title="Adjust opacity"
            className={`flex items-center gap-1 text-xs font-mono px-1.5 py-0.5 rounded border transition-colors ${
              opacityOpen
                ? 'border-blue-500 text-blue-400'
                : 'border-slate-700 text-slate-500 hover:border-slate-500 hover:text-slate-300'
            }`}
          >
            {opacityOpen ? <EyeOff size={11} /> : <Eye size={11} />}
            {opacity}%
          </button>
        )}
      </div>

      {/* Opacity slider panel — slides open when the eye button is clicked */}
      {isActive && opacityOpen && (
        <div className="px-4 pl-11 pb-3 bg-slate-950/40 border-t border-slate-800/60">
          <div className="pt-2">
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-600 font-mono w-6">0%</span>
              <input
                type="range"
                min="0" max="100" step="5"
                value={opacity}
                onChange={(e) => onOpacityChange(Number(e.target.value))}
                className="flex-1 h-1.5 rounded appearance-none cursor-pointer"
                style={{ accentColor: accentColor }}
                aria-label={`${layer.name} opacity`}
              />
              <span className="text-xs text-slate-600 font-mono w-8 text-right">100%</span>
            </div>
            {layer.description && (
              <p className="text-xs text-slate-600 mt-2 leading-relaxed border-t border-slate-800 pt-2">
                {layer.description}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default Sidebar;
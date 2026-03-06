// components/ActiveLayersLegend.jsx
// Bottom-left overlay showing currently visible layers with quick opacity controls

import React from 'react';

const CATEGORY_COLORS = [
  '#4FC3F7', '#81C784', '#FFB74D', '#F48FB1',
  '#CE93D8', '#80DEEA', '#FFCC02', '#A5D6A7',
];

export default function ActiveLayersLegend({
  activeLayersList,
  opacities,
  setLayerOpacity,
  toggleLayer,
  allLayers,
}) {
  if (activeLayersList.length === 0) return null;

  // Build a stable category→color map
  const categories = [...new Set(allLayers.map((l) => l.category))];
  const catColor = {};
  categories.forEach((c, i) => {
    catColor[c] = CATEGORY_COLORS[i % CATEGORY_COLORS.length];
  });

  return (
    <div className="legend">
      <div className="legend__header">
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
          <circle cx="6" cy="6" r="5" stroke="currentColor" strokeWidth="1.2" />
          <path d="M6 3v3l2 1" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
        </svg>
        <span>Active Layers</span>
      </div>
      <div className="legend__list">
        {activeLayersList.map((layer) => {
          const color = catColor[layer.category] || '#4FC3F7';
          const opacity = opacities[layer.id] ?? 80;
          return (
            <div key={layer.id} className="legend__item">
              <span
                className="legend__swatch"
                style={{ background: color, opacity: opacity / 100 + 0.2 }}
              />
              <span className="legend__name">{layer.name}</span>
              <div className="legend__inline-controls">
                <input
                  type="range"
                  min="0"
                  max="100"
                  step="5"
                  value={opacity}
                  onChange={(e) => setLayerOpacity(layer.id, Number(e.target.value))}
                  className="legend__slider"
                  style={{ '--accent': color }}
                  aria-label={`${layer.name} opacity`}
                  title={`Opacity: ${opacity}%`}
                />
                <span className="legend__opacity-val">{opacity}%</span>
                <button
                  className="legend__remove"
                  onClick={() => toggleLayer(layer.id)}
                  title={`Hide ${layer.name}`}
                  aria-label={`Remove ${layer.name}`}
                >
                  ×
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

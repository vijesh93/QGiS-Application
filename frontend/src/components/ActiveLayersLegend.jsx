// components/ActiveLayersLegend.jsx
// Floating bottom-left overlay — styled to match the dark geoportal theme.
// Uses inline styles only so no CSS file changes are needed.

import React, { useState } from 'react';

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
  const [collapsed, setCollapsed] = useState(false);

  if (!activeLayersList || activeLayersList.length === 0) return null;

  // Stable category → colour mapping
  const categories = [...new Set(allLayers.map((l) => l.category))];
  const catColor = {};
  categories.forEach((c, i) => { catColor[c] = CATEGORY_COLORS[i % CATEGORY_COLORS.length]; });

  return (
    <div style={{
      position:     'absolute',
      bottom:       '40px',
      left:         '16px',
      zIndex:       200,
      minWidth:     '260px',
      maxWidth:     '320px',
      background:   'rgba(17, 23, 32, 0.96)',
      border:       '1px solid #1f2d3d',
      borderRadius: '10px',
      boxShadow:    '0 8px 32px rgba(0,0,0,0.6)',
      backdropFilter: 'blur(12px)',
      fontFamily:   "'DM Sans', system-ui, sans-serif",
      overflow:     'hidden',
    }}>

      {/* ── Header ── */}
      <div
        onClick={() => setCollapsed(c => !c)}
        style={{
          display:      'flex',
          alignItems:   'center',
          gap:          '8px',
          padding:      '9px 12px',
          borderBottom: collapsed ? 'none' : '1px solid #1f2d3d',
          background:   'rgba(22, 29, 40, 0.9)',
          cursor:       'pointer',
          userSelect:   'none',
        }}
      >
        {/* Pulsing dot */}
        <span style={{
          width: '7px', height: '7px', borderRadius: '50%',
          background: '#4FC3F7', flexShrink: 0,
          boxShadow: '0 0 6px #4FC3F7',
          animation: 'pulse 2s infinite',
        }} />
        <span style={{
          flex: 1, fontSize: '11px', fontWeight: 700,
          letterSpacing: '0.07em', textTransform: 'uppercase',
          color: '#8fa3b8',
        }}>
          Active Layers
        </span>
        <span style={{
          fontSize: '11px', fontWeight: 700,
          color: '#4FC3F7', fontFamily: 'monospace',
          background: 'rgba(79,195,247,0.1)',
          padding: '1px 7px', borderRadius: '10px',
        }}>
          {activeLayersList.length}
        </span>
        {/* Collapse chevron */}
        <span style={{
          color: '#4a6077', fontSize: '12px',
          transform: collapsed ? 'rotate(180deg)' : 'rotate(0deg)',
          transition: 'transform 0.2s',
        }}>▲</span>
      </div>

      {/* ── Layer list ── */}
      {!collapsed && (
        <div style={{ maxHeight: '260px', overflowY: 'auto', padding: '4px 0' }}>
          {activeLayersList.map((layer) => {
            const color   = catColor[layer.category] || '#4FC3F7';
            const opacity = opacities[layer.id] ?? 80;
            return (
              <div
                key={layer.id}
                style={{
                  padding:    '7px 12px',
                  borderBottom: '1px solid rgba(31,45,61,0.5)',
                }}
              >
                {/* Layer name row */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '5px' }}>
                  <span style={{
                    width: '10px', height: '10px', borderRadius: '2px',
                    background: color, flexShrink: 0,
                  }} />
                  <span style={{
                    flex: 1, fontSize: '12px', color: '#e2e8f0',
                    whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                  }}>
                    {layer.name}
                  </span>
                  {/* Remove button */}
                  <button
                    onClick={() => toggleLayer(layer.id)}
                    title={`Hide ${layer.name}`}
                    style={{
                      background: 'none', border: 'none',
                      color: '#4a6077', fontSize: '18px', lineHeight: 1,
                      cursor: 'pointer', padding: '0 2px', flexShrink: 0,
                      transition: 'color 0.15s',
                    }}
                    onMouseEnter={e => e.currentTarget.style.color = '#ef4444'}
                    onMouseLeave={e => e.currentTarget.style.color = '#4a6077'}
                  >
                    ×
                  </button>
                </div>

                {/* Opacity row */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '10px', color: '#4a6077', width: '16px' }}>
                    {opacity === 0 ? '○' : '●'}
                  </span>
                  <input
                    type="range"
                    min="0" max="100" step="5"
                    value={opacity}
                    onChange={e => setLayerOpacity(layer.id, Number(e.target.value))}
                    aria-label={`${layer.name} opacity`}
                    style={{
                      flex: 1, height: '3px', cursor: 'pointer',
                      accentColor: color,
                    }}
                  />
                  <span style={{
                    fontSize: '10px', color: '#8fa3b8',
                    fontFamily: 'monospace', width: '32px', textAlign: 'right',
                  }}>
                    {opacity}%
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Keyframe for pulsing dot — injected once via a style tag */}
      <style>{`@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.35} }`}</style>
    </div>
  );
}
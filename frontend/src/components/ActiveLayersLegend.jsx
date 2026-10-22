// components/ActiveLayersLegend.jsx
// Floating bottom-left overlay — chrome restyled to the BW palette (see
// frontend/src/styles/index.css for the token source of truth; these are
// plain inline styles, not Tailwind classes, so the hex values are repeated
// here — keep the two in sync if the palette ever changes).
// CATEGORY_COLORS below is intentionally left untouched: it's the per-layer
// data-visualization accent, a separate concern from branded chrome — see
// docs/bw-rebrand-plan.md, item 6.

import React, { useState, useEffect } from 'react';

const CATEGORY_COLORS = [
  '#4FC3F7', '#81C784', '#FFB74D', '#F48FB1',
  '#CE93D8', '#80DEEA', '#FFCC02', '#A5D6A7',
];

// bands 1..bandCount are all real timesteps/values — band_start_date (when
// set) corresponds to band 1. band_labels (when set) takes priority over
// date math for layers whose bands are a qualitative, non-date sequence
// (e.g. "near"/"medium"/"far" prediction horizons).
function formatBandLabel(layer, band) {
  if (layer.bandLabels && layer.bandLabels[band - 1]) {
    return layer.bandLabels[band - 1];
  }
  if (layer.bandStartDate && layer.bandDateStepDays) {
    const d = new Date(layer.bandStartDate);
    d.setDate(d.getDate() + (band - 1) * layer.bandDateStepDays);
    return d.toISOString().slice(0, 10);
  }
  return `Day ${band} of ${layer.bandCount}`;
}

// Dragging this fires onChange on every pixel of movement — committing each
// one straight to the map would mean a fresh TiTiler tile request per pixel.
// Instead: the slider's visual position (and label) follows the drag
// instantly via local state, but the actual band change (and the tile
// request cascade it triggers in MapView) only commits on release — mouse,
// touch, or keyboard (arrow keys don't "release", so keyup commits there).
function TimeSliderRow({ layer, selectedBand, setLayerBand, color }) {
  const [dragValue, setDragValue] = useState(selectedBand);

  // Stay in sync when the band changes from elsewhere (e.g. the master
  // time control), as long as the user isn't actively dragging this slider.
  useEffect(() => {
    setDragValue(selectedBand);
  }, [selectedBand]);

  const commit = (e) => setLayerBand(layer.id, Number(e.target.value));

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '5px' }}>
      <span style={{ fontSize: '10px', color: '#918C8C', width: '16px' }}>⏱</span>
      <input
        type="range"
        min="1" max={layer.bandCount} step="1"
        value={dragValue}
        onChange={e => setDragValue(Number(e.target.value))}
        onMouseUp={commit}
        onTouchEnd={commit}
        onKeyUp={commit}
        aria-label={`${layer.name} timestep`}
        style={{
          flex: 1, height: '3px', cursor: 'pointer',
          accentColor: color,
        }}
      />
      <span style={{
        fontSize: '10px', color: '#BBB6B5',
        fontFamily: 'monospace', minWidth: '32px', textAlign: 'right',
        whiteSpace: 'nowrap',
      }}>
        {formatBandLabel(layer, dragValue)}
      </span>
    </div>
  );
}

export default function ActiveLayersLegend({
  activeLayersList,
  opacities,
  setLayerOpacity,
  selectedBands,
  setLayerBand,
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
      background:   'rgba(42, 38, 35, 0.96)',
      border:       '1px solid #47403C',
      borderRadius: '10px',
      boxShadow:    '0 8px 32px rgba(0,0,0,0.6)',
      backdropFilter: 'blur(12px)',
      fontFamily:   "'BaWueSansWeb', system-ui, sans-serif",
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
          borderBottom: collapsed ? 'none' : '1px solid #47403C',
          background:   'rgba(71, 64, 60, 0.9)',
          cursor:       'pointer',
          userSelect:   'none',
        }}
      >
        {/* Pulsing dot */}
        <span style={{
          width: '7px', height: '7px', borderRadius: '50%',
          background: '#FFFC00', flexShrink: 0,
          boxShadow: '0 0 6px #FFFC00',
          animation: 'pulse 2s infinite',
        }} />
        <span style={{
          flex: 1, fontSize: '11px', fontWeight: 700,
          letterSpacing: '0.07em', textTransform: 'uppercase',
          color: '#BBB6B5',
        }}>
          Active Layers
        </span>
        <span style={{
          fontSize: '11px', fontWeight: 700,
          color: '#FFFC00', fontFamily: 'monospace',
          background: 'rgba(255,252,0,0.15)',
          padding: '1px 7px', borderRadius: '10px',
        }}>
          {activeLayersList.length}
        </span>
        {/* Collapse chevron */}
        <span style={{
          color: '#918C8C', fontSize: '12px',
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
                  borderBottom: '1px solid rgba(71,64,60,0.5)',
                }}
              >
                {/* Layer name row */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '5px' }}>
                  <span style={{
                    width: '10px', height: '10px', borderRadius: '2px',
                    background: color, flexShrink: 0,
                  }} />
                  <span style={{
                    flex: 1, fontSize: '12px', color: '#E4E0E0',
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
                      color: '#918C8C', fontSize: '18px', lineHeight: 1,
                      cursor: 'pointer', padding: '0 2px', flexShrink: 0,
                      transition: 'color 0.15s',
                    }}
                    onMouseEnter={e => e.currentTarget.style.color = '#FD4D4D'}
                    onMouseLeave={e => e.currentTarget.style.color = '#918C8C'}
                  >
                    ×
                  </button>
                </div>

                {/* Opacity row */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '10px', color: '#918C8C', width: '16px' }}>
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
                    fontSize: '10px', color: '#BBB6B5',
                    fontFamily: 'monospace', width: '32px', textAlign: 'right',
                  }}>
                    {opacity}%
                  </span>
                </div>

                {/* Time row — only for multi-band (time-series) layers */}
                {layer.bandCount > 1 && (
                  <TimeSliderRow
                    layer={layer}
                    selectedBand={selectedBands[layer.id] ?? 1}
                    setLayerBand={setLayerBand}
                    color={color}
                  />
                )}
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

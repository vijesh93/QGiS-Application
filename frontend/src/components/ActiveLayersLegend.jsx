// components/ActiveLayersLegend.jsx
// Floating bottom-left overlay — chrome restyled to the BW palette (see
// frontend/src/styles/index.css for the token source of truth; these are
// plain inline styles, not Tailwind classes, so the hex values are repeated
// here — keep the two in sync if the palette ever changes).
// CATEGORY_COLORS below is intentionally left untouched: it's the per-layer
// data-visualization accent, a separate concern from branded chrome — see
// docs/bw-rebrand-plan.md, item 6.

import React, { useState, useEffect } from 'react';
import { formatBandLabel } from '../utils/bandLabel';

const CATEGORY_COLORS = [
  '#4FC3F7', '#81C784', '#FFB74D', '#F48FB1',
  '#CE93D8', '#80DEEA', '#FFCC02', '#A5D6A7',
];

// Matplotlib's standard viridis anchor colors. Every layer's tiles are
// rendered with the fixed colormap_name=viridis (see layersApi.js's
// buildTileUrl — its `colormap` param is never actually overridden
// anywhere in this codebase today), so this gradient is accurate for
// every layer shown here. If a per-layer colormap is ever introduced,
// this needs to switch to picking the matching gradient per layer instead
// of assuming viridis everywhere.
const VIRIDIS_STOPS = [
  '#440154', '#482878', '#3E4A89', '#31688E', '#26828E',
  '#1F9E89', '#35B779', '#6ECE58', '#B5DE2B', '#FDE725',
];
const VIRIDIS_GRADIENT = `linear-gradient(to right, ${VIRIDIS_STOPS.join(', ')})`;

// Compact formatting: a layer's values can range from small degC deltas
// (e.g. 0.27) to large precipitation totals in mm (e.g. 2773) — scale the
// decimal places shown to the magnitude so neither looks silly.
function formatScaleValue(v) {
  if (v == null || Number.isNaN(v)) return '—';
  const abs = Math.abs(v);
  const decimals = abs >= 100 ? 0 : abs >= 1 ? 1 : 2;
  return v.toFixed(decimals);
}

// The color scale maps TiTiler's rescale=min,max window onto the viridis
// gradient (min → leftmost color, max → rightmost), so this bar's two end
// labels line up directly with what's painted on the map. Renders nothing
// for a layer whose min/max failed to compute (rare — e.g. an all-nodata
// raster) rather than show a misleading placeholder range.
function ColorScaleRow({ minValue, maxValue }) {
  if (minValue == null || maxValue == null) return null;
  return (
    <div style={{ marginTop: '5px' }}>
      <div style={{
        height: '6px', borderRadius: '3px',
        background: VIRIDIS_GRADIENT,
        border: '1px solid rgba(0,0,0,0.3)',
      }} />
      <div style={{
        display: 'flex', justifyContent: 'space-between',
        fontSize: '9px', color: '#918C8C', fontFamily: 'monospace', marginTop: '2px',
      }}>
        <span>{formatScaleValue(minValue)}</span>
        <span>{formatScaleValue(maxValue)}</span>
      </div>
    </div>
  );
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
  topmostLayerId,
  defaultTopmostLayerId,
  onBringToTop,
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
            const color    = catColor[layer.category] || '#4FC3F7';
            const opacity  = opacities[layer.id] ?? 80;
            // Pinned (explicit, sticky choice) takes visual priority over
            // the default (automatic, changes as layers are toggled) —
            // see the button's style below for how these render
            // differently so the two aren't mistaken for each other.
            const isPinned         = topmostLayerId != null && layer.id === topmostLayerId;
            const isDefaultTopmost = topmostLayerId == null && layer.id === defaultTopmostLayerId;
            const isTopmost        = isPinned || isDefaultTopmost;
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
                  {/* Category/subcategory (e.g. "SSP2-4.5 · bio01") shown as
                      a small label above the name — without it, several
                      variables sharing the same time-horizon/kind (the
                      variable name was deliberately dropped from
                      display_name itself, since the Sidebar already shows
                      it as a heading) render as identical-looking rows
                      here, with no sidebar grouping context to tell them
                      apart. Same fix as PixelValuePopup.jsx's header,
                      applied here for the same reason. */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    {(layer.category || layer.subcategory) && (
                      <div style={{
                        fontSize: '9px', fontWeight: 700,
                        letterSpacing: '0.06em', textTransform: 'uppercase',
                        color: '#918C8C', marginBottom: '1px',
                        whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                      }}>
                        {[layer.category, layer.subcategory].filter(Boolean).join(' · ')}
                      </div>
                    )}
                    <div style={{
                      fontSize: '12px', color: '#E4E0E0',
                      whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                    }}>
                      {layer.name}
                    </div>
                  </div>
                  {/* "TOP" badge button — pins this layer above every other
                      active layer, both on the map and as the pixel-value
                      click popup's target (see useLayers.jsx's
                      topmostLayerId/bringLayerToTop), WITHOUT moving it
                      within this list — list position and map stacking are
                      deliberately independent, so pinning a layer never
                      makes it jump around in this panel. Exclusive: pinning
                      one layer automatically un-pins whichever was pinned
                      before it, so at most one is ever lit up at a time —
                      clicking the already-pinned layer's own badge again
                      releases it back to the default stacking. Labelled
                      with text rather than an icon since a single glyph
                      (e.g. an arrow) wasn't a clear enough affordance for
                      "this picks which overlapping layer the click-popup
                      reads from".

                      Three visual states: solid fill = explicitly pinned
                      (sticky until released or another layer is pinned);
                      outline only = this one is on top automatically right
                      now (the most recently activated layer) but nothing's
                      pinned — clicking it turns that into an explicit pin;
                      dim = neither, clicking it pins it. */}
                  <button
                    onClick={() => onBringToTop(layer.id)}
                    title={
                      isPinned
                        ? `${layer.name} is on top — click to release`
                        : isDefaultTopmost
                          ? `${layer.name} is on top by default — click to pin it there`
                          : `Bring ${layer.name} to top (so map clicks read its values)`
                    }
                    style={{
                      background: isPinned ? 'rgba(255,252,0,0.18)' : 'rgba(145,140,140,0.12)',
                      border: isPinned
                        ? '1px solid rgba(255,252,0,0.4)'
                        : isDefaultTopmost
                          ? '1px solid rgba(255,252,0,0.35)'
                          : '1px solid transparent',
                      borderRadius: '10px',
                      color: isTopmost ? '#FFFC00' : '#918C8C',
                      fontSize: '9px', fontWeight: 700, letterSpacing: '0.04em',
                      lineHeight: 1, cursor: 'pointer', padding: '3px 6px', flexShrink: 0,
                      transition: 'color 0.15s, background 0.15s',
                    }}
                    onMouseEnter={e => {
                      if (isTopmost) return;
                      e.currentTarget.style.color = '#BBB6B5';
                      e.currentTarget.style.background = 'rgba(145,140,140,0.22)';
                    }}
                    onMouseLeave={e => {
                      if (isTopmost) return;
                      e.currentTarget.style.color = '#918C8C';
                      e.currentTarget.style.background = 'rgba(145,140,140,0.12)';
                    }}
                  >
                    TOP
                  </button>
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

                <ColorScaleRow minValue={layer.minValue} maxValue={layer.maxValue} />

                {/* Time row — only for multi-band sequence (time-series) layers.
                    Distribution-mode layers (band_mode === 'distribution', e.g.
                    median/p17/p83/... statistics) never get a slider — the map
                    always shows band 1; the rest surface via the map-click
                    pixel-value popup instead, not by scrubbing. */}
                {layer.bandCount > 1 && layer.bandMode !== 'distribution' && (
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

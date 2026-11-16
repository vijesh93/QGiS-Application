// components/PixelValuePopup.jsx
// Small closable "note" popup shown on map click, reporting the clicked
// pixel's value(s) for the topmost active layer at that point. Chrome
// intentionally mirrors ActiveLayersLegend.jsx's palette/spacing (same
// hex values, same font) so the two floating overlays read as one system.

import React from 'react';
import { formatBandLabel } from '../utils/bandLabel';

function formatValue(v) {
  if (v === null || v === undefined || Number.isNaN(v)) return 'No data';
  return Math.round(v * 100) / 100;
}

// Distribution-mode layers (band_mode === 'distribution', e.g. the new
// SSP2-4.5/SSP3-7.0 climate-projection rasters) show one row per band,
// labelled from the layer's own DB-sourced band_labels
// (median/p17/p83/p05/p95[/agree]) zipped against the point query's
// `values` — never from TiTiler's per-point band_descriptions, which is
// confirmed buggy (repeats the last band's description for every entry).
// Every other layer (sequence-mode, or single-band) shows exactly one row:
// whichever band is currently displayed on the map for that layer, using
// the same label precedence the time slider already uses.
function buildRows(layer, values, selectedBand) {
  if (!values) return [];
  if (layer.bandMode === 'distribution' && layer.bandLabels && layer.bandLabels.length) {
    const n = Math.min(layer.bandLabels.length, values.length);
    return Array.from({ length: n }, (_, i) => ({
      label: layer.bandLabels[i],
      value: values[i],
    }));
  }
  const band = selectedBand ?? 1;
  return [{
    label: formatBandLabel(layer, band),
    value: values[band - 1],
  }];
}

export default function PixelValuePopup({ x, y, layer, selectedBand, values, loading, error, onClose }) {
  if (!layer) return null;
  const rows = buildRows(layer, values, selectedBand);

  return (
    <div style={{
      position:       'absolute',
      left:           `${x}px`,
      top:            `${y}px`,
      zIndex:         300,
      minWidth:       '220px',
      maxWidth:       '280px',
      background:     'rgba(42, 38, 35, 0.96)',
      border:         '1px solid #47403C',
      borderRadius:   '10px',
      boxShadow:      '0 8px 32px rgba(0,0,0,0.6)',
      backdropFilter: 'blur(12px)',
      fontFamily:     "'BaWueSansWeb', system-ui, sans-serif",
      overflow:       'hidden',
    }}>
      {/* ── Header ── */}
      <div style={{
        display:      'flex',
        alignItems:   'center',
        gap:          '8px',
        padding:      '9px 12px',
        borderBottom: '1px solid #47403C',
        background:   'rgba(71, 64, 60, 0.9)',
      }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          {/* Subcategory (e.g. the Variable, "bio01") is shown here rather
              than baked into display_name — the sidebar already shows it
              as a heading above these layers, so the name itself stays
              short, but the popup has no sidebar context visible, so two
              variables sharing the same time-horizon/kind would otherwise
              render identical, ambiguous headers. */}
          {layer.subcategory && (
            <div style={{
              fontSize: '9px', fontWeight: 700,
              letterSpacing: '0.08em', textTransform: 'uppercase',
              color: '#918C8C', marginBottom: '1px',
              whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
            }}>
              {layer.subcategory}
            </div>
          )}
          <div style={{
            fontSize: '11px', fontWeight: 700,
            letterSpacing: '0.07em', textTransform: 'uppercase',
            color: '#BBB6B5', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
          }}>
            {layer.name}
          </div>
        </div>
        <button
          onClick={onClose}
          title="Close"
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

      {/* ── Body ── */}
      <div style={{ padding: '8px 12px' }}>
        {loading && (
          <div style={{ fontSize: '12px', color: '#918C8C' }}>Loading…</div>
        )}
        {!loading && (error || rows.length === 0) && (
          <div style={{ fontSize: '12px', color: '#918C8C' }}>No data at this point.</div>
        )}
        {!loading && !error && rows.map((row, i) => (
          <div
            key={i}
            style={{
              display: 'flex', justifyContent: 'space-between', gap: '12px',
              padding: '3px 0',
              borderBottom: i < rows.length - 1 ? '1px solid rgba(71,64,60,0.5)' : 'none',
            }}
          >
            <span style={{ fontSize: '12px', color: '#BBB6B5' }}>{row.label}</span>
            <span style={{ fontSize: '12px', color: '#FFFC00', fontFamily: 'monospace' }}>
              {formatValue(row.value)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

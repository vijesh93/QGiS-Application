// frontend/src/utils/bandLabel.js
// Shared band-label formatting — bands 1..bandCount are all real
// timesteps/values. band_labels (when set) takes priority over date math
// for layers whose bands are a qualitative, non-date sequence (e.g.
// "near"/"medium"/"far" prediction horizons, or a distribution's
// median/p17/p83/p05/p95 statistic names). Used by both the time-slider
// row (ActiveLayersLegend) and the pixel-value popup (PixelValuePopup) so
// the two can never describe the same band differently.
export function formatBandLabel(layer, band) {
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

import type { HealthMarker } from '../api/healthReport';

// How far OUTSIDE its own printed reference range a value falls, as a
// fraction of the boundary it crossed (e.g. 0.20 = 20% past the
// min/max). This is a purely visual magnitude heuristic — NOT a
// medical severity score — computed client-side from numbers already
// in the marker (value + reference_range_min/max), never stored or
// sent anywhere. Both far-below and far-above are treated as equally
// worth flagging (marker.range_status already tells us which
// direction; this only decides how strongly to color/label it).
//
// Shared by app/(main)/health-insights/index.tsx (severityCardStyle,
// reviewMarkerSortRank) and app/(main)/body-details/index.tsx
// (flaggedMarkerDisplay) — previously duplicated identically in both
// files; extracted here so the two never drift out of sync.
export type MarkerSeverity = 'high' | 'medium' | 'none';

export const SEVERITY_THRESHOLD = 0.15; // >15% past the boundary = "high"

/**
 * Classifies how far a health-report marker's value falls outside its
 * own printed reference range: 'none' if within range (or no
 * range_status at all), 'high' if more than SEVERITY_THRESHOLD (15%)
 * past the boundary it crossed, otherwise 'medium'.
 */
export function getMarkerSeverity(marker: HealthMarker): MarkerSeverity {
  if (!marker.range_status || marker.range_status === 'within') return 'none';

  if (marker.range_status === 'below' && marker.reference_range_min != null && marker.reference_range_min !== 0) {
    const deviation = (marker.reference_range_min - marker.value) / marker.reference_range_min;
    return deviation > SEVERITY_THRESHOLD ? 'high' : 'medium';
  }

  if (marker.range_status === 'above' && marker.reference_range_max != null && marker.reference_range_max !== 0) {
    const deviation = (marker.value - marker.reference_range_max) / marker.reference_range_max;
    return deviation > SEVERITY_THRESHOLD ? 'high' : 'medium';
  }

  // range_status is set (below/above) but there's no min/max to
  // measure deviation from (shouldn't normally happen) — default to
  // the more visible "medium" rather than silently showing nothing.
  return 'medium';
}

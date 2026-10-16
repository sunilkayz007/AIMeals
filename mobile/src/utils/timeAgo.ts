// Shared "time ago" formatter — used by the Recent Scans sections on
// both the Food Scan and Ingredient Scan screens (app/(main)/scan and
// app/(main)/ingredient-scan) to show when each past scan happened,
// without pulling in a full date library for one small formatter.
//
// Deliberately coarse (minutes/hours/days, capped at a plain date
// past a week) — this is a lightweight context cue next to a recent-
// scans list, not a precise timestamp display.
export function timeAgo(isoString: string): string {
  const then = new Date(isoString).getTime();
  const now = Date.now();
  const diffMs = Math.max(0, now - then);
  const diffMin = Math.floor(diffMs / 60000);

  if (diffMin < 1) return 'Just now';
  if (diffMin < 60) return `${diffMin}m ago`;

  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;

  const diffDay = Math.floor(diffHr / 24);
  if (diffDay < 7) return `${diffDay}d ago`;

  return new Date(isoString).toLocaleDateString();
}

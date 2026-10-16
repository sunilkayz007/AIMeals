import { useEffect, useState } from 'react';
import type { Subscription } from '../types/subscription';

const WARNING_THRESHOLD_PERCENT = 75;

/**
 * Decides whether the 75%-usage "Upgrade or watch an ad" modal should
 * be shown for the given subscription.
 *
 * NOTE — scope of "dismissed" here: dismissal is per-mount only (a
 * simple useState), not persisted across screens or app restarts. If
 * this hook gets used on multiple screens, the modal could show again
 * on each one independently until credits reset or the tier changes.
 * That's an intentional, small first pass — a shared/global dismissal
 * (e.g. via context, or persisted per billing period so it only nags
 * once total) is a reasonable follow-up once this is proven useful,
 * but isn't built yet.
 *
 * Returns:
 *   isVisible - true if usage is at/above 75% AND the user hasn't
 *     dismissed it yet during this mount.
 *   dismiss() - call when the user closes the modal (via either
 *     action button or an explicit close) to hide it for the rest of
 *     this mount, even if usage stays above threshold.
 */
export function useCreditThresholdModal(subscription: Subscription | null) {
  const [isDismissed, setIsDismissed] = useState(false);

  const usedPercent =
    subscription && subscription.monthly_credit_allowance > 0
      ? (subscription.credits_used_this_period / subscription.monthly_credit_allowance) * 100
      : 0;

  const hasCrossedThreshold = usedPercent >= WARNING_THRESHOLD_PERCENT;

  // If a fresh billing period starts (credits_used_this_period drops
  // back down, e.g. after a reset or upgrade), let the modal be
  // eligible to show again rather than staying dismissed forever for
  // this mount.
  useEffect(() => {
    if (!hasCrossedThreshold) {
      setIsDismissed(false);
    }
  }, [hasCrossedThreshold]);

  return {
    isVisible: hasCrossedThreshold && !isDismissed,
    dismiss: () => setIsDismissed(true),
  };
}
import { useEffect, useRef, useState } from 'react';
import { Modal, View, Text, Pressable } from 'react-native';
import { useRouter } from 'expo-router';
import { useTheme } from '../theme/ThemeContext';
import { useAppRewardedAd } from '../hooks/useAppRewardedAd';

interface CreditThresholdModalProps {
  visible: boolean;
  onDismiss: () => void;
  creditsRemaining: number;
  /**
   * Called a few seconds after a rewarded ad is completed, and again when
   * the user taps Done, so the host screen can re-fetch the balance. The
   * server-side grant lands after the ad closes; without a re-fetch the
   * screen kept showing the old balance and the reward looked lost.
   */
  onRewardClaimed?: () => void;
}

// AdMob's server-side verification usually reaches the backend within a
// few seconds of the ad finishing.
const REWARD_REFRESH_DELAY_MS = 4000;

/**
 * Shown once usage crosses 75% of the monthly allowance (see
 * useCreditThresholdModal). Offers two paths: upgrade the plan, or
 * watch a rewarded ad for bonus credits.
 *
 * "Watch Ad" now triggers a REAL AdMob rewarded ad via
 * useAppRewardedAd(). Once the SDK confirms isEarnedReward
 * client-side, this shows a "reward on its way" message rather than
 * claiming credits were added immediately — the actual grant happens
 * server-side via AdMob's SSV callback (app/api/v1/ads.py), which
 * requires Google's servers to independently verify the view and can
 * lag a few seconds behind. Overstating an instant credit here would
 * be misleading if the SSV call is delayed or (in local dev, before
 * the backend is publicly reachable) never arrives at all.
 */
export default function CreditThresholdModal({
  visible,
  onDismiss,
  creditsRemaining,
  onRewardClaimed,
}: CreditThresholdModalProps) {
  const router = useRouter();
  const { colors } = useTheme();
  const { isLoaded, isEarnedReward, watchAd } = useAppRewardedAd();
  const [rewardJustEarned, setRewardJustEarned] = useState(false);

  useEffect(() => {
    if (isEarnedReward) {
      setRewardJustEarned(true);
    }
  }, [isEarnedReward]);

  // Held in a ref so a parent passing an inline arrow function doesn't
  // restart the timer on every re-render (the refresh itself re-renders
  // the parent, which would otherwise re-arm it forever).
  const onRewardClaimedRef = useRef(onRewardClaimed);
  onRewardClaimedRef.current = onRewardClaimed;

  useEffect(() => {
    if (!rewardJustEarned) return;
    const timer = setTimeout(() => onRewardClaimedRef.current?.(), REWARD_REFRESH_DELAY_MS);
    return () => clearTimeout(timer);
  }, [rewardJustEarned]);

  // Reset the "just earned" state each time the modal is freshly
  // reopened, so a stale success message from a previous watch
  // doesn't linger into the next time this modal appears.
  useEffect(() => {
    if (visible) {
      setRewardJustEarned(false);
    }
  }, [visible]);

  const handleUpgrade = () => {
    onDismiss();
    router.push('/(main)/upgrade' as any);
  };

  const handleWatchAd = () => {
    watchAd();
  };

  const handleDone = () => {
    setRewardJustEarned(false);
    onRewardClaimed?.();
    onDismiss();
  };

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onDismiss}>
      <View
        style={{
          flex: 1,
          backgroundColor: 'rgba(0,0,0,0.5)',
          justifyContent: 'center',
          alignItems: 'center',
          padding: 24,
        }}
      >
        <View
          style={{
            backgroundColor: colors.screenBg,
            borderRadius: 16,
            padding: 22,
            width: '100%',
            maxWidth: 340,
          }}
        >
          {rewardJustEarned ? (
            <>
              <Text style={{ fontSize: 32, textAlign: 'center', marginBottom: 10 }}>🎉</Text>
              <Text
                style={{
                  fontSize: 17,
                  fontWeight: '700',
                  color: colors.textPrimary,
                  textAlign: 'center',
                  marginBottom: 6,
                }}
              >
                Reward on its way
              </Text>
              <Text
                style={{
                  fontSize: 12,
                  color: colors.textSecondary,
                  textAlign: 'center',
                  marginBottom: 20,
                }}
              >
                Thanks for watching! Your bonus credits will be added shortly once verified.
              </Text>
              <Pressable
                onPress={handleDone}
                style={{
                  backgroundColor: colors.accentSage,
                  borderRadius: 100,
                  paddingVertical: 12,
                  alignItems: 'center',
                }}
              >
                <Text style={{ fontSize: 13, fontWeight: '700', color: '#fff' }}>Done</Text>
              </Pressable>
            </>
          ) : (
            <>
              <Text style={{ fontSize: 32, textAlign: 'center', marginBottom: 10 }}>⚡</Text>

              <Text
                style={{
                  fontSize: 17,
                  fontWeight: '700',
                  color: colors.textPrimary,
                  textAlign: 'center',
                  marginBottom: 6,
                }}
              >
                Running low on credits
              </Text>

              <Text
                style={{
                  fontSize: 12,
                  color: colors.textSecondary,
                  textAlign: 'center',
                  marginBottom: 20,
                }}
              >
                {creditsRemaining <= 0
                  ? "You're out of credits for this period."
                  : `You have ${creditsRemaining} ${creditsRemaining === 1 ? 'credit' : 'credits'} left this period.`}{' '}
                Upgrade for more, or watch a short ad to earn bonus credits.
              </Text>

              <Pressable
                onPress={handleUpgrade}
                style={{
                  backgroundColor: colors.accentSage,
                  borderRadius: 100,
                  paddingVertical: 12,
                  alignItems: 'center',
                  marginBottom: 10,
                }}
              >
                <Text style={{ fontSize: 13, fontWeight: '700', color: '#fff' }}>Upgrade Plan</Text>
              </Pressable>

              <Pressable
                onPress={handleWatchAd}
                disabled={!isLoaded}
                style={{
                  backgroundColor: colors.surfaceAlt,
                  borderRadius: 100,
                  paddingVertical: 12,
                  alignItems: 'center',
                  marginBottom: 14,
                  borderWidth: 1,
                  borderColor: colors.border,
                  opacity: isLoaded ? 1 : 0.6,
                }}
              >
                <Text style={{ fontSize: 13, fontWeight: '700', color: colors.textPrimary }}>
                  {isLoaded ? '🎬 Watch Ad for Credits' : 'Loading ad…'}
                </Text>
              </Pressable>

              <Pressable onPress={onDismiss} style={{ alignItems: 'center' }}>
                <Text style={{ fontSize: 12, color: colors.textSecondary }}>Maybe later</Text>
              </Pressable>
            </>
          )}
        </View>
      </View>
    </Modal>
  );
}

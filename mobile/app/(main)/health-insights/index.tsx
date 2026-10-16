import { useEffect, useRef, useState } from 'react';
import { View, Text, Pressable, TextInput, ActivityIndicator, ScrollView, Modal, Alert } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import * as ImagePicker from 'expo-image-picker';
import * as DocumentPicker from 'expo-document-picker';
import {
  analyzeHealthReport,
  confirmHealthReport,
  deleteHealthReport,
  getHealthReports,
  HEALTH_REPORT_STAGE_ORDER,
  HEALTH_REPORT_STAGE_LABELS,
} from '../../../src/api/healthReport';
import type { HealthReport, HealthReportAnalysisStage, HealthMarker } from '../../../src/api/healthReport';
import { useTheme } from '../../../src/theme/ThemeContext';
import { RADIUS, CARD_SHADOW } from '../../../src/theme/layout';
import ModuleNavBar from '../../../src/components/ModuleNavBar';
import ThemedCard from '../../../src/components/ThemedCard';
import { getMarkerSeverity, type MarkerSeverity } from '../../../src/utils/healthMarkerSeverity';
import { compressHealthReportImage, getCompressionStatusMessage } from '../../../src/utils/imageCompression';

const ERROR_MESSAGES: Record<string, string> = {
  InsufficientCreditsError:
    "You're out of credits for this billing period. Upgrade your plan to keep analyzing reports.",
  UnrecognizedReportError:
    "This doesn't look like a health or lab report — try again with a clear scan or PDF of your report.",
};

// Range-status display — purely factual (below/within/above the
// report's OWN printed range), never a disease name. See backend
// HealthMarkerOut's range_status field docstring.
const RANGE_STATUS_LABEL: Record<string, string> = {
  below: 'Low',
  above: 'High',
  within: 'In range',
};

const RANGE_STATUS_COLOR = (status: string | null, colors: any): string => {
  if (status === 'below' || status === 'above') return colors.danger;
  if (status === 'within') return colors.textSecondary;
  return colors.textMuted;
};

// FIXED (dark mode bug): this used to be hardcoded hex values
// designed only for light mode (light pink/yellow/green backgrounds
// with dark text) — in dark mode, the card's near-white title text
// became unreadable against those light backgrounds, and the small
// priority badge's dark red/brown text became invisible against the
// theme's own dark card background. Now pulls from the theme's
// EXISTING semantic danger/warning/success colors (colors.ts), which
// are already correctly defined for both light AND dark mode.
function priorityBadgeColor(priority: string, colors: any): { bg: string; text: string } {
  if (priority === 'high') return { bg: colors.dangerBg, text: colors.danger };
  if (priority === 'medium') return { bg: colors.warningBg, text: colors.warningText };
  return { bg: colors.successBg, text: colors.successText };
}

// Severity classification (getMarkerSeverity/MarkerSeverity) now
// lives in src/utils/healthMarkerSeverity.ts, shared with
// app/(main)/body-details/index.tsx — previously duplicated
// identically in both files.

// Reuses the app's existing warning/danger theme colors (no new
// colors introduced) — 'high' severity uses the same red as
// dangerBg/danger, 'medium' uses the same amber as warningBg/warningText.
function severityCardStyle(severity: MarkerSeverity, colors: any): { bg: string; border: string; text: string } {
  if (severity === 'high') return { bg: colors.dangerBg, border: colors.danger, text: colors.danger };
  if (severity === 'medium') return { bg: colors.warningBg, border: colors.warningText, text: colors.warningText };
  return { bg: colors.cardBg, border: colors.cardBorder, text: colors.textSecondary };
}

// Review screen ordering: most attention-needing markers first —
// severely high, then severely low, then moderately outside range
// (either direction), then everything within range or lacking a
// reference range to judge by. A stable sort (JS's Array.sort is
// stable) preserves each marker's original position within its rank
// group, so items of equal urgency don't jump around arbitrarily.
function reviewMarkerSortRank(marker: HealthMarker): number {
  const severity = getMarkerSeverity(marker);
  if (severity === 'high' && marker.range_status === 'above') return 0; // Highs
  if (severity === 'high' && marker.range_status === 'below') return 1; // Lows
  if (severity === 'medium') return 2; // Medium
  return 3; // within range / no reference data
}

function sortReviewMarkers(markers: HealthMarker[]): HealthMarker[] {
  return [...markers].sort((a, b) => reviewMarkerSortRank(a) - reviewMarkerSortRank(b));
}

type ScreenState = 'picking' | 'compressing' | 'analyzing' | 'reviewing' | 'results' | 'error';

export default function HealthInsights() {
  const router = useRouter();
  const { colors } = useTheme();
  // "My History" entry point (Home) links here with ?view=history — on
  // mount, that skips the upload screen entirely and jumps straight to
  // the most recently CONFIRMED report's results, if one exists. A
  // normal tap on the main Health Insights card (no param) behaves
  // exactly as before, starting at the upload screen.
  const { view } = useLocalSearchParams<{ view?: string }>();

  const [state, setState] = useState<ScreenState>('picking');
  const [isLoadingHistory, setIsLoadingHistory] = useState(view === 'history');
  const [agreedToDisclaimer, setAgreedToDisclaimer] = useState(false);
  const [compressionStatus, setCompressionStatus] = useState<string>('');

  // The entry ("picking") screen's own "Your Latest Report" panel —
  // distinct from the ?view=history fast-path above, which SKIPS this
  // screen entirely. This runs on every normal visit (no param) so
  // the screen can surface the latest confirmed report inline,
  // alongside the option to upload a new one.
  const [latestConfirmedReport, setLatestConfirmedReport] = useState<HealthReport | null>(null);
  const [currentStage, setCurrentStage] = useState<HealthReportAnalysisStage | null>(null);
  const [currentDetail, setCurrentDetail] = useState<string | null>(null);
  const [result, setResult] = useState<HealthReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Review-stage editable markers (a working copy of extracted_markers —
  // the user can adjust a value before confirming).
  const [reviewMarkers, setReviewMarkers] = useState<HealthMarker[]>([]);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editingValue, setEditingValue] = useState('');
  const [isConfirming, setIsConfirming] = useState(false);
  const [confirmError, setConfirmError] = useState<string | null>(null);

  // Results-screen "show only 3, then Know more" state — one flag per
  // section, so expanding one doesn't affect the others.
  const [showAllPriorities, setShowAllPriorities] = useState(false);
  const [showAllHighlights, setShowAllHighlights] = useState(false);
  const [showAllActions, setShowAllActions] = useState(false);
  const [showAllReviewMarkers, setShowAllReviewMarkers] = useState(false);

  const abortRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    return () => {
      abortRef.current?.();
    };
  }, []);

  // "My History" flow — runs once on mount when opened via
  // ?view=history. Finds the most recently CONFIRMED report (the list
  // is already most-recent-first) and jumps straight to its results;
  // if the user has never confirmed one, falls back to the normal
  // upload screen with a brief explanatory message rather than
  // showing a dead end.
  useEffect(() => {
    if (view !== 'history') return;

    let cancelled = false;

    (async () => {
      try {
        const reports = await getHealthReports();
        const latestConfirmed = reports.find((r) => r.status === 'confirmed');
        if (cancelled) return;

        if (latestConfirmed) {
          setResult(latestConfirmed);
          setState('results');
        } else {
          setError("You haven't confirmed a health report yet — upload one to get started.");
          setState('picking');
        }
      } catch {
        if (cancelled) return;
        setError('Could not load your history — please try again.');
        setState('picking');
      } finally {
        if (!cancelled) setIsLoadingHistory(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [view]);

  // Entry screen's inline "Your Latest Report" panel — runs on every
  // NORMAL visit (no ?view=history param, which has its own loading
  // path above and skips this screen entirely). Silent/non-blocking:
  // the upload UI renders immediately regardless; this panel simply
  // appears once (and if) a confirmed report is found, same
  // philosophy as the other silent Home-screen loaders elsewhere in
  // this app (e.g. loadDailyTip/loadWaterSummary never block Home's
  // core content).
  useEffect(() => {
    if (view === 'history') return;

    let cancelled = false;

    (async () => {
      try {
        const reports = await getHealthReports();
        const latestConfirmed = reports.find((r) => r.status === 'confirmed');
        if (!cancelled && latestConfirmed) {
          setLatestConfirmedReport(latestConfirmed);
        }
      } catch {
        // Silent — this is a nice-to-have panel, not core functionality;
        // the upload flow works fine without it.
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [view]);

  // ---------------------------------------------------
  // Upload
  // ---------------------------------------------------

  /**
   * Determines if a file is an image type that can be compressed.
   * PDFs are not compressed client-side in Phase 1.
   */
  const isCompressibleImage = (mimeType: string): boolean => {
    return mimeType.startsWith('image/') && !mimeType.includes('pdf');
  };

  const handleChooseFile = async () => {
    if (!agreedToDisclaimer) return;
    const pickResult = await DocumentPicker.getDocumentAsync({
      type: ['application/pdf', 'image/jpeg', 'image/png'],
      copyToCacheDirectory: true,
    });

    if (pickResult.canceled || !pickResult.assets?.[0]) return;

    const asset = pickResult.assets[0];
    const mimeType = asset.mimeType ?? 'application/octet-stream';
    const fileName = asset.name ?? 'report.pdf';

    // Check if this is an image that can be compressed
    if (isCompressibleImage(mimeType)) {
      setState('compressing');
      setCompressionStatus(getCompressionStatusMessage('image'));

      try {
        const compressedUri = await compressHealthReportImage(asset.uri, mimeType);
        startAnalysis(compressedUri, mimeType, fileName);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : 'Failed to compress image — please try again'
        );
        setState('error');
      }
    } else {
      // PDFs and other files are uploaded without compression
      startAnalysis(asset.uri, mimeType, fileName);
    }
  };

  const handleTakePhoto = async () => {
    if (!agreedToDisclaimer) return;
    const perm = await ImagePicker.requestCameraPermissionsAsync();
    if (!perm.granted) {
      setError('Camera permission is needed to take a photo.');
      setState('error');
      return;
    }
    const pickResult = await ImagePicker.launchCameraAsync({ quality: 0.7 });
    if (!pickResult.canceled && pickResult.assets[0]) {
      const asset = pickResult.assets[0];
      const mimeType = asset.mimeType ?? 'image/jpeg';

      // Camera photos are always images and benefit from compression
      setState('compressing');
      setCompressionStatus(getCompressionStatusMessage('image'));

      try {
        const compressedUri = await compressHealthReportImage(asset.uri, mimeType);
        startAnalysis(compressedUri, mimeType, 'report.jpg');
      } catch (err) {
        setError(
          err instanceof Error ? err.message : 'Failed to compress image — please try again'
        );
        setState('error');
      }
    }
  };

  const startAnalysis = (uri: string, mimeType: string, fileName: string) => {
    setState('analyzing');
    setCompressionStatus('');
    setCurrentStage(null);
    setCurrentDetail(null);
    setError(null);
    setResult(null);

    abortRef.current = analyzeHealthReport(uri, mimeType, fileName, {
      onStage: (stage, detail) => {
        setCurrentStage(stage as HealthReportAnalysisStage);
        setCurrentDetail(detail ?? null);
      },
      onResult: (report) => {
        setResult(report);
        setCurrentStage(null);
        setCurrentDetail(null);
        // Sorted once here, at load time — editing (handleStartEdit/
        // handleSaveEdit) and confirming both key off this same
        // array's indices, so sorting later or separately would
        // desync the edit UI from what's actually stored.
        setReviewMarkers(sortReviewMarkers(report.extracted_markers));
        setState('reviewing');
      },
      onError: (errorType, detail) => {
        setCurrentStage(null);
        setCurrentDetail(null);
        setError(ERROR_MESSAGES[errorType] ?? detail);
        setState('error');
      },
    });
  };

  const handleStartOver = () => {
    setState('picking');
    setAgreedToDisclaimer(false);
    setResult(null);
    setError(null);
    setReviewMarkers([]);
    setCompressionStatus('');
  };

  const handleViewLatestResults = () => {
    if (latestConfirmedReport) {
      setResult(latestConfirmedReport);
      setState('results');
    }
  };

  const handleShowInfo = () => {
    Alert.alert(
      'About Health Insights',
      'Upload a health or lab report to get personalized, food-based nutrition suggestions. AIMeals never diagnoses or gives medical advice — always consult a healthcare professional about your results.'
    );
  };

  // ---------------------------------------------------
  // Review & Confirm
  // ---------------------------------------------------

  const handleStartEdit = (index: number) => {
    setEditingIndex(index);
    setEditingValue(String(reviewMarkers[index].value));
  };

  const handleSaveEdit = () => {
    if (editingIndex === null) return;
    const parsed = parseFloat(editingValue);
    if (!isNaN(parsed)) {
      setReviewMarkers((prev) =>
        prev.map((m, i) => (i === editingIndex ? { ...m, value: parsed } : m))
      );
    }
    setEditingIndex(null);
  };

  const handleConfirm = async () => {
    if (!result) return;
    setIsConfirming(true);
    setConfirmError(null);
    try {
      const confirmed = await confirmHealthReport(result.id, reviewMarkers);
      setResult(confirmed);
      setState('results');
    } catch (err) {
      setConfirmError(err instanceof Error ? err.message : 'Failed to confirm — please try again');
    } finally {
      setIsConfirming(false);
    }
  };

  // ---------------------------------------------------
  // Delete
  // ---------------------------------------------------

  const handleDelete = async () => {
    if (!result) return;
    try {
      await deleteHealthReport(result.id);
      handleStartOver();
    } catch {
      // Silent failure is acceptable here — the report simply stays
      // visible and the user can retry the delete.
    }
  };

  // ---------------------------------------------------
  // Picking / Analyzing
  // ---------------------------------------------------

  if (isLoadingHistory) {
    return (
      <View style={{ flex: 1, backgroundColor: colors.pageBg, alignItems: 'center', justifyContent: 'center' }}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={{ fontSize: 13, color: colors.textSecondary, marginTop: 12 }}>
          Loading your health insights…
        </Text>
      </View>
    );
  }

  if (state === 'picking' || state === 'compressing' || state === 'analyzing') {
    return (
      <View style={{ flex: 1, backgroundColor: colors.pageBg }}>
        <ScrollView contentContainerStyle={{ padding: 20, paddingTop: 60, flexGrow: 1 }}>
          <View
            style={{
              flexDirection: 'row',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: 20,
            }}
          >
            <Pressable onPress={() => router.back()}>
              <Text style={{ fontSize: 18, color: colors.textPrimary }}>‹</Text>
            </Pressable>
            <Text style={{ fontSize: 17, fontWeight: '700', color: colors.textPrimary }}>
              Health Insights 🩺
            </Text>
            <Pressable onPress={handleShowInfo}>
              <Text style={{ fontSize: 16, color: colors.textPrimary }}>ⓘ</Text>
            </Pressable>
          </View>

          <Text style={{ fontSize: 13, color: colors.textSecondary, marginBottom: 20 }}>
            Understand your health. Eat better.
          </Text>

          <ThemedCard style={{ backgroundColor: colors.surfaceAlt, marginBottom: 20 }} padding={16}>
            <Text style={{ fontSize: 13, color: colors.textSecondary, lineHeight: 19 }}>
              Upload your health report to get personalized nutrition insights and food
              suggestions.
            </Text>
          </ThemedCard>

          {/* Shown when "My History" (Home) found no confirmed report to
              jump to — a gentle nudge rather than a dead-end error
              screen, since this is an entirely normal first-time state. */}
          {error && state === 'picking' && (
            <ThemedCard style={{ backgroundColor: colors.warningBg, marginBottom: 16 }} padding={12}>
              <Text style={{ fontSize: 12, color: colors.warningText }}>{error}</Text>
            </ThemedCard>
          )}

          {state === 'compressing' && (
            // Shown while compressing the selected image before upload.
            // This can take 1-2 seconds on typical Android devices for a
            // 4-5MB file down to 500KB, so users need feedback.
            <ThemedCard style={{ backgroundColor: colors.surfaceAlt, alignItems: 'center' }} padding={24}>
              <ActivityIndicator size="large" color={colors.primary} style={{ marginBottom: 14 }} />
              <Text style={{ fontSize: 14, fontWeight: '700', color: colors.textPrimary, marginBottom: 4 }}>
                {compressionStatus || 'Compressing image…'}
              </Text>
              <Text style={{ fontSize: 12, color: colors.textSecondary, textAlign: 'center' }}>
                Optimizing for faster upload (87% size reduction)
              </Text>
            </ThemedCard>
          )}

          {state === 'analyzing' && !currentStage ? (
            // Shown during the actual file upload — before the server
            // has emitted even its FIRST stage event. A multi-MB PDF
            // over a slower connection can take several real seconds
            // here with zero backend feedback yet (the stage list
            // below only starts updating once "checking_credits"
            // arrives), so without this the screen looked frozen.
            <ThemedCard style={{ backgroundColor: colors.surfaceAlt, alignItems: 'center' }} padding={24}>
              <ActivityIndicator size="large" color={colors.primary} style={{ marginBottom: 14 }} />
              <Text style={{ fontSize: 14, fontWeight: '700', color: colors.textPrimary, marginBottom: 4 }}>
                Uploading your report…
              </Text>
              <Text style={{ fontSize: 12, color: colors.textSecondary, textAlign: 'center' }}>
                This may take a moment for larger files.
              </Text>
            </ThemedCard>
          ) : state === 'analyzing' ? (
            <ThemedCard style={{ backgroundColor: colors.surfaceAlt }} padding={18}>
              <Text style={{ fontSize: 14, fontWeight: '700', color: colors.textPrimary, marginBottom: 4 }}>
                Analyzing your report…
              </Text>
              {currentDetail && (
                <Text
                  style={{ fontSize: 12, color: colors.primary, marginBottom: 10, fontStyle: 'italic' }}
                  numberOfLines={1}
                >
                  {currentDetail}
                </Text>
              )}
              <View style={{ marginTop: currentDetail ? 4 : 10 }} />
              {HEALTH_REPORT_STAGE_ORDER.map((stage) => {
                const currentIndex = currentStage ? HEALTH_REPORT_STAGE_ORDER.indexOf(currentStage) : -1;
                const thisIndex = HEALTH_REPORT_STAGE_ORDER.indexOf(stage);
                const isDone = thisIndex < currentIndex;
                const isActive = stage === currentStage;
                return (
                  <View key={stage} style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 8 }}>
                    <Text style={{ width: 18, fontSize: 12 }}>{isDone ? '✓' : isActive ? '' : '○'}</Text>
                    {isActive && <ActivityIndicator size="small" color={colors.primary} style={{ marginRight: 6 }} />}
                    <Text
                      style={{
                        fontSize: 13,
                        color: isDone || isActive ? colors.textPrimary : colors.textMuted,
                        fontWeight: isActive ? '600' : '400',
                      }}
                    >
                      {HEALTH_REPORT_STAGE_LABELS[stage]}
                    </Text>
                  </View>
                );
              })}
            </ThemedCard>
          ) : (
            <>
              {/* "Your Latest Report" panel — only shown when a
                  confirmed report already exists; entirely absent for
                  a genuine first-time user, who goes straight to the
                  upload dropzone below with no "OR" divider. */}
              {latestConfirmedReport && (
                <>
                  <View
                    style={{
                      flexDirection: 'row',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      marginBottom: 10,
                    }}
                  >
                    <Text style={{ fontSize: 14, fontWeight: '700', color: colors.textPrimary }}>
                      Your Latest Report
                    </Text>
                    <View
                      style={{
                        backgroundColor: colors.surfaceAlt,
                        borderRadius: 100,
                        paddingHorizontal: 8,
                        paddingVertical: 2,
                      }}
                    >
                      <Text style={{ fontSize: 10, fontWeight: '700', color: colors.primary }}>
                        Most Recent
                      </Text>
                    </View>
                  </View>

                  <Pressable
                    onPress={handleViewLatestResults}
                    style={{ marginBottom: 14 }}
                  >
                    <ThemedCard style={{ flexDirection: 'row', alignItems: 'center' }}>
                      <Text style={{ fontSize: 22, marginRight: 12 }}>📄</Text>
                      <View style={{ flex: 1 }}>
                        <Text style={{ fontSize: 13, fontWeight: '700', color: colors.textPrimary }} numberOfLines={1}>
                          {latestConfirmedReport.report_label ?? 'Health Report'}
                        </Text>
                        <Text style={{ fontSize: 11, color: colors.textMuted, marginTop: 2 }}>
                          Analyzed on {new Date(latestConfirmedReport.created_at).toLocaleDateString()}
                        </Text>
                        <View
                          style={{
                            alignSelf: 'flex-start',
                            backgroundColor: colors.surfaceAlt,
                            borderRadius: 100,
                            paddingHorizontal: 8,
                            paddingVertical: 2,
                            marginTop: 6,
                          }}
                        >
                          <Text style={{ fontSize: 10, fontWeight: '600', color: colors.primary }}>
                            Results available ✓
                          </Text>
                        </View>
                      </View>
                      <Text style={{ fontSize: 16, color: colors.textMuted }}>›</Text>
                    </ThemedCard>
                  </Pressable>

                  <ThemedCard style={{ backgroundColor: colors.surfaceAlt, marginBottom: 14 }}>
                    <Text style={{ fontSize: 12, color: colors.textSecondary, lineHeight: 17, marginBottom: 10 }}>
                      📈 We'll use your latest report to personalize your food choices and show
                      improvements.
                    </Text>
                    <Pressable
                      onPress={handleViewLatestResults}
                      style={{
                        backgroundColor: colors.primary,
                        borderRadius: RADIUS.button,
                        paddingVertical: 13,
                        alignItems: 'center',
                      }}
                    >
                      <Text style={{ color: '#fff', fontWeight: '700', fontSize: 14 }}>
                        View Latest Results
                      </Text>
                    </Pressable>
                  </ThemedCard>

                  <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 16 }}>
                    <View style={{ flex: 1, height: 1, backgroundColor: colors.cardBorder }} />
                    <Text style={{ fontSize: 11, fontWeight: '700', color: colors.textMuted, marginHorizontal: 10 }}>
                      OR
                    </Text>
                    <View style={{ flex: 1, height: 1, backgroundColor: colors.cardBorder }} />
                  </View>

                  <Text style={{ fontSize: 14, fontWeight: '700', color: colors.textPrimary, marginBottom: 4 }}>
                    Upload New Report
                  </Text>
                  <Text style={{ fontSize: 12, color: colors.textSecondary, marginBottom: 16, lineHeight: 17 }}>
                    Upload a new report to get updated insights and see your progress over time.
                  </Text>
                </>
              )}

              <Text style={{ fontSize: 13, fontWeight: '600', color: colors.textPrimary, marginBottom: 10 }}>
                Upload your health report
              </Text>
              <Text style={{ fontSize: 11, color: colors.textMuted, marginBottom: 12 }}>
                Supports PDF, JPG, PNG
              </Text>

              {/* Both upload paths stay disabled until the disclaimer below
                  is ticked — the checkbox used to be purely decorative. */}
              <Pressable
                onPress={handleChooseFile}
                disabled={!agreedToDisclaimer}
                style={{
                  backgroundColor: colors.primary,
                  borderRadius: RADIUS.button,
                  paddingVertical: 14,
                  alignItems: 'center',
                  marginBottom: 10,
                  opacity: agreedToDisclaimer ? 1 : 0.45,
                  ...CARD_SHADOW,
                }}
              >
                <Text style={{ color: '#fff', fontWeight: '700', fontSize: 14 }}>Choose File</Text>
              </Pressable>

              <Pressable
                onPress={handleTakePhoto}
                disabled={!agreedToDisclaimer}
                style={{
                  borderWidth: 1,
                  borderColor: colors.cardBorder,
                  borderRadius: RADIUS.button,
                  paddingVertical: 14,
                  alignItems: 'center',
                  marginBottom: agreedToDisclaimer ? 20 : 8,
                  opacity: agreedToDisclaimer ? 1 : 0.45,
                }}
              >
                <Text style={{ color: colors.textPrimary, fontWeight: '700', fontSize: 14 }}>Take Photo</Text>
              </Pressable>
              {!agreedToDisclaimer && (
                <Text style={{ fontSize: 11, color: colors.textMuted, marginBottom: 20, textAlign: 'center' }}>
                  Read the disclaimer below and tick the box to enable uploading.
                </Text>
              )}

              <ThemedCard style={{ backgroundColor: colors.surfaceAlt, marginBottom: 16 }}>
                <Text style={{ fontSize: 12, fontWeight: '700', color: colors.textPrimary, marginBottom: 8 }}>
                  ✨ Why upload a new report?
                </Text>
                {[
                  'Track improvements in your health markers',
                  'Get updated nutrition priorities',
                  'See how your food choices can improve further',
                ].map((line) => (
                  <View key={line} style={{ flexDirection: 'row', alignItems: 'flex-start', marginBottom: 4 }}>
                    <Text style={{ color: colors.primary, marginRight: 6, fontSize: 12 }}>✓</Text>
                    <Text style={{ fontSize: 12, color: colors.textSecondary, flex: 1, lineHeight: 16 }}>
                      {line}
                    </Text>
                  </View>
                ))}
              </ThemedCard>

              <Text style={{ fontSize: 11, color: colors.textMuted, marginBottom: 20 }}>
                🔒 Your data is private and secure. Only you can view your reports.
              </Text>

              <ThemedCard style={{ backgroundColor: colors.warningBg, marginBottom: 16 }}>
                <Text style={{ fontSize: 11, fontWeight: '700', color: colors.warningText, marginBottom: 6 }}>
                  ⚠️ Important Disclaimer
                </Text>
                <Text style={{ fontSize: 11, color: colors.warningText, lineHeight: 16 }}>
                  AIMeals provides AI-generated nutrition information and meal suggestions for
                  informational purposes only. It is not a medical device and does not diagnose,
                  treat, cure, or prevent medical conditions. AI may make mistakes or misinterpret
                  uploaded reports. Do not make medical decisions or change medications or
                  treatment based solely on AIMeals. Please consult a qualified healthcare
                  professional before acting on these suggestions.
                </Text>
              </ThemedCard>

              <Pressable
                onPress={() => setAgreedToDisclaimer((prev) => !prev)}
                style={{ flexDirection: 'row', alignItems: 'flex-start', marginBottom: 20 }}
              >
                <View
                  style={{
                    width: 18,
                    height: 18,
                    borderRadius: 4,
                    borderWidth: 1,
                    borderColor: colors.cardBorder,
                    backgroundColor: agreedToDisclaimer ? colors.primary : 'transparent',
                    marginRight: 10,
                    marginTop: 1,
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  {agreedToDisclaimer && <Text style={{ color: '#fff', fontSize: 12 }}>✓</Text>}
                </View>
                <Text style={{ fontSize: 12, color: colors.textSecondary, flex: 1 }}>
                  I understand and agree to the above information.
                </Text>
              </Pressable>
            </>
          )}
        </ScrollView>

        <ModuleNavBar currentKey="health_insights" />
      </View>
    );
  }

  // ---------------------------------------------------
  // Error state
  // ---------------------------------------------------

  if (state === 'error') {
    return (
      <View style={{ flex: 1, backgroundColor: colors.pageBg, alignItems: 'center', justifyContent: 'center', padding: 24 }}>
        <Text style={{ fontSize: 36, marginBottom: 12 }}>😕</Text>
        <Text style={{ fontSize: 17, fontWeight: '700', color: colors.textPrimary, marginBottom: 6, textAlign: 'center' }}>
          Couldn't analyze this report
        </Text>
        <Text style={{ fontSize: 13, color: colors.textSecondary, marginBottom: 24, textAlign: 'center' }}>
          {error ?? 'Something went wrong while analyzing your report.'}
        </Text>
        <Pressable
          onPress={handleStartOver}
          style={{ backgroundColor: colors.primary, borderRadius: RADIUS.button, paddingVertical: 12, paddingHorizontal: 28 }}
        >
          <Text style={{ color: '#fff', fontWeight: '700', fontSize: 14 }}>Try Again</Text>
        </Pressable>
      </View>
    );
  }

  // ---------------------------------------------------
  // Reviewing (edit before confirm)
  // ---------------------------------------------------

  if (state === 'reviewing') {
    return (
      <View style={{ flex: 1, backgroundColor: colors.pageBg }}>
        <ScrollView contentContainerStyle={{ padding: 20, paddingTop: 60, paddingBottom: 40 }}>
          <Text style={{ fontSize: 20, fontWeight: '700', color: colors.textPrimary, marginBottom: 4 }}>
            Review Your Report
          </Text>
          <Text style={{ fontSize: 13, color: colors.textSecondary, marginBottom: 20 }}>
            Please review and confirm the extracted information. Tap any value to correct it.
          </Text>

          <View style={{ gap: 10, marginBottom: 8 }}>
            {(showAllReviewMarkers ? reviewMarkers : reviewMarkers.slice(0, 3)).map((marker, index) => {
              const severity = getMarkerSeverity(marker);
              const severityStyle = severityCardStyle(severity, colors);
              return (
              <ThemedCard
                key={`${marker.name}-${index}`}
                style={{
                  backgroundColor: severityStyle.bg,
                  borderWidth: 1,
                  borderColor: severityStyle.border,
                }}
              >
                <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Text style={{ fontSize: 13, fontWeight: '600', color: colors.textPrimary, flex: 1 }}>
                    {marker.name}
                  </Text>
                  {marker.range_status && (
                    <Text
                      style={{
                        fontSize: 11,
                        fontWeight: '700',
                        color: severityStyle.text,
                      }}
                    >
                      {RANGE_STATUS_LABEL[marker.range_status]}
                    </Text>
                  )}
                </View>

                {editingIndex === index ? (
                  <View style={{ flexDirection: 'row', alignItems: 'center', marginTop: 8, gap: 8 }}>
                    <TextInput
                      value={editingValue}
                      onChangeText={setEditingValue}
                      keyboardType="numeric"
                      autoFocus
                      style={{
                        flex: 1,
                        borderWidth: 1,
                        borderColor: colors.primary,
                        borderRadius: 8,
                        paddingHorizontal: 10,
                        paddingVertical: 6,
                        fontSize: 14,
                        color: colors.textPrimary,
                      }}
                    />
                    <Pressable
                      onPress={handleSaveEdit}
                      style={{ backgroundColor: colors.primary, borderRadius: 8, paddingHorizontal: 12, paddingVertical: 8 }}
                    >
                      <Text style={{ color: '#fff', fontSize: 12, fontWeight: '700' }}>Save</Text>
                    </Pressable>
                  </View>
                ) : (
                  <Pressable onPress={() => handleStartEdit(index)} style={{ marginTop: 6 }}>
                    <Text style={{ fontSize: 15, fontWeight: '700', color: colors.textPrimary }}>
                      {marker.value} {marker.unit ?? ''}
                      <Text style={{ fontSize: 11, fontWeight: '400', color: colors.textMuted }}>
                        {'  '}Edit ›
                      </Text>
                    </Text>
                    {marker.reference_range_text && (
                      <Text style={{ fontSize: 11, color: colors.textMuted, marginTop: 2 }}>
                        Reference: {marker.reference_range_text}
                      </Text>
                    )}
                  </Pressable>
                )}
              </ThemedCard>
              );
            })}
          </View>

          {reviewMarkers.length > 3 && (
            <Pressable onPress={() => setShowAllReviewMarkers((prev) => !prev)} style={{ marginBottom: 20 }}>
              <Text style={{ fontSize: 12, fontWeight: '600', color: colors.primary }}>
                {showAllReviewMarkers ? '‹ Show less' : `Know more (${reviewMarkers.length}) ›`}
              </Text>
            </Pressable>
          )}
          {reviewMarkers.length <= 3 && <View style={{ marginBottom: 12 }} />}

          {confirmError && (
            <ThemedCard style={{ backgroundColor: colors.dangerBg, marginBottom: 14 }} padding={12}>
              <Text style={{ color: colors.danger, fontSize: 12 }}>{confirmError}</Text>
            </ThemedCard>
          )}

          <Pressable
            onPress={handleConfirm}
            disabled={isConfirming}
            style={{
              backgroundColor: colors.primary,
              borderRadius: RADIUS.button,
              paddingVertical: 15,
              alignItems: 'center',
              opacity: isConfirming ? 0.6 : 1,
            }}
          >
            {isConfirming ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={{ color: '#fff', fontWeight: '700', fontSize: 15 }}>Confirm & Continue</Text>
            )}
          </Pressable>
        </ScrollView>
      </View>
    );
  }

  // ---------------------------------------------------
  // Results
  // ---------------------------------------------------

  const priorities = result?.nutrition_priorities ?? [];
  const highlightMarkers = (result?.confirmed_markers ?? []).filter(
    (m) => m.range_status === 'above' || m.range_status === 'below'
  );
  const allActionItems = priorities.flatMap((p) => p.action_items);

  return (
    <View style={{ flex: 1, backgroundColor: colors.pageBg }}>
      <ScrollView contentContainerStyle={{ padding: 20, paddingTop: 60, paddingBottom: 40 }}>
        <Pressable onPress={() => router.back()} style={{ marginBottom: 16 }}>
          <Text style={{ fontSize: 13, color: colors.textSecondary }}>‹ Back</Text>
        </Pressable>

        <Text style={{ fontSize: 20, fontWeight: '700', color: colors.textPrimary, marginBottom: 4 }}>
          Your Health Insights
        </Text>
        <Text style={{ fontSize: 12, color: colors.textSecondary, marginBottom: 4 }}>
          Based on your uploaded and confirmed report information.
        </Text>
        {result?.created_at && (
          <Text style={{ fontSize: 11, color: colors.textMuted, marginBottom: 20 }}>
            Analyzed on {new Date(result.created_at).toLocaleDateString()}
          </Text>
        )}

        {priorities.length > 0 && (
          <>
            <Text style={{ fontSize: 13, fontWeight: '700', color: colors.textPrimary, marginBottom: 10 }}>
              🎯 Nutrition Priorities
            </Text>
            <View style={{ gap: 10, marginBottom: 8 }}>
              {(showAllPriorities ? priorities : priorities.slice(0, 3)).map((p) => {
                const badge = priorityBadgeColor(p.priority, colors);
                return (
                  <ThemedCard
                    key={p.key}
                    style={{
                      backgroundColor: badge.bg,
                      borderWidth: 1,
                      borderColor: badge.text,
                      borderLeftWidth: 4,
                    }}
                  >
                    <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 6 }}>
                      <Text style={{ fontSize: 14, fontWeight: '700', color: colors.textPrimary, flex: 1 }}>
                        {p.title}
                      </Text>
                      <View style={{ backgroundColor: colors.cardBg, borderRadius: 100, paddingHorizontal: 8, paddingVertical: 2 }}>
                        <Text style={{ fontSize: 10, fontWeight: '700', color: badge.text }}>
                          {p.priority.toUpperCase()}
                        </Text>
                      </View>
                    </View>
                    <Text style={{ fontSize: 12, color: colors.textSecondary, lineHeight: 17 }}>
                      {p.description}
                    </Text>
                  </ThemedCard>
                );
              })}
            </View>
            {priorities.length > 3 && (
              <Pressable onPress={() => setShowAllPriorities((prev) => !prev)} style={{ marginBottom: 24 }}>
                <Text style={{ fontSize: 12, fontWeight: '600', color: colors.primary }}>
                  {showAllPriorities ? '‹ Show less' : `Know more (${priorities.length}) ›`}
                </Text>
              </Pressable>
            )}
            {priorities.length <= 3 && <View style={{ marginBottom: 16 }} />}
          </>
        )}

        {highlightMarkers.length > 0 && (
          <>
            <Text style={{ fontSize: 13, fontWeight: '700', color: colors.textPrimary, marginBottom: 10 }}>
              📊 Key Report Highlights
            </Text>
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginBottom: 8 }}>
              {(showAllHighlights ? highlightMarkers : highlightMarkers.slice(0, 3)).map((m, i) => {
                const severity = getMarkerSeverity(m);
                const style = severityCardStyle(severity, colors);
                return (
                  <ThemedCard
                    key={`${m.name}-${i}`}
                    style={{ width: '47%', backgroundColor: style.bg, borderWidth: 1, borderColor: style.border }}
                    padding={12}
                  >
                    <Text style={{ fontSize: 12, fontWeight: '600', color: colors.textPrimary }} numberOfLines={1}>
                      {m.name}
                    </Text>
                    <Text style={{ fontSize: 14, fontWeight: '700', color: colors.textPrimary, marginTop: 2 }}>
                      {m.value} {m.unit ?? ''}
                    </Text>
                    <Text style={{ fontSize: 11, fontWeight: '700', color: style.text, marginTop: 2 }}>
                      {m.range_status ? RANGE_STATUS_LABEL[m.range_status] : ''}
                    </Text>
                  </ThemedCard>
                );
              })}
            </View>
            {highlightMarkers.length > 3 && (
              <Pressable onPress={() => setShowAllHighlights((prev) => !prev)} style={{ marginBottom: 24 }}>
                <Text style={{ fontSize: 12, fontWeight: '600', color: colors.primary }}>
                  {showAllHighlights ? '‹ Show less' : `Know more (${highlightMarkers.length}) ›`}
                </Text>
              </Pressable>
            )}
            {highlightMarkers.length <= 3 && <View style={{ marginBottom: 16 }} />}
          </>
        )}

        {allActionItems.length > 0 && (
          <>
            <Text style={{ fontSize: 13, fontWeight: '700', color: colors.textPrimary, marginBottom: 10 }}>
              💡 What You Can Focus On
            </Text>
            <View style={{ marginBottom: 8 }}>
              {(showAllActions ? allActionItems : allActionItems.slice(0, 3)).map((item, i) => (
                <View key={i} style={{ flexDirection: 'row', alignItems: 'flex-start', marginBottom: 8 }}>
                  <Text style={{ color: colors.primary, marginRight: 8 }}>✓</Text>
                  <Text style={{ fontSize: 12, color: colors.textSecondary, flex: 1, lineHeight: 17 }}>
                    {item}
                  </Text>
                </View>
              ))}
            </View>
            {allActionItems.length > 3 && (
              <Pressable onPress={() => setShowAllActions((prev) => !prev)} style={{ marginBottom: 24 }}>
                <Text style={{ fontSize: 12, fontWeight: '600', color: colors.primary }}>
                  {showAllActions ? '‹ Show less' : `Know more (${allActionItems.length}) ›`}
                </Text>
              </Pressable>
            )}
            {allActionItems.length <= 3 && <View style={{ marginBottom: 16 }} />}
          </>
        )}

        <Text style={{ fontSize: 13, fontWeight: '700', color: colors.textPrimary, marginBottom: 4 }}>
          Put Your Insights Into Action
        </Text>
        <Text style={{ fontSize: 11, color: colors.textMuted, lineHeight: 15, marginBottom: 12 }}>
          Generate a personalised meal plan, explore suitable recipes, or ask your Nutrition
          Coach about the foods that may support your health goals.
        </Text>
        {/* Navigation itself stays simple (no report-id params) — the
            backend already carries this report's confirmed nutrition
            priorities into recipe/meal-plan/coach generation
            automatically via AIService._build_nutrition_focus_context(),
            which always reads the user's LATEST CONFIRMED health
            report. The "Recipes" card below additionally passes a
            PRE-FILLED starting request (built from the top priorities)
            purely as a convenience so the user isn't staring at a
            blank text box — it changes nothing about what the backend
            actually applies, since that happens automatically
            regardless of what's typed. If a future design supports
            multiple simultaneous report contexts, that would need a
            real backend parameter added first — not invented here. */}
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginBottom: 24 }}>
          <Pressable
            onPress={() => {
              const suggestion =
                priorities.length > 0
                  ? `A recipe to help with: ${priorities.slice(0, 2).map((p) => p.title).join(' and ')}`
                  : undefined;
              router.push({
                pathname: '/(main)/recipes',
                params: { tab: 'discover', ...(suggestion ? { prefill: suggestion } : {}) },
              } as any);
            }}
            style={{ flex: 1, minWidth: '30%' }}
          >
            <ThemedCard style={{ backgroundColor: colors.surfaceAlt, borderColor: 'transparent', alignItems: 'center' }}>
              <Text style={{ fontSize: 20, marginBottom: 6 }}>🍽️</Text>
              <Text style={{ fontSize: 12, fontWeight: '600', color: colors.textPrimary, marginBottom: 2 }}>
                Recipes
              </Text>
              <Text style={{ fontSize: 9, color: colors.textMuted, textAlign: 'center' }} numberOfLines={2}>
                Find meals suitable for you
              </Text>
            </ThemedCard>
          </Pressable>
          <Pressable
            onPress={() => {
              const suggestion =
                priorities.length > 0
                  ? `Focus on: ${priorities.slice(0, 2).map((p) => p.title).join(' and ')}`
                  : undefined;
              router.push({
                pathname: '/(main)/meal-plans/new',
                params: suggestion ? { prefill: suggestion } : {},
              } as any);
            }}
            style={{ flex: 1, minWidth: '30%' }}
          >
            <ThemedCard style={{ backgroundColor: colors.surfaceAlt, borderColor: 'transparent', alignItems: 'center' }}>
              <Text style={{ fontSize: 20, marginBottom: 6 }}>📅</Text>
              <Text style={{ fontSize: 12, fontWeight: '600', color: colors.textPrimary, marginBottom: 2 }}>
                Meal Plan
              </Text>
              <Text style={{ fontSize: 9, color: colors.textMuted, textAlign: 'center' }} numberOfLines={2}>
                Generate a health-focused meal plan
              </Text>
            </ThemedCard>
          </Pressable>
          <Pressable
            onPress={() => router.push('/(main)/coach' as any)}
            style={{ flex: 1, minWidth: '30%' }}
          >
            <ThemedCard style={{ backgroundColor: colors.surfaceAlt, borderColor: 'transparent', alignItems: 'center' }}>
              <Text style={{ fontSize: 20, marginBottom: 6 }}>💬</Text>
              <Text style={{ fontSize: 12, fontWeight: '600', color: colors.textPrimary, marginBottom: 2 }}>
                Ask Coach
              </Text>
              <Text style={{ fontSize: 9, color: colors.textMuted, textAlign: 'center' }} numberOfLines={2}>
                Ask about your diet & food choices
              </Text>
            </ThemedCard>
          </Pressable>
        </View>

        <Pressable
          onPress={handleDelete}
          style={{
            borderWidth: 1,
            borderColor: colors.dangerBg,
            borderRadius: RADIUS.button,
            paddingVertical: 12,
            alignItems: 'center',
            marginBottom: 20,
          }}
        >
          <Text style={{ color: colors.danger, fontWeight: '600', fontSize: 13 }}>🗑️ Delete Report</Text>
        </Pressable>

        <ThemedCard style={{ backgroundColor: colors.surfaceAlt }} padding={12}>
          <Text style={{ fontSize: 11, color: colors.textMuted, textAlign: 'center', lineHeight: 15 }}>
            AI can make mistakes. Please consult a qualified healthcare professional before
            acting on these suggestions.
          </Text>
        </ThemedCard>
      </ScrollView>

      <ModuleNavBar currentKey="health_insights" />
    </View>
  );
}

import { useEffect, useRef, useState } from 'react';
import * as SecureStore from 'expo-secure-store';
import {
  View,
  Text,
  TextInput,
  Pressable,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
  Image,
} from 'react-native';
import { useRouter } from 'expo-router';
import { LinearGradient } from 'expo-linear-gradient';
import { sendChatMessage } from '../../../src/api/aiChat';
import MarkdownText from '../../../src/components/MarkdownText';
import ModuleNavBar from '../../../src/components/ModuleNavBar';
import ThemedCard from '../../../src/components/ThemedCard';
import { useTheme } from '../../../src/theme/ThemeContext';
import { RADIUS } from '../../../src/theme/layout';

// Characters revealed per tick and tick interval — tuned for a natural
// typing feel (~165 chars/sec) independent of how bursty the network
// delivery actually is. See the reveal-loop comment below for why this
// exists at all.
const REVEAL_CHARS_PER_TICK = 3;
const REVEAL_TICK_MS = 18;

// Persists the chat session_id across app restarts, so the Coach's
// short-term conversation-history context (see
// AIContextBuilder._build_conversation_section on the backend)
// still applies to "the same chat" after the user closes and
// reopens the app, rather than silently starting a fresh session
// (with no prior-exchange context) every time this screen mounts.
const COACH_SESSION_STORAGE_KEY = 'aimeals_coach_session_id';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  isStreaming?: boolean;
  timestamp: string;
}

function formatTime(): string {
  const now = new Date();
  let hours = now.getHours();
  const minutes = now.getMinutes().toString().padStart(2, '0');
  const ampm = hours >= 12 ? 'PM' : 'AM';
  hours = hours % 12 || 12;
  return `${hours}:${minutes} ${ampm}`;
}

let messageIdCounter = 0;
function nextId() {
  messageIdCounter += 1;
  return `msg-${messageIdCounter}`;
}

// Static conversation-starter chips — deliberately simple: each just
// sends a natural-language prompt to the coach, same as if the user
// typed it. No deep-linking into other screens or new backend calls —
// keeps this a pure chat-module improvement, not a dependency on
// features (Scan, Nutrition Logs) that don't exist yet.
const QUICK_ACTIONS: { label: string; prompt: string }[] = [
  { label: '🍳 Suggest breakfast', prompt: 'Can you suggest a healthy breakfast for me?' },
  { label: '🥗 Healthy lunch', prompt: 'What would be a good healthy lunch option today?' },
  { label: '🍽 Plan dinner', prompt: 'Give me a dinner idea for tonight.' },
  { label: '💪 High protein', prompt: 'What are some high-protein foods or meal ideas?' },
  { label: '🥤 Quick snack', prompt: 'Suggest a quick, healthy snack.' },
];

export default function Coach() {
  const router = useRouter();
  const { colors } = useTheme();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [upsellMessage, setUpsellMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const abortRef = useRef<(() => void) | null>(null);
  const scrollRef = useRef<ScrollView>(null);

  // Smoothing layer: raw network chunks (via onChunk below) can arrive in
  // uneven bursts on React Native — the underlying XHR/networking layer
  // doesn't guarantee the same smooth per-chunk delivery a browser gives
  // you. Rather than render each burst directly (which looks jumpy), we
  // push arriving text into `pendingRef` and a separate steady-interval
  // loop drains it a few characters at a time onto the screen — the same
  // technique used in aimeals_chat_demo.html's revealText(). This makes
  // the visible typing speed constant and smooth regardless of how
  // bursty the actual network delivery is underneath.
  const pendingRef = useRef('');
  const streamEndedRef = useRef(false);
  const revealTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Load any previously-persisted session_id on mount, so a message
  // sent right after reopening the app still continues the same
  // conversation instead of silently starting a new one.
  useEffect(() => {
    SecureStore.getItemAsync(COACH_SESSION_STORAGE_KEY)
      .then((stored) => {
        if (stored) sessionIdRef.current = stored;
      })
      .catch(() => {
        // Best-effort — a read failure just means this message starts
        // a fresh session, same as a first-ever launch.
      });
  }, []);

  useEffect(() => {
    return () => {
      abortRef.current?.();
      if (revealTimerRef.current) clearInterval(revealTimerRef.current);
    };
  }, []);

  // "New conversation" — clears the on-screen thread and the
  // persisted session_id, so the next message starts a genuinely
  // fresh session (no prior-exchange context pulled in). Does NOT
  // touch remembered Coach-memory facts (dietary preferences/goals)
  // — those are deliberately cross-session and controlled separately
  // from Settings, not tied to any one conversation thread.
  const startNewConversation = () => {
    abortRef.current?.();
    if (revealTimerRef.current) {
      clearInterval(revealTimerRef.current);
      revealTimerRef.current = null;
    }
    pendingRef.current = '';
    streamEndedRef.current = false;
    sessionIdRef.current = null;
    setMessages([]);
    setIsSending(false);
    setUpsellMessage(null);
    setError(null);
    SecureStore.deleteItemAsync(COACH_SESSION_STORAGE_KEY).catch(() => {});
  };

  const scrollToBottom = () => {
    setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 50);
  };

  const startRevealLoop = (assistantMessageId: string) => {
    if (revealTimerRef.current) return; // already running for this message

    revealTimerRef.current = setInterval(() => {
      if (pendingRef.current.length === 0) {
        if (streamEndedRef.current) {
          // Network finished AND we've drained everything queued —
          // only now is the message actually fully revealed.
          if (revealTimerRef.current) clearInterval(revealTimerRef.current);
          revealTimerRef.current = null;
          setMessages((prev) =>
            prev.map((m) => (m.id === assistantMessageId ? { ...m, isStreaming: false } : m))
          );
          setIsSending(false);
        }
        return;
      }

      const next = pendingRef.current.slice(0, REVEAL_CHARS_PER_TICK);
      pendingRef.current = pendingRef.current.slice(REVEAL_CHARS_PER_TICK);

      setMessages((prev) =>
        prev.map((m) => (m.id === assistantMessageId ? { ...m, text: m.text + next } : m))
      );
      scrollToBottom();
    }, REVEAL_TICK_MS);
  };

  const handleSend = (overrideText?: string) => {
    const trimmed = (overrideText ?? input).trim();
    if (!trimmed || isSending) return;

    setError(null);
    setUpsellMessage(null);
    setInput('');

    const userMessage: ChatMessage = {
      id: nextId(),
      role: 'user',
      text: trimmed,
      timestamp: formatTime(),
    };
    const assistantMessageId = nextId();
    const assistantMessage: ChatMessage = {
      id: assistantMessageId,
      role: 'assistant',
      text: '',
      isStreaming: true,
      timestamp: formatTime(),
    };

    setMessages((prev) => [...prev, userMessage, assistantMessage]);
    setIsSending(true);
    scrollToBottom();

    pendingRef.current = '';
    streamEndedRef.current = false;

    abortRef.current = sendChatMessage(trimmed, sessionIdRef.current, {
      onChunk: (text) => {
        // Queue it — don't render directly. The reveal loop (started
        // below on first chunk) drains this at a steady pace.
        pendingRef.current += text;
        startRevealLoop(assistantMessageId);
      },
      onUpsell: (message) => {
        setUpsellMessage(message);
      },
      onSession: (sid) => {
        sessionIdRef.current = sid;
        SecureStore.setItemAsync(COACH_SESSION_STORAGE_KEY, sid).catch(() => {});
        // Always arrives last, regardless of success/error — see
        // aiChat.ts's docstring. Mark the network side done; the reveal
        // loop finishes draining any remaining buffered text on its own
        // and only THEN marks the message as no longer streaming.
        streamEndedRef.current = true;
        // Edge case: if no chunks ever arrived (empty reply) and the
        // reveal loop was never started, there's nothing to drain it —
        // finish immediately here instead of waiting forever.
        if (!revealTimerRef.current) {
          setMessages((prev) =>
            prev.map((m) => (m.id === assistantMessageId ? { ...m, isStreaming: false } : m))
          );
          setIsSending(false);
        }
      },
      onError: (errorType, detail) => {
        streamEndedRef.current = true;
        if (!revealTimerRef.current) {
          setIsSending(false);
          setMessages((prev) =>
            prev.map((m) => (m.id === assistantMessageId ? { ...m, isStreaming: false } : m))
          );
        }
        if (errorType === 'InsufficientCreditsError') {
          setError("You're out of credits for this billing period. Upgrade your plan to keep chatting.");
        } else {
          setError('Something went wrong sending that message. Please try again.');
        }
      },
    });
  };

  const canSend = !!input.trim() && !isSending;

  return (
    <KeyboardAvoidingView
      style={{ flex: 1, backgroundColor: colors.pageBg }}
      // 'padding' on Android too: since Android 15 apps are edge-to-edge and
      // the window no longer resizes for the keyboard, so without this the
      // input and Send button sat hidden behind it. On older Android, where
      // the window still resizes, KeyboardAvoidingView finds no overlap and
      // adds nothing.
      behavior="padding"
      keyboardVerticalOffset={0}
    >
      <View
        style={{
          flexDirection: 'row',
          alignItems: 'center',
          paddingTop: 60,
          paddingHorizontal: 20,
          paddingBottom: 14,
        }}
      >
        <Pressable onPress={() => router.back()} style={{ marginRight: 12 }}>
          <Text style={{ fontSize: 16, color: colors.textSecondary }}>‹</Text>
        </Pressable>
        {/* Green gradient ring behind the avatar, per brand spec */}
        <LinearGradient
          colors={[colors.gradientPrimaryStart, colors.gradientPrimaryEnd]}
          style={{
            width: 46,
            height: 46,
            borderRadius: 23,
            alignItems: 'center',
            justifyContent: 'center',
            marginRight: 12,
          }}
        >
          <Image
            source={require('../../../assets/images/avatar-female.png')}
            style={{ width: 40, height: 40, borderRadius: 20 }}
          />
        </LinearGradient>
        <View style={{ flex: 1 }}>
          <Text style={{ fontSize: 17, fontWeight: '600', color: colors.textPrimary }}>
            Nutrition Coach 💬
          </Text>
          <Text style={{ fontSize: 11, color: colors.textSecondary }}>
            Always here to help you eat better ✨
          </Text>
        </View>
        {messages.length > 0 ? (
          <Pressable
            onPress={startNewConversation}
            style={{
              paddingVertical: 6,
              paddingHorizontal: 10,
              borderRadius: 14,
              backgroundColor: colors.surfaceAlt,
            }}
          >
            <Text style={{ fontSize: 11, fontWeight: '600', color: colors.textSecondary }}>
              New chat
            </Text>
          </Pressable>
        ) : null}
      </View>

      <ScrollView
        ref={scrollRef}
        style={{ flex: 1 }}
        contentContainerStyle={{ paddingHorizontal: 20, paddingBottom: 12 }}
      >
        {messages.length === 0 ? (
          <View>
            <View
              style={{
                backgroundColor: colors.aiBubbleBg,
                borderRadius: 18,
                borderBottomLeftRadius: 4,
                paddingHorizontal: 14,
                paddingVertical: 12,
                marginBottom: 12,
                alignSelf: 'flex-start',
                maxWidth: '85%',
              }}
            >
              <Text style={{ fontSize: 13, lineHeight: 19, color: colors.aiBubbleText }}>
                Hey there 👋{'\n'}How are you feeling today?
              </Text>
            </View>
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 20 }}>
              {[
                { label: '😊 Great', prompt: "I'm feeling great today!" },
                { label: '😴 Tired', prompt: "I'm feeling a bit tired today." },
                { label: '🤒 Not well', prompt: "I'm not feeling well today." },
                { label: '💪 Ready to train', prompt: "I'm ready to train today — any nutrition tips?" },
              ].map((mood) => (
                <Pressable
                  key={mood.label}
                  onPress={() => handleSend(mood.prompt)}
                  style={{
                    backgroundColor: colors.suggestedChipBg,
                    paddingHorizontal: 12,
                    paddingVertical: 8,
                    borderRadius: RADIUS.chip,
                  }}
                >
                  <Text style={{ fontSize: 12, fontWeight: '600', color: colors.suggestedChipText }}>
                    {mood.label}
                  </Text>
                </Pressable>
              ))}
            </View>
            <Text style={{ fontSize: 12, color: colors.textSecondary, textAlign: 'center' }}>
              Or just type below — I'll stick to food and nutrition topics, but I'm happy to help
              however I can.
            </Text>
          </View>
        ) : (
          messages.map((msg) => {
            const isUser = msg.role === 'user';
            return (
              <View
                key={msg.id}
                style={{
                  alignSelf: isUser ? 'flex-end' : 'flex-start',
                  maxWidth: '82%',
                  marginBottom: 12,
                }}
              >
                <View
                  style={{
                    backgroundColor: isUser ? colors.userBubbleBg : colors.aiBubbleBg,
                    borderWidth: isUser ? 1 : 0,
                    borderColor: colors.border,
                    borderRadius: 18,
                    borderBottomRightRadius: isUser ? 4 : 18,
                    borderBottomLeftRadius: isUser ? 18 : 4,
                    paddingHorizontal: 13,
                    paddingVertical: 10,
                    // Soft shadow on the user's own bubble so a white
                    // bubble on a near-white background still reads as
                    // elevated, not invisible.
                    shadowColor: '#000',
                    shadowOffset: { width: 0, height: isUser ? 2 : 0 },
                    shadowOpacity: isUser ? 0.06 : 0,
                    shadowRadius: isUser ? 6 : 0,
                    elevation: isUser ? 1 : 0,
                  }}
                >
                  {msg.role === 'assistant' ? (
                    msg.text ? (
                      <MarkdownText text={msg.text} color={colors.aiBubbleText} accentColor={colors.primaryDark} />
                    ) : (
                      <Text style={{ fontSize: 13, color: colors.aiBubbleText }}>
                        {msg.isStreaming ? '…' : ''}
                      </Text>
                    )
                  ) : (
                    <Text style={{ fontSize: 13, lineHeight: 19, color: colors.userBubbleText }}>
                      {msg.text}
                    </Text>
                  )}
                </View>
                <Text
                  style={{
                    fontSize: 10,
                    color: colors.textMuted,
                    marginTop: 3,
                    alignSelf: isUser ? 'flex-end' : 'flex-start',
                  }}
                >
                  {msg.timestamp}
                </Text>
              </View>
            );
          })
        )}

        {upsellMessage ? (
          <ThemedCard
            padding={12}
            style={{ backgroundColor: colors.warningBg, borderColor: 'transparent', borderRadius: 12, marginTop: 8, marginBottom: 8 }}
          >
            <Text style={{ color: colors.warningText, fontSize: 12 }}>{upsellMessage}</Text>
          </ThemedCard>
        ) : null}

        {error ? (
          <ThemedCard
            padding={12}
            style={{ backgroundColor: colors.dangerBg, borderColor: 'transparent', borderRadius: 12, marginTop: 8, marginBottom: 8 }}
          >
            <Text style={{ color: colors.danger, fontSize: 12 }}>{error}</Text>
          </ThemedCard>
        ) : null}
      </ScrollView>

      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={{ maxHeight: 46, flexGrow: 0 }}
        contentContainerStyle={{
          paddingHorizontal: 20,
          paddingTop: 6,
          paddingBottom: 10,
          gap: 8,
          alignItems: 'center',
        }}
      >
        {QUICK_ACTIONS.map((action) => (
          <Pressable
            key={action.label}
            onPress={() => handleSend(action.prompt)}
            disabled={isSending}
            style={{
              backgroundColor: colors.suggestedChipBg,
              paddingHorizontal: 12,
              paddingVertical: 7,
              borderRadius: RADIUS.chip,
              opacity: isSending ? 0.5 : 1,
            }}
          >
            <Text style={{ fontSize: 12, fontWeight: '600', color: colors.suggestedChipText }}>
              {action.label}
            </Text>
          </Pressable>
        ))}
      </ScrollView>

      <View
        style={{
          flexDirection: 'row',
          alignItems: 'flex-end',
          paddingHorizontal: 20,
          paddingVertical: 12,
          borderTopWidth: 1,
          borderTopColor: colors.border,
          gap: 8,
        }}
      >
        <TextInput
          placeholder="Ask anything about food or nutrition..."
          placeholderTextColor={colors.textMuted}
          value={input}
          onChangeText={setInput}
          multiline
          editable={!isSending}
          style={{
            flex: 1,
            borderWidth: 1,
            borderColor: colors.border,
            borderRadius: 20,
            paddingHorizontal: 14,
            paddingVertical: 10,
            fontSize: 13,
            color: colors.textPrimary,
            backgroundColor: colors.cardBg,
            maxHeight: 100,
          }}
        />
        {canSend ? (
          <Pressable onPress={() => handleSend()}>
            <LinearGradient
              colors={[colors.gradientPrimaryStart, colors.gradientPrimaryEnd]}
              style={{
                width: 40,
                height: 40,
                borderRadius: 20,
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Text style={{ color: '#fff', fontSize: 16 }}>➤</Text>
            </LinearGradient>
          </Pressable>
        ) : (
          <View
            style={{
              width: 40,
              height: 40,
              borderRadius: 20,
              backgroundColor: colors.border,
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Text style={{ color: '#fff', fontSize: 16 }}>➤</Text>
          </View>
        )}
      </View>

      <ModuleNavBar currentKey="coach" />
    </KeyboardAvoidingView>
  );
}

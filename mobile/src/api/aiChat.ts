import { streamSSE } from './sse';

interface SendChatMessageHandlers {
  onChunk?: (text: string) => void;
  onUpsell?: (message: string) => void;
  onSession?: (sessionId: string) => void;
  onError?: (errorType: string, detail: string) => void;
}

/**
 * Streams a chat message to the Nutrition Coach. Returns an abort function.
 *
 * Unlike the stage-based AI features, this streams the actual reply TEXT
 * chunk-by-chunk in real time (genuine live streaming, not a simulated
 * reveal) — so onChunk should be appended to a live-updating message
 * bubble as each piece arrives.
 *
 * The "session" event always arrives last, REGARDLESS of whether the
 * message succeeded or errored (see the backend route's docstring) — it's
 * not a success indicator by itself. Capture the session_id from it for
 * subsequent messages either way; only treat the reply as actually
 * complete if no error event arrived before it.
 */
export function sendChatMessage(
  message: string,
  sessionId: string | null,
  handlers: SendChatMessageHandlers
): () => void {
  return streamSSE(
    '/api/v1/ai/chat',
    {
      message,
      ...(sessionId ? { session_id: sessionId } : {}),
    },
    {
      onChunk: handlers.onChunk,
      onUpsell: handlers.onUpsell,
      onSession: handlers.onSession,
      onError: (errorType, detail) => handlers.onError?.(errorType, detail),
    }
  );
}
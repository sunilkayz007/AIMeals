import { useAuthStore } from '../stores/authStore';
import { apiClient } from './client';

// React Native's fetch does not reliably support streaming response
// bodies across versions/platforms. XMLHttpRequest's onprogress firing
// with the growing responseText is the standard, reliable technique for
// SSE in React Native — used here instead of fetch + ReadableStream.

export interface SSEHandlers {
  // detail is an optional, short live-progress string for a single
  // long-running stage (e.g. stage="analyzing_report",
  // detail="Extracted Vitamin D") — see backend
  // app/core/sse_streaming.py's Aug 2026 update. Existing handlers
  // that only destructure the first argument are unaffected.
  onStage?: (stage: string, detail?: string) => void;
  onResult?: (data: any) => void;
  onError?: (errorType: string, detail: string, data?: any) => void;
  onChunk?: (text: string) => void;
  onUpsell?: (message: string) => void;
  onSession?: (sessionId: string) => void;
  onDone?: () => void;
}

function parseSSEBlock(block: string): { event: string; data: any } | null {
  let event = '';
  let dataStr = '';
  for (const line of block.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim();
    else if (line.startsWith('data:')) dataStr += line.slice(5).trim();
  }
  if (!event) return null;
  try {
    return { event, data: dataStr ? JSON.parse(dataStr) : {} };
  } catch {
    return null;
  }
}

function dispatchSSEEvent(handlers: SSEHandlers, event: string, data: any) {
  switch (event) {
    case 'stage':
      handlers.onStage?.(data.stage, data.detail);
      break;
    case 'result':
      handlers.onResult?.(data);
      break;
    case 'error':
      handlers.onError?.(data.error_type, data.detail, data);
      break;
    case 'chunk':
      handlers.onChunk?.(data.text);
      break;
    case 'upsell':
      handlers.onUpsell?.(data.message);
      break;
    case 'session':
      handlers.onSession?.(data.session_id);
      break;
    case 'done':
      handlers.onDone?.();
      break;
  }
}

/**
 * Opens a POST-based SSE stream against the backend. Returns an abort
 * function to cancel the request (e.g. if the user navigates away).
 *
 * Known limitation: unlike apiClient, this does NOT auto-refresh an
 * expired access token — the access token is read once at request start.
 * Acceptable for now (tokens are typically valid well past a single
 * recipe generation call); revisit if this becomes a real issue.
 */
export function streamSSE(path: string, body: unknown, handlers: SSEHandlers): () => void {
  const xhr = new XMLHttpRequest();
  let processedLength = 0;
  const token = useAuthStore.getState().tokens?.access_token;

  xhr.open('POST', `${apiClient.baseUrl}${path}`);
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.setRequestHeader('Accept', 'text/event-stream');
  if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`);

  const processNewData = () => {
    const fullText = xhr.responseText;
    const lastBoundary = fullText.lastIndexOf('\n\n');
    // Only consume up to the last complete "\n\n"-terminated block, so a
    // block split across two onprogress firings isn't parsed prematurely.
    if (lastBoundary === -1 || lastBoundary < processedLength) return;
    const chunkToProcess = fullText.slice(processedLength, lastBoundary);
    processedLength = lastBoundary + 2;
    for (const block of chunkToProcess.split('\n\n')) {
      if (!block.trim()) continue;
      const parsed = parseSSEBlock(block);
      if (parsed) dispatchSSEEvent(handlers, parsed.event, parsed.data);
    }
  };

  xhr.onprogress = processNewData;
  xhr.onload = () => {
    processNewData(); // catch any trailing block that didn't trigger another onprogress
    if (xhr.status < 200 || xhr.status >= 300) {
      handlers.onError?.('HTTPError', `Request failed with status ${xhr.status}`);
    }
  };
  xhr.onerror = () => {
    handlers.onError?.('NetworkError', 'Connection failed.');
  };

  xhr.send(JSON.stringify(body));
  return () => xhr.abort();
}

/**
 * Same SSE mechanics as streamSSE, but sends a real file upload
 * (multipart/form-data) instead of a JSON body. Generalized (Aug 2026)
 * from the original food-image-only streamSSEWithImage to accept ANY
 * form field name, so it can back both /ai/food-image/analyze (field
 * "image") and /health-reports/analyze (field "report") — see
 * streamSSEWithImage below, now a thin wrapper over this.
 *
 * Deliberately does NOT set a Content-Type header: FormData needs the
 * multipart boundary that XHR/React Native sets automatically when
 * sending a FormData body, and setting Content-Type manually would omit
 * that boundary and silently break the upload.
 */
export function streamSSEWithFile(
  path: string,
  fileUri: string,
  fieldName: string,
  handlers: SSEHandlers,
  fileName: string,
  mimeType: string
): () => void {
  const xhr = new XMLHttpRequest();
  let processedLength = 0;
  const token = useAuthStore.getState().tokens?.access_token;

  xhr.open('POST', `${apiClient.baseUrl}${path}`);
  xhr.setRequestHeader('Accept', 'text/event-stream');
  if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`);

  const processNewData = () => {
    const fullText = xhr.responseText;
    const lastBoundary = fullText.lastIndexOf('\n\n');
    if (lastBoundary === -1 || lastBoundary < processedLength) return;
    const chunkToProcess = fullText.slice(processedLength, lastBoundary);
    processedLength = lastBoundary + 2;
    for (const block of chunkToProcess.split('\n\n')) {
      if (!block.trim()) continue;
      const parsed = parseSSEBlock(block);
      if (parsed) dispatchSSEEvent(handlers, parsed.event, parsed.data);
    }
  };

  xhr.onprogress = processNewData;
  xhr.onload = () => {
    processNewData();
    if (xhr.status < 200 || xhr.status >= 300) {
      handlers.onError?.('HTTPError', `Request failed with status ${xhr.status}`);
    }
  };
  xhr.onerror = () => {
    handlers.onError?.('NetworkError', 'Connection failed.');
  };

  try {
    // Validate file URI before attempting upload
    if (!fileUri || typeof fileUri !== 'string' || fileUri.trim() === '') {
      throw new Error('Invalid or empty file URI provided');
    }

    const formData = new FormData();
    // React Native's FormData accepts this {uri, name, type} shape for
    // file fields — not a real Blob, but RN's networking layer knows to
    // treat it as one. fieldName must match the backend's UploadFile
    // parameter name exactly (e.g. "image" or "report").
    formData.append(fieldName, {
      uri: fileUri,
      name: fileName,
      type: mimeType,
    } as any);

    xhr.send(formData as any);
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : 'File upload failed';
    console.error('[SSE] File upload error:', errorMsg, { fileUri, fileName, mimeType });

    // Notify handler of the error with type and detail
    handlers.onError?.('FileUploadError', errorMsg);

    // Re-throw so caller can implement additional error handling if needed
    throw error;
  }

  return () => xhr.abort();
}

/**
 * Food-image-specific wrapper over streamSSEWithFile, preserved with
 * its original signature/defaults so no existing call site needs to
 * change.
 */
export function streamSSEWithImage(
  path: string,
  imageUri: string,
  handlers: SSEHandlers,
  fileName: string = 'photo.jpg',
  mimeType: string = 'image/jpeg'
): () => void {
  return streamSSEWithFile(path, imageUri, 'image', handlers, fileName, mimeType);
}
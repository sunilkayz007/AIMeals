"""
=========================================================
AIMeals Backend
SSE Streaming Helper

Responsibilities:
    - Run a synchronous AIService method in a worker thread
      while streaming its progress as Server-Sent Events
    - Provide ONE shared implementation of this pattern, used
      by every AI route (Chat, Recipe Generation, Meal Plan
      Generation, Pantry Chef, Ingredient Scan flow, Food
      Image Analysis, Health Report Analysis) — not
      reimplemented six times

Why this exists:
    Every AIService method is a synchronous, multi-step
    blocking call (credit check -> Claude call -> parse ->
    safety checks -> save). FastAPI's event loop is async.
    This helper bridges the two: it runs the blocking method
    in a worker thread via to_thread.run_sync, while an
    async generator polls a thread-safe queue.Queue for
    progress markers pushed by the method's on_progress
    callback, yielding each one as an SSE "stage" event. Once
    the worker thread finishes, it yields a final "result" or
    "error" event.

Notes:
    - The polling loop uses queue.get_nowait() + a short
      asyncio.sleep(), not a blocking queue.get() — a blocking
      call would stall the event loop, defeating the purpose
      of doing this asynchronously at all.
    - serialize_result is REQUIRED, not optional with a naive
      default — an AIService method's return value (a Recipe,
      MealPlan, FoodImage, IngredientScan, or HealthReport ORM
      object) is never directly JSON-serializable, and
      guessing a "reasonable" default serialization would
      silently hide bugs (e.g. leaking SQLAlchemy internals
      into an API response) rather than surfacing them at the
      call site where the correct shape is actually known.
    - Exceptions raised by the blocking call are caught and
      surfaced as an "error" SSE event with the exception's
      class name (e.g. "InsufficientCreditsError",
      "AllergenDetectedError") so the client can distinguish
      error types without parsing message text. The route
      layer does NOT need its own try/except around the
      blocking call — this helper already isolates it.
    - UPDATED: if the raised exception has an `sse_extra_data`
      attribute/property returning a dict, those fields are
      merged into the error event's data payload alongside
      error_type/detail. This is deliberately generic —
      sse_streaming.py knows nothing about recipes or
      allergens specifically; it just forwards whatever a
      given exception class chooses to expose. See
      AllergenDetectedError in core/exceptions.py for the
      first real use of this (attaching recipe_preview and
      flagged_allergens for the fail-open-with-confirmation
      flow). Any future exception type can opt into this same
      mechanism without touching this file again.
    - UPDATED (Aug 2026, Health Insights live-detail feature):
      on_progress now optionally accepts a second argument,
      `detail` — a short human-readable string describing
      what's happening RIGHT NOW within a single long-running
      stage (e.g. stage="analyzing_report",
      detail="Extracted Vitamin D"). This is purely additive
      and fully backward-compatible: every existing call site
      still calls on_progress("some_stage") with one argument,
      which continues to work identically (detail defaults to
      None and is simply omitted from the emitted SSE data in
      that case — see the "stage" branch below). Only
      AIService.analyze_health_report() currently uses the
      detail parameter; any other AIService method can opt
      into it later with zero changes needed here.

Example usage:
    from app.core.sse_streaming import stream_ai_progress

    @router.post("/chat")
    async def chat(payload: ChatRequest, current_user=Depends(get_current_user), db=Depends(get_db)):
        service = AIService(db)
        return StreamingResponse(
            stream_ai_progress(
                service.send_chat_message,
                serialize_result=lambda reply: {"reply": reply, "session_id": str(session_id)},
                user_id=current_user.id,
                user_message=payload.message,
                session_id=session_id,
            ),
            media_type="text/event-stream",
        )
=========================================================
"""

import asyncio
import json
import queue
from typing import Any, Callable, Optional

import anyio
from anyio import to_thread


# =========================================================
# SSE Formatting Helper
# =========================================================

def _format_sse(event: str, data: dict) -> str:
    """
    Formats a single Server-Sent Event. The blank line at the
    end is required by the SSE spec to terminate the event.
    """
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


# =========================================================
# Core Streaming Generator
# =========================================================

async def stream_ai_progress(
    blocking_fn: Callable[..., Any],
    *,
    serialize_result: Callable[[Any], dict],
    **kwargs: Any,
):
    """
    Runs blocking_fn(**kwargs, on_progress=...) in a worker
    thread, yielding SSE events as it progresses:

        event: stage   data: {"stage": "checking_credits"}
        event: stage   data: {"stage": "generating"}
        event: stage   data: {"stage": "saving"}
        event: result  data: {...serialize_result(return_value)}

    A stage event MAY also include a "detail" field — see the
    module docstring's note on the live-detail feature:

        event: stage   data: {"stage": "analyzing_report", "detail": "Extracted Vitamin D"}

    On failure, yields a single error event instead of a
    result event:

        event: error   data: {"error_type": "InsufficientCreditsError", "detail": "..."}

    If the raised exception exposes an `sse_extra_data`
    attribute/property (a dict), those fields are merged into
    the error event's data too — see the module docstring.

    blocking_fn MUST accept an on_progress keyword argument
    (every AIService method that supports streaming does —
    see send_chat_message() for the pattern). This helper
    injects that callback itself; callers should NOT pass
    their own on_progress in kwargs. The injected callback
    accepts on_progress(stage, detail=None) — existing callers
    passing only a stage continue to work unchanged.
    """
    progress_queue: "queue.Queue[tuple[str, Any]]" = queue.Queue()

    def on_progress(stage: str, detail: Optional[str] = None) -> None:
        progress_queue.put(("stage", (stage, detail)))

    kwargs["on_progress"] = on_progress

    result_holder: dict = {}

    def run() -> None:
        try:
            result_holder["result"] = blocking_fn(**kwargs)
        except Exception as e:  # noqa: BLE001 — intentionally broad, re-surfaced as an SSE error event below
            result_holder["error"] = e
        finally:
            progress_queue.put(("done", None))

    async with anyio.create_task_group() as tg:
        tg.start_soon(to_thread.run_sync, run)

        while True:
            try:
                kind, value = progress_queue.get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.05)
                continue

            if kind == "stage":
                stage_name, detail = value
                data: dict = {"stage": stage_name}
                if detail:
                    data["detail"] = detail
                yield _format_sse("stage", data)
            elif kind == "done":
                break

    if "error" in result_holder:
        error = result_holder["error"]
        error_data = {
            "error_type": type(error).__name__,
            "detail": str(error),
        }
        extra = getattr(error, "sse_extra_data", None)
        if isinstance(extra, dict):
            error_data.update(extra)
        yield _format_sse("error", error_data)
    else:
        yield _format_sse("result", serialize_result(result_holder.get("result")))


# =========================================================
# Text-Chunk Streaming Generator (ChatGPT-style typing)
# =========================================================

async def stream_ai_text(generator_fn: Callable[..., Any], **kwargs: Any):
    """
    Runs a SYNCHRONOUS generator function (one that yields
    text chunks, e.g. AIService.send_chat_message_stream) in
    a worker thread, forwarding each yielded chunk as an SSE
    "chunk" event in real time as it's produced — the
    ChatGPT-style token-by-token "typing" pattern.

    Distinct from stream_ai_progress() above: that helper
    streams a handful of discrete named STAGES for a single
    blocking call with one final result; this streams many
    small pieces of the actual response TEXT as Claude
    generates them, with no separate "result" event at all —
    the concatenation of all "chunk" events IS the full reply.

    Events:
        event: chunk    data: {"text": "..."}    (one per chunk, many per call)
        event: upsell   data: {"message": "..."}  (optional — see note below)
        event: done     data: {}                   (stream finished successfully)
        event: error    data: {"error_type": ..., "detail": ...}

    generator_fn may yield either plain strings (rendered as
    "chunk" events) OR a dict shaped like
    {"__event__": "upsell", "message": "..."} to signal a
    distinct, non-text event — used by
    AIService.send_chat_message_stream() to attach an upgrade
    nudge after a one-time "grace" message, kept as its own
    event rather than mixed into the assistant's reply text so
    the client can render it as a separate banner.

    Note: if the underlying call fails partway through (e.g.
    a ClaudeAPIError mid-stream), any chunks already yielded
    have ALREADY been sent to the client — there is no way to
    "unsend" partial text once it's been streamed out. The
    credit is still correctly refunded server-side regardless
    (see AIService.send_chat_message_stream()'s docstring).
    """
    chunk_queue: "queue.Queue[tuple[str, Any]]" = queue.Queue()

    def run() -> None:
        try:
            for chunk in generator_fn(**kwargs):
                if isinstance(chunk, dict) and chunk.get("__event__") == "upsell":
                    chunk_queue.put(("upsell", chunk.get("message", "")))
                else:
                    chunk_queue.put(("chunk", chunk))
        except Exception as e:  # noqa: BLE001 — re-surfaced as an SSE error event below
            chunk_queue.put(("error", e))
        finally:
            chunk_queue.put(("done", None))

    async with anyio.create_task_group() as tg:
        tg.start_soon(to_thread.run_sync, run)

        while True:
            try:
                kind, value = chunk_queue.get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.02)
                continue

            if kind == "chunk":
                yield _format_sse("chunk", {"text": value})
            elif kind == "upsell":
                yield _format_sse("upsell", {"message": value})
            elif kind == "error":
                yield _format_sse(
                    "error",
                    {"error_type": type(value).__name__, "detail": str(value)},
                )
                break
            elif kind == "done":
                yield _format_sse("done", {})
                break
"""
=========================================================
AIMeals Backend
AI Chat API Route

Endpoint:
    POST /api/v1/ai/chat   - send a message to the Nutrition Coach, streamed word-by-word via SSE

Requires a valid access token (Authorization: Bearer <token>).

Response format (text/event-stream):
    event: chunk   data: {"text": "Great"}
    event: chunk   data: {"text": " question"}
    event: chunk   data: {"text": "!"}
    ... many more chunk events, arriving in real time as Claude generates them ...
    event: session data: {"session_id": "..."}

    On failure, a single error event is sent instead (may
    arrive AFTER some chunk events already streamed - see
    note below):
    event: error   data: {"error_type": "InsufficientCreditsError", "detail": "..."}

Notes:
    - This streams the actual reply TEXT chunk-by-chunk, the
      ChatGPT "typing" effect - different from the
      stage-progress pattern (checking_credits/generating/
      saving) used for the other five AI features, which have
      no long prose response to stream tokens from (a JSON
      recipe object isn't something you'd want to watch
      assemble character-by-character).
    - session_id resolution happens HERE, in the route, same
      reasoning as before: the service generates its own
      session_id internally when None is passed but has no
      return value to hand it back through (a generator
      can't "return and yield" cleanly), so the route resolves
      it before calling the service and includes it in a
      trailing "session" event.
    - If the Claude call fails partway through a stream, any
      chunks already sent to the client are already sent -
      there's no undo. The client should treat the "session"
      event as the ONLY confirmation a reply is complete and
      safe to finalize/save; an "error" event (even after some
      chunks) means the reply may be incomplete.

Dependencies:
    - app.core.sse_streaming.stream_ai_text
    - app.services.ai_service.AIService
    - app.core.dependencies.get_current_user
=========================================================
"""

import json
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.B_database import get_db
from app.core.dependencies import get_current_user
from app.core.sse_streaming import stream_ai_text
from app.models.user import User
from app.schemas.ai_chat import ChatRequest
from app.services.ai_service import AIService

router = APIRouter(prefix="/api/v1/ai", tags=["AI"])


# =========================================================
# Chat (Nutrition Coach) - Real-Time Token Streaming
# =========================================================

@router.post("/chat")
async def chat(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """
    Sends a message to the Nutrition Coach. Streams the reply
    word-by-word as Claude generates it (ChatGPT-style), then
    a final "session" event containing the session_id to reuse
    for follow-up messages.
    """
    service = AIService(db)

    session_id = payload.session_id if payload.session_id is not None else uuid.uuid4()

    async def event_stream():
        async for event in stream_ai_text(
            service.send_chat_message_stream,
            user_id=current_user.id,
            user_message=payload.message,
            session_id=session_id,
        ):
            yield event

        yield f"event: session\ndata: {json.dumps({'session_id': str(session_id)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
"""
=========================================================
AIMeals Backend
AI Chat Schemas

Responsibilities:
    - Define the request shape for the streaming chat endpoint

Notes:
    - No response schema — SSE responses aren't a single JSON
      body, they're a stream of "event: ...\\ndata: ..." lines
      (see app.core.sse_streaming). The actual final payload
      shape sent in the "result" event is documented in
      api/v1/ai_chat.py's route docstring instead.

Example usage:
    from app.schemas.ai_chat import ChatRequest

    def chat(payload: ChatRequest):
        ...
=========================================================
"""

import uuid
from typing import Optional

from pydantic import BaseModel, field_validator


# =========================================================
# Request Schema — Chat Message
# =========================================================

class ChatRequest(BaseModel):
    """
    Shape of the payload accepted by POST /ai/chat.

    session_id is optional — omit it to start a new
    conversation (the server generates one and returns it in
    the "result" event's session_id field); include it on
    subsequent messages in the same thread to maintain context.
    """

    message: str
    session_id: Optional[uuid.UUID] = None

    @field_validator("message")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("message cannot be blank.")
        return value.strip()
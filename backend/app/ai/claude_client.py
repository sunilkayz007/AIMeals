"""
=========================================================
AIMeals Backend
Claude Client

Responsibilities:
    - Wrap the raw Anthropic SDK client
    - Provide send_message() (non-streaming) and
      send_message_stream() (streaming, yields text chunks
      as they arrive) — used by every AI feature in the app
    - Safely extract text from a non-streaming response,
      filtering out ThinkingBlocks and any other non-text
      content

Dependencies:
    - anthropic (pip package)
    - app.A_config.settings (CLAUDE_API_KEY)
    - app.C_logger.app_logger

Notes:
    - This module is intentionally "dumb" — it knows nothing
      about credits, users, or business logic. It only knows
      how to talk to the Claude API. All business logic
      (credit checks, model selection, logging interactions)
      belongs in app/services/ai_service.py, which sits on
      top of this client.
    - extract_text() follows the same pattern used in the
      author's other Claude-integrated projects: filter
      response.content by block.type == "text" to handle
      ThinkingBlock safely, since iterating content blindly
      can include non-text blocks that break naive
      concatenation.
    - send_message_stream() stores final usage stats on
      self.last_stream_usage after the stream completes,
      since a generator can't both yield values AND return a
      final value cleanly. This is safe in this codebase's
      usage pattern specifically because a new ClaudeClient
      instance is created fresh per AIService(db) instance,
      which is itself created fresh per request (via
      Depends()) — there is no cross-request instance sharing
      that could cause one request's usage stats to leak into
      another's. This would NOT be safe if ClaudeClient were
      ever turned into an app-wide singleton.

Example usage:
    from app.ai.claude_client import ClaudeClient

    client = ClaudeClient()

    # Non-streaming:
    response = client.send_message(
        model="claude-sonnet-5",
        system_prompt="You are a helpful nutrition coach.",
        messages=[{"role": "user", "content": "What should I eat?"}],
    )
    reply_text = client.extract_text(response)

    # Streaming:
    for chunk in client.send_message_stream(
        model="claude-sonnet-5",
        system_prompt="You are a helpful nutrition coach.",
        messages=[{"role": "user", "content": "What should I eat?"}],
    ):
        print(chunk, end="", flush=True)
    print(client.last_stream_usage)  # {"input_tokens": ..., "output_tokens": ...}
=========================================================
"""

from typing import Any, Iterator, Optional

import anthropic

from app.A_config import settings
from app.C_logger import app_logger
from app.core.exceptions import ClaudeAPIError


# =========================================================
# Claude Client
# =========================================================

class ClaudeClient:
    """
    Thin wrapper around the Anthropic SDK client.
    """

    def __init__(self):
        self._client = anthropic.Anthropic(api_key=settings.CLAUDE_API_KEY)
        self.last_stream_usage: Optional[dict[str, int]] = None

    # ---------------------------------------------------
    # Send Message (Non-Streaming)
    # ---------------------------------------------------

    def send_message(
        self,
        model: str,
        messages: list[dict[str, Any]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        enable_caching: bool = True,
    ) -> Any:
        """
        Sends a message to the Claude API and returns the
        raw response object.

        Args:
            model: Model string, e.g. "claude-sonnet-5".
            messages: List of {"role": ..., "content": ...} dicts.
            system_prompt: Optional system prompt.
            max_tokens: Max tokens in the response.
            enable_caching: Adds the top-level cache_control
                field Anthropic's automatic prompt caching
                uses (see platform.claude.com prompt-caching
                docs). Defaults to True — every AI feature in
                this app sends a large, static system prompt
                reused across many different users' requests,
                which is exactly what caching is for. Caching
                is scoped to the organization's API key, not
                per-user or per-conversation, so this benefits
                the whole app's traffic sharing the same
                prompt text within the cache TTL window, not
                just repeat calls from a single user. Safe to
                leave on unconditionally; there's no real
                downside for a fully static/repeated prompt,
                only for genuinely one-off text that will
                never repeat, which doesn't describe any
                current AIMeals feature.

        Raises:
            ClaudeAPIError: on any failure — network error,
                rate limit, authentication failure, API
                outage, etc. The caller (app_service layer)
                is expected to handle this, including
                refunding any AI credit already consumed for
                this call.
        """
        try:
            kwargs: dict[str, Any] = {
                "model": model,
                "max_tokens": max_tokens,
                "messages": messages,
            }
            if system_prompt is not None:
                kwargs["system"] = system_prompt
            if enable_caching:
                kwargs["cache_control"] = {"type": "ephemeral"}

            response = self._client.messages.create(**kwargs)

            usage = response.usage
            app_logger.info(
                f"Claude usage — input: {usage.input_tokens}, "
                f"output: {usage.output_tokens}, "
                f"cache_creation: {getattr(usage, 'cache_creation_input_tokens', 0)}, "
                f"cache_read: {getattr(usage, 'cache_read_input_tokens', 0)}"
            )

            return response

        except anthropic.APIError as e:
            app_logger.exception(f"Claude API call failed: {e}")
            raise ClaudeAPIError(
                "The AI request failed. Please try again."
            ) from e

    # ---------------------------------------------------
    # Send Message (Streaming)
    # ---------------------------------------------------

    def send_message_stream(
        self,
        model: str,
        messages: list[dict[str, Any]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        enable_caching: bool = True,
    ) -> Iterator[str]:
        """
        Sends a message to the Claude API and yields the reply
        as a series of text chunks, in real time, as Claude
        generates them — the ChatGPT-style "typing" pattern.

        enable_caching: see send_message()'s docstring — same
        reasoning applies here, defaulted on.

        After the generator is fully exhausted,
        self.last_stream_usage is set to
        {"input_tokens": int, "output_tokens": int} — read it
        AFTER the for-loop completes, not during.

        Raises:
            ClaudeAPIError: on any failure. If this happens
                partway through streaming, any chunks already
                yielded have already been sent to the caller —
                there is no way to "unsend" them. Callers
                should still refund the credit regardless
                (the API cost was incurred either way at the
                point Anthropic started generating).
        """
        try:
            kwargs: dict[str, Any] = {
                "model": model,
                "max_tokens": max_tokens,
                "messages": messages,
            }
            if system_prompt is not None:
                kwargs["system"] = system_prompt
            if enable_caching:
                kwargs["cache_control"] = {"type": "ephemeral"}

            with self._client.messages.stream(**kwargs) as stream:
                for text in stream.text_stream:
                    yield text

                final_message = stream.get_final_message()
                self.last_stream_usage = {
                    "input_tokens": final_message.usage.input_tokens,
                    "output_tokens": final_message.usage.output_tokens,
                }
                app_logger.info(
                    f"Claude usage (stream) — input: {final_message.usage.input_tokens}, "
                    f"output: {final_message.usage.output_tokens}, "
                    f"cache_creation: {getattr(final_message.usage, 'cache_creation_input_tokens', 0)}, "
                    f"cache_read: {getattr(final_message.usage, 'cache_read_input_tokens', 0)}"
                )

        except anthropic.APIError as e:
            app_logger.exception(f"Claude streaming API call failed: {e}")
            raise ClaudeAPIError(
                "The AI request failed. Please try again."
            ) from e

    # ---------------------------------------------------
    # Extract Text (Non-Streaming Responses Only)
    # ---------------------------------------------------

    def extract_text(self, response: Any) -> str:
        """
        Safely extracts the text content from a non-streaming
        Claude API response, filtering response.content by
        block.type == "text" to skip ThinkingBlocks or any
        other non-text content types.

        Returns an empty string (not None) if no text blocks
        are found, so callers can always safely use the
        result as a string.

        Not used for streaming responses — send_message_stream()
        already yields plain text chunks directly.
        """
        text_blocks = [
            block.text for block in response.content if block.type == "text"
        ]
        return "".join(text_blocks)
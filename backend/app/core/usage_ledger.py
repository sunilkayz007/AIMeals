"""
=========================================================
AIMeals Backend
Usage Ledger

Responsibilities:
    - Maintain a live-updating JSON file tracking, per user,
      per MODEL (e.g. claude-haiku-4-5 vs claude-sonnet-5),
      AND in aggregate: total input tokens, total output
      tokens, and estimated dollar cost of every Claude API
      call the app makes
    - Update incrementally, in real time, every time any AI
      feature successfully logs an interaction — NOT
      recomputed from the database on demand (that's what
      scripts/user_usage_report.py is for, if you ever want a
      from-scratch recount instead of trusting the running total)

Dependencies:
    - none beyond the standard library — deliberately kept
      simple and dependency-free since it runs on the hot
      path of every single AI call

Notes:
    - MANUALLY MAINTAINED pricing table below, same caveat as
      scripts/user_usage_report.py: verify against Anthropic's
      current published pricing before trusting these dollar
      figures for real business decisions.
    - Writes are ATOMIC (write to a .tmp file, then swap it
      into place) so a crash mid-write can't leave a
      half-written, corrupted JSON file behind.
    - Guarded by a module-level threading.Lock — FastAPI's
      sync route handlers can run concurrently across worker
      threads, so a naive read-modify-write here would risk
      losing updates under real concurrent traffic.
    - If the file is missing or unreadable/corrupted, starts
      fresh rather than crashing the whole app over a broken
      tracking file — usage tracking failing should never take
      down an actual user-facing AI feature.
    - Default path is app/data/usage_ledger.json, relative to
      wherever the app is run from (matches this project's
      other relative-path convention, e.g. UPLOAD_FOLDER).
      Override via the constructor if you want it elsewhere.

Example usage:
    from app.core.usage_ledger import UsageLedger

    ledger = UsageLedger()
    ledger.record(
        user_id=user.id,
        model="claude-sonnet-5",
        input_tokens=180,
        output_tokens=270,
    )
=========================================================
"""

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_lock = threading.Lock()

# MANUALLY MAINTAINED — $ per MILLION tokens. Verify against
# Anthropic's current published pricing before trusting these
# numbers for real financial decisions.
MODEL_PRICING: dict[str, dict[str, float]] = {
    "claude-haiku-4-5": {"input": 1.00, "output": 5.00},
    "claude-sonnet-5": {"input": 3.00, "output": 15.00},
    "claude-opus-4-8": {"input": 15.00, "output": 75.00},
}

_EMPTY_LEDGER = {
    "users": {},
    "models": {},
    "grand_total_input_tokens": 0,
    "grand_total_output_tokens": 0,
    "grand_total_cost_usd": 0.0,
    "last_updated": None,
}


def _calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    pricing = MODEL_PRICING.get(model)
    if pricing is None:
        return 0.0  # unknown model — can't price it, don't guess
    return (
        (input_tokens / 1_000_000) * pricing["input"]
        + (output_tokens / 1_000_000) * pricing["output"]
    )


# =========================================================
# Usage Ledger
# =========================================================

class UsageLedger:
    """
    Maintains data/usage_ledger.json: per-user and grand-total
    running token usage and dollar cost, updated in real time.
    """

    def __init__(self, path: Optional[str] = None):
        self.path = Path(path or "app/data/usage_ledger.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------
    # Internal — Load / Save
    # ---------------------------------------------------

    def _load(self) -> dict:
        if not self.path.exists():
            return dict(_EMPTY_LEDGER, users={})

        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            # Corrupted or unreadable — start fresh rather than
            # crash the app over a broken tracking file.
            return dict(_EMPTY_LEDGER, users={})

    def _save_atomic(self, data: dict) -> None:
        tmp_path = self.path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        tmp_path.replace(self.path)  # atomic swap

    # ---------------------------------------------------
    # Record
    # ---------------------------------------------------

    def record(
        self,
        user_id: uuid.UUID,
        model: str,
        input_tokens: Optional[int],
        output_tokens: Optional[int],
    ) -> None:
        """
        Records one AI interaction's token usage/cost against
        a user, updating both that user's running totals and
        the grand totals, then writes the file back to disk
        atomically.

        input_tokens/output_tokens of None are treated as 0 —
        better to still record the interaction (with 0 token
        cost) than silently skip tracking it entirely.

        This method should never raise in a way that breaks
        the calling AI feature — usage TRACKING failing must
        never take down actual user-facing functionality. Any
        unexpected error here is caught and swallowed (the
        interaction itself was already logged to the real
        database by this point regardless).
        """
        input_tokens = input_tokens or 0
        output_tokens = output_tokens or 0
        cost = _calculate_cost(model, input_tokens, output_tokens)

        try:
            with _lock:
                data = self._load()

                # Defensive: files written before this update won't
                # have a "models" key yet — add it rather than error.
                if "models" not in data:
                    data["models"] = {}

                uid_str = str(user_id)
                if uid_str not in data["users"]:
                    data["users"][uid_str] = {
                        "total_input_tokens": 0,
                        "total_output_tokens": 0,
                        "total_cost_usd": 0.0,
                    }

                if model not in data["models"]:
                    data["models"][model] = {
                        "total_input_tokens": 0,
                        "total_output_tokens": 0,
                        "total_cost_usd": 0.0,
                    }

                data["users"][uid_str]["total_input_tokens"] += input_tokens
                data["users"][uid_str]["total_output_tokens"] += output_tokens
                data["users"][uid_str]["total_cost_usd"] = round(
                    data["users"][uid_str]["total_cost_usd"] + cost, 6
                )

                data["models"][model]["total_input_tokens"] += input_tokens
                data["models"][model]["total_output_tokens"] += output_tokens
                data["models"][model]["total_cost_usd"] = round(
                    data["models"][model]["total_cost_usd"] + cost, 6
                )

                data["grand_total_input_tokens"] = data.get("grand_total_input_tokens", 0) + input_tokens
                data["grand_total_output_tokens"] = data.get("grand_total_output_tokens", 0) + output_tokens
                data["grand_total_cost_usd"] = round(
                    data.get("grand_total_cost_usd", 0.0) + cost, 6
                )
                data["last_updated"] = datetime.now(timezone.utc).isoformat()

                self._save_atomic(data)
        except Exception:
            # Deliberately swallowed — see docstring. Usage
            # tracking is a secondary concern; it must never
            # break the primary AI feature that already
            # succeeded and was already logged to the real DB.
            pass
"""
=========================================================
AIMeals Backend
Daily Tip Schema

Responsibilities:
    - Define the response shape for GET /ai/daily-tip

Example usage:
    from app.schemas.daily_tip import DailyTipOut
=========================================================
"""

from typing import Optional

from pydantic import BaseModel


# =========================================================
# Response Schema — Daily Tip
# =========================================================

class DailyTipOut(BaseModel):
    """
    tip_text is None when there isn't enough data yet to
    generate a meaningful tip (no goals configured) — the
    client should show nothing (or a "set your goals" nudge)
    rather than treat None as an error.
    """

    tip_text: Optional[str] = None
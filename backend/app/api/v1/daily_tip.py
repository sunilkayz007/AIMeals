"""
=========================================================
AIMeals Backend
Daily Tip API Route

Endpoint:
    GET /api/v1/ai/daily-tip   - get (or generate) today's tip

Requires a valid access token (Authorization: Bearer <token>).

Notes:
    - Unlike the other AI routes, this is a plain JSON GET, not
      SSE — a single short tip doesn't warrant streaming.
    - No controller layer, matching the existing pattern for
      every other AI route in this file family (ai_chat.py,
      ai_recipes.py) — the route calls AIService directly.
    - tip_text in the response is null (not a 404/error) when
      there's no meaningful tip to show yet — see
      AIService.get_daily_tip()'s docstring for exactly when
      that happens (no goals configured, or a Claude call
      failure that day).

Dependencies:
    - app.services.ai_service.AIService
    - app.core.dependencies.get_current_user
=========================================================
"""

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.B_database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.daily_tip import DailyTipOut
from app.services.ai_service import AIService

router = APIRouter(prefix="/api/v1/ai", tags=["AI"])


@router.get("/daily-tip", response_model=DailyTipOut)
def get_daily_tip(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DailyTipOut:
    """
    Returns today's cached tip if one already exists, or
    generates and caches a new one (at most once per user per
    day — see AIService.get_daily_tip()'s docstring for the
    full caching guarantee).
    """
    service = AIService(db)
    tip_text = service.get_daily_tip(current_user.id, date.today())
    return DailyTipOut(tip_text=tip_text)
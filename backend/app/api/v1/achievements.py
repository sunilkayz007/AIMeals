"""
=========================================================
AIMeals Backend
Achievements API Route

Endpoint:
    GET /api/v1/achievements   - list all achievements with
                                  this user's earned status

Requires a valid access token (Authorization: Bearer <token>).

Notes:
    - No controller layer, matching the existing pattern for
      every other lightweight route in this file family
      (daily_tip.py, coach_memory.py) -- the route calls
      AchievementService directly.
    - Achievement AWARDING happens elsewhere (inside
      NutritionLogService, right after a meal is logged -- see
      AchievementService.check_and_award_streaks()'s docstring).
      This route only ever READS status; it never awards
      anything itself.
    - Fetching this list marks any newly-earned-but-unseen
      achievements as seen, as a side effect (see
      AchievementService.get_achievements_for_user()'s
      docstring) -- the returned is_new flag reflects the
      state BEFORE that side effect, so the client still gets
      one chance to show a "New!" indicator on this same
      response.

Dependencies:
    - app.services.achievement_service.AchievementService
    - app.core.dependencies.get_current_user
=========================================================
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.B_database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.achievement import AchievementListOut, AchievementOut
from app.services.achievement_service import AchievementService

router = APIRouter(prefix="/api/v1/achievements", tags=["Achievements"])


@router.get("", response_model=AchievementListOut)
def get_achievements(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AchievementListOut:
    """
    Returns every achievement definition combined with this
    user's earned status, in display order.
    """
    service = AchievementService(db)
    results = service.get_achievements_for_user(current_user.id)
    return AchievementListOut(
        achievements=[AchievementOut(**r) for r in results]
    )

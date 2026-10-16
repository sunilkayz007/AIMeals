"""
=========================================================
AIMeals Backend
Coach Memory API Route

Endpoints:
    GET    /api/v1/coach/memory   - list remembered facts
    DELETE /api/v1/coach/memory   - clear all remembered facts

Requires a valid access token (Authorization: Bearer <token>).

Notes:
    - No controller layer, matching the existing pattern for
      every other lightweight AI-adjacent route in this file
      family (daily_tip.py) -- the route calls
      CoachMemoryRepository directly, since there's no
      business logic beyond "read this user's rows" /
      "delete this user's rows."
    - This is the user-facing "Coach memory" control surface
      referenced in the Coach roadmap plan's own "Privacy /
      control" requirement -- every fact the Coach silently
      remembers must be visible and clearable here.
    - DELETE clears ALL facts, not one at a time -- matches the
      mobile Settings screen's single "Clear" action. There is
      no per-fact delete endpoint because the plan doesn't call
      for one.

Dependencies:
    - app.repositories.coach_memory_repository.CoachMemoryRepository
    - app.core.dependencies.get_current_user
=========================================================
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.B_database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.repositories.coach_memory_repository import CoachMemoryRepository
from app.schemas.coach_memory import CoachMemoryClearOut, CoachMemoryFactOut, CoachMemoryListOut

router = APIRouter(prefix="/api/v1/coach", tags=["Coach"])


@router.get("/memory", response_model=CoachMemoryListOut)
def get_coach_memory(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CoachMemoryListOut:
    """
    Returns this user's remembered dietary-preference/goal
    facts, most recently added first.
    """
    repo = CoachMemoryRepository(db)
    facts = repo.get_recent(current_user.id, limit=15)
    return CoachMemoryListOut(
        facts=[CoachMemoryFactOut.model_validate(f) for f in facts]
    )


@router.delete("/memory", response_model=CoachMemoryClearOut)
def clear_coach_memory(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CoachMemoryClearOut:
    """
    Deletes every remembered fact for this user. User-initiated
    only -- there is no automatic clearing anywhere else in the
    app.
    """
    repo = CoachMemoryRepository(db)
    cleared_count = repo.clear_all(current_user.id)
    return CoachMemoryClearOut(cleared_count=cleared_count)

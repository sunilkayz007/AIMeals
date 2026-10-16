"""
=========================================================
AIMeals Backend
Allergy General Facts API Route

Endpoint:
    GET /api/v1/ai/allergy-facts   - get (or generate) the
                                      "Things you might not
                                      know" facts

Requires a valid access token (Authorization: Bearer <token>).

Notes:
    - Plain JSON GET, not SSE — matches daily_tip.py's pattern
      for the same reason (short, non-streamed response).
    - No controller layer, matching every other AI route in
      this file family.
    - Free — no credit cost, so no InsufficientCreditsError
      handling needed here.

Dependencies:
    - app.services.ai_service.AIService
    - app.core.dependencies.get_current_user
=========================================================
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.B_database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.allergy_general_facts import AllergyFactsOut
from app.services.ai_service import AIService

router = APIRouter(prefix="/api/v1/ai", tags=["AI"])


@router.get("/allergy-facts", response_model=AllergyFactsOut)
def get_allergy_facts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AllergyFactsOut:
    """
    Returns the cached "Things you might not know" facts,
    generating/refreshing them if needed — see
    AIService.get_allergy_general_facts()'s docstring for the
    full caching logic.
    """
    service = AIService(db)
    facts = service.get_allergy_general_facts(current_user.id)
    return AllergyFactsOut(facts=facts)
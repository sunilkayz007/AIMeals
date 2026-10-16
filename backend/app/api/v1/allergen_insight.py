"""
=========================================================
AIMeals Backend
Allergen Insight API Routes

Endpoints:
    GET  /api/v1/ai/allergen-insight/{allergy_id}
        - free short insight (always available) + whether
          the current user has already unlocked the deep
          version (and that text, if so)
    POST /api/v1/ai/allergen-insight/{allergy_id}/deep
        - Plus/Pro only, 1 credit on first unlock per user
          per allergen, free on repeat calls after that

Requires a valid access token (Authorization: Bearer <token>).

Status code mapping (no controller layer, matching every
other AI route in this file family — routes call AIService
directly and translate its exceptions here):
    ValueError                 -> 404 (unknown allergen)
    TierUpgradeRequiredError   -> 403 (Free tier, needs Plus/Pro)
    InsufficientCreditsError   -> 402 (Plus/Pro but out of credits)
    ClaudeAPIError             -> 502 (upstream call failed)

Dependencies:
    - app.services.ai_service.AIService
    - app.core.dependencies.get_current_user
=========================================================
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.B_database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import ClaudeAPIError, InsufficientCreditsError
from app.models.user import User
from app.schemas.allergen_insight import AllergenDeepInsightOut, AllergenInsightOut
from app.services.ai_service import AIService, TierUpgradeRequiredError

router = APIRouter(prefix="/api/v1/ai", tags=["AI"])


@router.get("/allergen-insight/{allergy_id}", response_model=AllergenInsightOut)
def get_allergen_insight(
    allergy_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AllergenInsightOut:
    """
    Free short insight for this allergen (generated on first-
    ever request for it, cached after that), plus whether the
    current user has already unlocked the deep version.
    """
    service = AIService(db)
    try:
        summary = service.get_allergen_insight_summary(current_user.id, allergy_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No allergen found with id={allergy_id}.",
        )

    return AllergenInsightOut(
        allergy_id=str(allergy_id),
        allergy_name=summary["allergy_name"],
        short_insight_text=summary["short_insight_text"],
        is_unlocked=summary["is_unlocked"],
        deep_insight_text=summary["deep_insight_text"],
    )


@router.post("/allergen-insight/{allergy_id}/deep", response_model=AllergenDeepInsightOut)
def get_allergen_deep_insight(
    allergy_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AllergenDeepInsightOut:
    """
    Deep (Sonnet) insight for this allergen. Plus/Pro only.
    Costs 1 credit on this user's first unlock of this
    allergen; free on every call after that (see
    AIService.get_allergen_deep_insight()'s docstring).
    """
    service = AIService(db)
    try:
        deep_text = service.get_allergen_deep_insight(current_user.id, allergy_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No allergen found with id={allergy_id}.",
        )
    except TierUpgradeRequiredError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except InsufficientCreditsError as e:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(e))
    except ClaudeAPIError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Couldn't generate the deep insight right now — please try again.",
        )

    return AllergenDeepInsightOut(deep_insight_text=deep_text)
"""
=========================================================
AIMeals Backend
Water Log API Routes

Endpoints:
    POST   /api/v1/water-logs                    - log a manual water entry
    DELETE /api/v1/water-logs/{log_id}            - remove a manual entry (idempotent)
    GET    /api/v1/water-logs/day/{target_date}   - combined daily summary
                                                     (manual + food-derived + pacing)

Requires a valid access token (Authorization: Bearer <token>).

No controller layer — matches the AI route family's pattern
(routes call the service directly); this feature is simple
enough not to need the extra layer nutrition_logs.py uses.

Dependencies:
    - app.services.water_log_service.WaterLogService
    - app.core.dependencies.get_current_user
=========================================================
"""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.B_database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.water_log import WaterDaySummaryOut, WaterLogCreate, WaterLogOut
from app.services.water_log_service import WaterLogService

router = APIRouter(prefix="/api/v1/water-logs", tags=["Water"])


@router.post("", response_model=WaterLogOut, status_code=status.HTTP_201_CREATED)
def log_water(
    payload: WaterLogCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WaterLogOut:
    service = WaterLogService(db)
    log = service.log_water(current_user.id, payload.logged_at, payload.amount_ml)
    return WaterLogOut.model_validate(log)


@router.delete("/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_water_log(
    log_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    service = WaterLogService(db)
    service.delete_water_log(log_id, current_user.id)


@router.get("/day/{target_date}", response_model=WaterDaySummaryOut)
def get_day_summary(
    target_date: date,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WaterDaySummaryOut:
    service = WaterLogService(db)
    summary = service.get_day_summary(current_user.id, target_date)
    return WaterDaySummaryOut(**summary)
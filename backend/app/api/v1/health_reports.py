"""
=========================================================
AIMeals Backend
Health Insights API Routes

Endpoints:
    POST   /api/v1/health-reports/analyze          - upload + analyze a health report, streamed via SSE
    GET    /api/v1/health-reports                  - list the current user's health reports
    GET    /api/v1/health-reports/{report_id}      - get a single health report
    DELETE /api/v1/health-reports/{report_id}      - delete a health report

Requires a valid access token (Authorization: Bearer <token>).

Response format -- /analyze (text/event-stream):
    event: stage    data: {"stage": "checking_credits"}
    event: stage    data: {"stage": "analyzing_report"}
    event: stage    data: {"stage": "saving"}
    event: result   data: {...HealthReportOut fields, JSON-safe...}

    On failure, a single error event replaces the result event:
    event: error    data: {"error_type": "UnrecognizedReportError", "detail": "..."}

Notes:
    - /analyze accepts multipart/form-data (a PDF or image
      file upload), like /ai/food-image/analyze -- not JSON.
    - No file is ever saved to disk -- bytes are read into
      memory, sent to Claude, then discarded. See
      AIService.analyze_health_report()'s docstring.
    - Upload and extraction are ONE step here, not two
      separate phases -- this app has no persisted
      "uploaded, not yet processed" intermediate state
      anywhere (see analyze_food_image()'s identical shape).
    - A HealthReport's status is always AWAITING_CONFIRMATION
      immediately after /analyze -- confirming it (Phase 5,
      not yet built) is a separate, later step. Nothing
      downstream may personalize based on this data until
      then.

Dependencies:
    - app.core.sse_streaming.stream_ai_progress
    - app.services.ai_service.AIService
    - app.schemas.health_report.HealthReportOut
    - app.core.dependencies.get_current_user
=========================================================
"""

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.B_database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import (
    HealthReportAnalysisError,
    HealthReportNotFoundError,
    NotHealthReportOwnerError,
)
from app.core.sse_streaming import stream_ai_progress
from app.models.health_report import HealthReport
from app.models.user import User
from app.schemas.health_report import HealthReportConfirmRequest, HealthReportOut
from app.services.ai_service import AIService

router = APIRouter(prefix="/api/v1/health-reports", tags=["Health Insights"])


def _serialize_health_report(report: HealthReport) -> dict:
    return HealthReportOut.model_validate(report).model_dump(mode="json")


# =========================================================
# Analyze Health Report -- Streamed via SSE
# =========================================================

@router.post("/analyze")
async def analyze_health_report(
    report: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """
    Uploads and analyzes a health/medical report (PDF, JPG,
    JPEG, or PNG), extracting raw lab test values. Streams
    progress stages, then a final result event with the
    created HealthReport.

    Returns an error event with error_type
    "UnrecognizedReportError" if the document doesn't appear
    to be a health/medical report.
    """
    file_bytes = await report.read()
    media_type = report.content_type or "application/octet-stream"

    service = AIService(db)

    return StreamingResponse(
        stream_ai_progress(
            service.analyze_health_report,
            serialize_result=_serialize_health_report,
            user_id=current_user.id,
            file_bytes=file_bytes,
            media_type=media_type,
            original_filename=report.filename or "report.pdf",
        ),
        media_type="text/event-stream",
    )


# =========================================================
# List Health Reports
# =========================================================

@router.get(
    "",
    response_model=list[HealthReportOut],
    status_code=status.HTTP_200_OK,
)
def get_health_reports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[HealthReportOut]:
    """Returns the current user's health reports, most recent first."""
    service = AIService(db)
    reports = service.get_health_reports_for_user(current_user.id)
    return [HealthReportOut.model_validate(r) for r in reports]


# =========================================================
# Get Single Health Report
# =========================================================

@router.get(
    "/{report_id}",
    response_model=HealthReportOut,
    status_code=status.HTTP_200_OK,
)
def get_health_report(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HealthReportOut:
    """
    Returns a single health report.

    Returns 404 if no such report exists, 403 if it belongs
    to another user.
    """
    service = AIService(db)

    try:
        report = service.get_health_report(report_id, current_user.id)
    except HealthReportNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except NotHealthReportOwnerError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    return HealthReportOut.model_validate(report)


# =========================================================
# Confirm Health Report
# =========================================================

@router.post(
    "/{report_id}/confirm",
    response_model=HealthReportOut,
    status_code=status.HTTP_200_OK,
)
def confirm_health_report(
    report_id: uuid.UUID,
    payload: HealthReportConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HealthReportOut:
    """
    Records the user's reviewed (possibly edited) markers as
    confirmed, then runs the Nutrition Focus Engine to produce
    non-diagnostic nutrition priorities. FREE -- no credit
    charge, this is a continuation of the original analysis.

    Only confirmed_markers and status are guaranteed to update
    on success -- nutrition_priorities may remain null if the
    Nutrition Focus Engine's call fails; the confirmed review
    work itself is never lost in that case. See
    AIService.confirm_health_report()'s docstring.

    Returns 404 if no such report exists, 403 if it belongs to
    another user.
    """
    service = AIService(db)

    markers_as_dicts = [m.model_dump() for m in payload.markers]

    try:
        report = service.confirm_health_report(
            report_id=report_id,
            user_id=current_user.id,
            confirmed_markers=markers_as_dicts,
        )
    except HealthReportNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except NotHealthReportOwnerError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except HealthReportAnalysisError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return HealthReportOut.model_validate(report)


# =========================================================
# Delete Health Report
# =========================================================

@router.delete(
    "/{report_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_health_report(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """
    Deletes a health report and its extracted/confirmed data
    permanently. There is no separate raw file to delete --
    none was ever stored.

    Returns 404 if no such report exists, 403 if it belongs
    to another user.
    """
    service = AIService(db)

    try:
        service.delete_health_report(report_id, current_user.id)
    except HealthReportNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except NotHealthReportOwnerError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

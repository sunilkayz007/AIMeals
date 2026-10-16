"""
=========================================================
AIMeals Backend
Report API Routes

Endpoints:
    POST   /api/v1/reports                       - submit a report
    GET    /api/v1/reports                       - list reports (own, or all if admin)
    GET    /api/v1/reports/{report_id}           - report detail + comment thread
    POST   /api/v1/reports/{report_id}/comments  - add a reply
    PATCH  /api/v1/reports/{report_id}/status    - admin-only status update
    POST   /api/v1/reports/{report_id}/close     - mark Resolved (owner or admin)

Requires a valid access token (Authorization: Bearer <token>)
on every route.

Notes:
    - Admin detection uses `current_user.role == UserRole.ADMIN`
      (confirmed against the real User model, 2026-08-08).
    - Ownership vs admin-access authorization itself (can this
      caller see/comment on/close this specific report) is
      enforced in ReportService, not here — this file only
      decides IS the caller an admin, then passes that bool
      through, and converts the service's domain exceptions
      into the right HTTP status codes.
    - /close is deliberately separate from the admin-only
      PATCH .../status — a normal user should only ever be
      able to close their OWN report (mark it Resolved once
      they're satisfied with a reply), never set arbitrary
      status values on any report.

Dependencies:
    - app.core.dependencies.get_current_user
    - app.controller.report_controller.ReportController
=========================================================
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.B_database import get_db
from app.core.dependencies import get_current_user
from app.controller.report_controller import ReportController
from app.models.user import User, UserRole
from app.services.report_service import ReportNotFoundError, NotReportOwnerError
from app.schemas.report import (
    ReportCreate,
    ReportCommentCreate,
    ReportStatusUpdate,
    ReportOut,
    ReportDetailOut,
    ReportCommentOut,
)

router = APIRouter(prefix="/api/v1/reports", tags=["Reports"])


def _is_admin(user: User) -> bool:
    return getattr(user, "role", None) == UserRole.ADMIN


# =========================================================
# Create
# =========================================================

@router.post("", response_model=ReportOut)
async def create_report(
    payload: ReportCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportOut:
    controller = ReportController(db)
    return controller.create_report(current_user.id, payload)


# =========================================================
# List
# =========================================================

@router.get("", response_model=list[ReportOut])
async def list_reports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ReportOut]:
    controller = ReportController(db)
    return controller.list_reports(current_user.id, _is_admin(current_user))


# =========================================================
# Detail
# =========================================================

@router.get("/{report_id}", response_model=ReportDetailOut)
async def get_report_detail(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportDetailOut:
    controller = ReportController(db)
    try:
        return controller.get_report_detail(report_id, current_user.id, _is_admin(current_user))
    except ReportNotFoundError:
        raise HTTPException(status_code=404, detail="Report not found")
    except NotReportOwnerError:
        raise HTTPException(status_code=403, detail="This report belongs to another user")


# =========================================================
# Add Comment
# =========================================================

@router.post("/{report_id}/comments", response_model=ReportCommentOut)
async def add_comment(
    report_id: uuid.UUID,
    payload: ReportCommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportCommentOut:
    controller = ReportController(db)
    try:
        return controller.add_comment(report_id, current_user.id, _is_admin(current_user), payload)
    except ReportNotFoundError:
        raise HTTPException(status_code=404, detail="Report not found")
    except NotReportOwnerError:
        raise HTTPException(status_code=403, detail="This report belongs to another user")


# =========================================================
# Update Status (admin-only)
# =========================================================

@router.patch("/{report_id}/status", response_model=ReportOut)
async def update_status(
    report_id: uuid.UUID,
    payload: ReportStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportOut:
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    controller = ReportController(db)
    try:
        return controller.update_status(report_id, payload)
    except ReportNotFoundError:
        raise HTTPException(status_code=404, detail="Report not found")


# =========================================================
# Close (report owner, or admin)
# =========================================================

@router.post("/{report_id}/close", response_model=ReportOut)
async def close_report(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportOut:
    controller = ReportController(db)
    try:
        return controller.close_report(report_id, current_user.id, _is_admin(current_user))
    except ReportNotFoundError:
        raise HTTPException(status_code=404, detail="Report not found")
    except NotReportOwnerError:
        raise HTTPException(status_code=403, detail="This report belongs to another user")
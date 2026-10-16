"""
=========================================================
AIMeals Backend
Report Controller

Responsibilities:
    - Convert between API schemas and service calls
    - Contains NO business logic — that lives in
      ReportService

Dependencies:
    - app.services.report_service.ReportService
    - app.schemas.report.*
=========================================================
"""

import uuid
from typing import List

from sqlalchemy.orm import Session

from app.schemas.report import (
    ReportCreate,
    ReportCommentCreate,
    ReportStatusUpdate,
    ReportOut,
    ReportDetailOut,
    ReportCommentOut,
)
from app.services.report_service import ReportService


class ReportController:
    def __init__(self, db: Session):
        self.db = db
        self.service = ReportService(db)

    def create_report(self, user_id: uuid.UUID, payload: ReportCreate) -> ReportOut:
        report = self.service.create_report(
            user_id=user_id,
            category=payload.category,
            title=payload.title,
            description=payload.description,
        )
        return self._to_report_out(report)

    def list_reports(self, user_id: uuid.UUID, is_admin: bool) -> List[ReportOut]:
        reports = self.service.list_reports(user_id, is_admin)
        return [self._to_report_out(r) for r in reports]

    def get_report_detail(self, report_id: uuid.UUID, user_id: uuid.UUID, is_admin: bool) -> ReportDetailOut:
        report = self.service.get_report_detail(report_id, user_id, is_admin)
        return ReportDetailOut(
            id=report.id,
            user_id=report.user_id,
            user_email=report.user.email,
            category=report.category,
            title=report.title,
            description=report.description,
            status=report.status,
            created_at=report.created_at,
            updated_at=report.updated_at,
            comments=[self._to_comment_out(c) for c in report.comments],
        )

    def add_comment(
        self,
        report_id: uuid.UUID,
        user_id: uuid.UUID,
        is_admin: bool,
        payload: ReportCommentCreate,
    ) -> ReportCommentOut:
        comment = self.service.add_comment(
            report_id=report_id,
            author_user_id=user_id,
            comment_text=payload.comment_text,
            is_admin=is_admin,
        )
        return self._to_comment_out(comment)

    def update_status(self, report_id: uuid.UUID, payload: ReportStatusUpdate) -> ReportOut:
        report = self.service.update_status(report_id, payload.status)
        return self._to_report_out(report)

    def close_report(self, report_id: uuid.UUID, user_id: uuid.UUID, is_admin: bool) -> ReportOut:
        report = self.service.close_report(report_id, user_id, is_admin)
        return self._to_report_out(report)

    # ---------------------------------------------------
    # Internal helpers
    #
    # Built with explicit keyword arguments rather than
    # ReportOut.model_validate(report, from_attributes=True)
    # — the ORM object only has user_id / a `user` relationship,
    # not a flat user_email attribute, so automatic attribute-
    # matching can't find it (this was a real bug, not a
    # theoretical one — see the 500 error it caused when a
    # report was created).
    # ---------------------------------------------------

    @staticmethod
    def _to_report_out(report) -> ReportOut:
        return ReportOut(
            id=report.id,
            user_id=report.user_id,
            user_email=report.user.email,
            category=report.category,
            title=report.title,
            description=report.description,
            status=report.status,
            created_at=report.created_at,
            updated_at=report.updated_at,
        )

    @staticmethod
    def _to_comment_out(comment) -> ReportCommentOut:
        return ReportCommentOut(
            id=comment.id,
            report_id=comment.report_id,
            author_user_id=comment.author_user_id,
            author_email=comment.author.email,
            is_admin_reply=comment.is_admin_reply,
            comment_text=comment.comment_text,
            created_at=comment.created_at,
        )
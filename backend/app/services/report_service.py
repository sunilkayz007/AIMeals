"""
=========================================================
AIMeals Backend
Report Service

Responsibilities:
    - Enforce who can see/comment on which reports
    - Auto-advance status OPEN -> IN_PROGRESS on first admin
      reply

Dependencies:
    - app.repositories.report_repository.ReportRepository
    - app.repositories.report_repository.ReportCommentRepository

Notes:
    - Ownership/admin authorization itself (deciding whether
      the calling user IS an admin) belongs to the route layer,
      which has access to the authenticated user's role. This
      service assumes the caller has already been authorized
      and just needs is_admin passed in to decide behavior
      (e.g. which reports get returned, whether a reply counts
      as the official response).
=========================================================
"""

import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.report import Report, ReportCategory, ReportStatus
from app.repositories.report_repository import ReportRepository, ReportCommentRepository


class ReportNotFoundError(Exception):
    pass


class NotReportOwnerError(Exception):
    pass


class ReportService:
    def __init__(self, db: Session):
        self.db = db
        self.report_repo = ReportRepository(db)
        self.comment_repo = ReportCommentRepository(db)

    # ---------------------------------------------------
    # Create
    # ---------------------------------------------------

    def create_report(
        self,
        user_id: uuid.UUID,
        category: ReportCategory,
        title: str,
        description: str,
    ) -> Report:
        return self.report_repo.create(
            user_id=user_id,
            category=category,
            title=title,
            description=description,
        )

    # ---------------------------------------------------
    # Read
    # ---------------------------------------------------

    def list_reports(self, user_id: uuid.UUID, is_admin: bool) -> List[Report]:
        """Admins see every report; everyone else sees only their own."""
        if is_admin:
            return self.report_repo.get_all()
        return self.report_repo.get_by_user(user_id)

    def get_report_detail(self, report_id: uuid.UUID, user_id: uuid.UUID, is_admin: bool) -> Report:
        report = self.report_repo.get_by_id(report_id)
        if report is None:
            raise ReportNotFoundError(f"No report with id {report_id}")
        if not is_admin and report.user_id != user_id:
            raise NotReportOwnerError("This report belongs to another user")
        return report

    # ---------------------------------------------------
    # Comments
    # ---------------------------------------------------

    def add_comment(
        self,
        report_id: uuid.UUID,
        author_user_id: uuid.UUID,
        comment_text: str,
        is_admin: bool,
    ):
        report = self.get_report_detail(report_id, author_user_id, is_admin)

        comment = self.comment_repo.create(
            report_id=report.id,
            author_user_id=author_user_id,
            comment_text=comment_text,
            is_admin_reply=is_admin,
        )

        # First admin reply moves a report from OPEN to
        # IN_PROGRESS, so the user sees it was actually seen.
        # Any reply after that (admin or user) doesn't change
        # status further — only PATCH .../status explicitly
        # marks RESOLVED.
        if is_admin and report.status == ReportStatus.OPEN:
            self.report_repo.update_status(report, ReportStatus.IN_PROGRESS)

        return comment

    # ---------------------------------------------------
    # Status
    # ---------------------------------------------------

    def update_status(self, report_id: uuid.UUID, status: ReportStatus) -> Report:
        """Admin-only — enforced at the route layer."""
        report = self.report_repo.get_by_id(report_id)
        if report is None:
            raise ReportNotFoundError(f"No report with id {report_id}")
        return self.report_repo.update_status(report, status)

    def close_report(self, report_id: uuid.UUID, user_id: uuid.UUID, is_admin: bool) -> Report:
        """
        Marks a report Resolved. Allowed for the report's own
        owner (closing their own thread once they're satisfied
        with the reply) or an admin (closing any). Ownership is
        checked here rather than left to the route, same as
        get_report_detail — this is the one place that decision
        needs to be made correctly.
        """
        report = self.report_repo.get_by_id(report_id)
        if report is None:
            raise ReportNotFoundError(f"No report with id {report_id}")
        if not is_admin and report.user_id != user_id:
            raise NotReportOwnerError("This report belongs to another user")
        return self.report_repo.update_status(report, ReportStatus.RESOLVED)
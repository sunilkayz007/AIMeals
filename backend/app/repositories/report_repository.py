"""
=========================================================
AIMeals Backend
Report Repository

Responsibilities:
    - Perform CRUD operations against reports and
      report_comments
    - Contains NO business logic

Dependencies:
    - app.models.report.Report / ReportComment
=========================================================
"""

import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.report import Report, ReportComment, ReportStatus


# =========================================================
# Report Repository
# =========================================================

class ReportRepository:
    def __init__(self, db: Session):
        self.db = db

    # ---------------------------------------------------
    # Read
    # ---------------------------------------------------

    def get_by_id(self, report_id: uuid.UUID) -> Optional[Report]:
        return self.db.query(Report).filter(Report.id == report_id).first()

    def get_by_user(self, user_id: uuid.UUID) -> List[Report]:
        return (
            self.db.query(Report)
            .filter(Report.user_id == user_id)
            .order_by(Report.created_at.desc())
            .all()
        )

    def get_all(self) -> List[Report]:
        """Admin-only listing — every report, newest first."""
        return self.db.query(Report).order_by(Report.created_at.desc()).all()

    # ---------------------------------------------------
    # Create
    # ---------------------------------------------------

    def create(
        self,
        user_id: uuid.UUID,
        category,
        title: str,
        description: str,
    ) -> Report:
        new_report = Report(
            user_id=user_id,
            category=category,
            title=title,
            description=description,
        )
        self.db.add(new_report)
        self.db.commit()
        self.db.refresh(new_report)
        return new_report

    # ---------------------------------------------------
    # Update
    # ---------------------------------------------------

    def update_status(self, report: Report, status: ReportStatus) -> Report:
        report.status = status
        self.db.commit()
        self.db.refresh(report)
        return report


# =========================================================
# Report Comment Repository
# =========================================================

class ReportCommentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_report(self, report_id: uuid.UUID) -> List[ReportComment]:
        return (
            self.db.query(ReportComment)
            .filter(ReportComment.report_id == report_id)
            .order_by(ReportComment.created_at)
            .all()
        )

    def create(
        self,
        report_id: uuid.UUID,
        author_user_id: uuid.UUID,
        comment_text: str,
        is_admin_reply: bool = False,
    ) -> ReportComment:
        new_comment = ReportComment(
            report_id=report_id,
            author_user_id=author_user_id,
            comment_text=comment_text,
            is_admin_reply=is_admin_reply,
        )
        self.db.add(new_comment)
        self.db.commit()
        self.db.refresh(new_comment)
        return new_comment
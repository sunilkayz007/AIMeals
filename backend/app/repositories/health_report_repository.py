"""
=========================================================
AIMeals Backend
Health Report Repository

Responsibilities:
    - Perform CRUD operations against the health_reports table
    - Contains NO business logic

Dependencies:
    - app.models.health_report.HealthReport

Example usage:
    from app.repositories.health_report_repository import HealthReportRepository

    repo = HealthReportRepository(db)
    reports = repo.get_by_user(user.id)
=========================================================
"""

import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.health_report import HealthReport, HealthReportStatus


# =========================================================
# Health Report Repository
# =========================================================

class HealthReportRepository:
    """
    Encapsulates all direct database access for the
    HealthReport model.
    """

    def __init__(self, db: Session):
        self.db = db

    # ---------------------------------------------------
    # Read
    # ---------------------------------------------------

    def get_by_id(self, report_id: uuid.UUID) -> Optional[HealthReport]:
        return self.db.query(HealthReport).filter(HealthReport.id == report_id).first()

    def get_by_user(self, user_id: uuid.UUID) -> List[HealthReport]:
        """Returns a user's health reports, most recent first."""
        return (
            self.db.query(HealthReport)
            .filter(HealthReport.user_id == user_id)
            .order_by(HealthReport.created_at.desc())
            .all()
        )

    def get_latest_confirmed_for_user(self, user_id: uuid.UUID) -> Optional[HealthReport]:
        """
        Returns the user's most recently CONFIRMED health report,
        or None if they have none. Used by AIService's
        _build_nutrition_focus_context() to pull the nutrition
        priorities (never raw markers) that inform recipe/meal-plan/
        coach generation — see that method's docstring.
        """
        return (
            self.db.query(HealthReport)
            .filter(
                HealthReport.user_id == user_id,
                HealthReport.status == HealthReportStatus.CONFIRMED,
            )
            .order_by(HealthReport.updated_at.desc())
            .first()
        )

    def get_previous_confirmed_for_user(
        self,
        user_id: uuid.UUID,
        exclude_report_id: uuid.UUID,
    ) -> Optional[HealthReport]:
        """
        Returns the user's most recently CONFIRMED health report,
        EXCLUDING a specific report id — used to find the "previous"
        report to compare against when a NEW report is being
        confirmed (at that point, the new report may already be
        CONFIRMED itself, so a plain get_latest_confirmed_for_user()
        would just return the new report back). See
        AIService._compute_marker_trends() and
        confirm_health_report()'s trend-comparison logic.
        """
        return (
            self.db.query(HealthReport)
            .filter(
                HealthReport.user_id == user_id,
                HealthReport.status == HealthReportStatus.CONFIRMED,
                HealthReport.id != exclude_report_id,
            )
            .order_by(HealthReport.updated_at.desc())
            .first()
        )

    # ---------------------------------------------------
    # Create
    # ---------------------------------------------------

    def create(
        self,
        user_id: uuid.UUID,
        extracted_markers: list[dict],
        ai_interaction_id: Optional[uuid.UUID] = None,
        report_label: Optional[str] = None,
        status: HealthReportStatus = HealthReportStatus.AWAITING_CONFIRMATION,
    ) -> HealthReport:
        """
        Creates a new health report row. Called only AFTER
        Claude has successfully extracted markers — matching
        FoodImageRepository/analyze_food_image()'s pattern, a
        row is never created for a failed/rejected analysis.
        """
        new_report = HealthReport(
            user_id=user_id,
            ai_interaction_id=ai_interaction_id,
            report_label=report_label,
            status=status,
            extracted_markers=extracted_markers,
        )

        self.db.add(new_report)
        self.db.commit()
        self.db.refresh(new_report)

        return new_report

    # ---------------------------------------------------
    # Update
    # ---------------------------------------------------

    def update(self, report: HealthReport, **fields) -> HealthReport:
        """
        Updates arbitrary fields on an existing health report.

        Usage:
            repo.update(report, confirmed_markers=[...], status=HealthReportStatus.CONFIRMED)
        """
        for key, value in fields.items():
            setattr(report, key, value)

        self.db.commit()
        self.db.refresh(report)

        return report

    # ---------------------------------------------------
    # Delete
    # ---------------------------------------------------

    def delete(self, report: HealthReport) -> None:
        self.db.delete(report)
        self.db.commit()
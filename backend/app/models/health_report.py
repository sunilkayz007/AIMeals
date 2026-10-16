"""
=========================================================
AIMeals Backend
Health Report Model

Responsibilities:
    - Define the health_reports table schema
    - Define the HealthReportStatus enum

Dependencies:
    - app.B_database.Base
    - app.models.user.User
    - app.models.ai_interaction.AIInteraction (nullable FK)

Notes:
    - Phase 1 of the Health Insights feature ("From Report to
      Plate") — this model only. No AI extraction logic, no
      routes yet; those are later phases.
    - Deliberately follows FoodImage's exact established
      pattern for this app, not the originally-drafted spec's
      assumptions (which suggested a separate "uploaded" /
      "processing" / "failed" status pipeline implying
      persistent file storage and a multi-step background
      job). This app has neither: every existing AI-vision
      feature (analyze_food_image) is synchronous — read
      bytes, call Claude, create the row ONLY on success — and
      NEVER persists the raw file. Health reports follow that
      same shape:
        - No raw PDF/image is ever stored anywhere. Bytes are
          read into memory, sent to Claude, then discarded —
          identical to FoodImage's model docstring.
        - No "uploaded"/"processing"/"failed" states exist,
          because there is no intermediate persisted state
          before extraction succeeds. If extraction fails, an
          exception is raised (matching InappropriateImageError/
          FoodImageAnalysisError) and NOTHING is saved — same
          as food image analysis today.
        - The real lifecycle is therefore just two states,
          directly mirroring FoodImageStatus.PENDING/CONFIRMED:
          AWAITING_CONFIRMATION (Claude has extracted markers,
          user hasn't reviewed/confirmed them yet) and
          CONFIRMED (user has reviewed, possibly edited, and
          explicitly confirmed the data — see module docstring
          on why confirmation is mandatory before any
          nutrition-focus/personalization step may use this
          data).
    - extracted_markers is the AI's raw output — a JSONB list
      of marker dicts (name, value, unit, reference range,
      source_page, confidence). confirmed_markers starts NULL
      and is populated only once the user has reviewed/edited
      and explicitly confirmed — this is the mandatory
      human-in-the-loop gate the spec requires (Phase 5):
      nothing downstream may read extracted_markers directly,
      only confirmed_markers, once it exists.
    - report_label is a short, human-readable title for this
      report (e.g. "Full Body Checkup — Aug 2026"), either
      Claude-derived from the document or a simple fallback —
      used for the "My Health Insights" history list (a later
      phase), not required for extraction itself.

Example usage:
    from app.models.health_report import HealthReport, HealthReportStatus

    report = HealthReport(
        user_id=user.id,
        status=HealthReportStatus.AWAITING_CONFIRMATION,
        extracted_markers=[{"name": "Vitamin D", "value": 11.8, ...}],
    )
=========================================================
"""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.B_database import Base


# =========================================================
# Health Report Status Enum
# =========================================================

class HealthReportStatus(str, enum.Enum):
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    CONFIRMED = "confirmed"


# =========================================================
# Health Report Model
# =========================================================

class HealthReport(Base):
    """
    Represents one analyzed health/medical report — the
    nutrition-relevant markers Claude extracted from it, and
    the confirmed/awaiting-confirmation resolution state.

    Table: health_reports
    """

    __tablename__ = "health_reports"

    # ---------------------------------------------------
    # Primary Key
    # ---------------------------------------------------

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ---------------------------------------------------
    # Foreign Keys
    # ---------------------------------------------------

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    ai_interaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_interactions.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ---------------------------------------------------
    # Report Details
    # ---------------------------------------------------

    report_label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    status: Mapped[HealthReportStatus] = mapped_column(
        Enum(HealthReportStatus, name="health_report_status"),
        nullable=False,
        default=HealthReportStatus.AWAITING_CONFIRMATION,
    )

    # AI's raw extraction — never used directly by any
    # downstream nutrition-focus/personalization step. See
    # module docstring — only confirmed_markers may be used
    # for that, once it exists.
    extracted_markers: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)

    # NULL until the user explicitly confirms (Phase 5) —
    # this is the mandatory human-in-the-loop gate. May differ
    # from extracted_markers if the user edited/removed/added
    # entries during review.
    confirmed_markers: Mapped[Optional[list[dict]]] = mapped_column(JSONB, nullable=True)

    # NULL until confirm_health_report() runs the Nutrition
    # Focus Engine (Phase 6) against confirmed_markers -- a
    # list of non-diagnostic nutrition priorities (e.g.
    # "Increase Dietary Fiber", priority level, suggested
    # action items). NEVER a diagnosis or disease claim -- see
    # AIService's _NUTRITION_FOCUS_SYSTEM_PROMPT for the exact
    # safety-constrained shape. This is the ONLY health-report-
    # derived data any other feature (recipe generation, meal
    # plans, the Nutrition Coach) may read -- raw markers/
    # values are never exposed to those features directly.
    nutrition_priorities: Mapped[Optional[list[dict]]] = mapped_column(JSONB, nullable=True)

    # ---------------------------------------------------
    # Timestamps
    # ---------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ---------------------------------------------------
    # Relationships
    # ---------------------------------------------------

    user = relationship("User")
    ai_interaction = relationship("AIInteraction")

    # ---------------------------------------------------
    # Representation
    # ---------------------------------------------------

    def __repr__(self) -> str:
        return f"<HealthReport id={self.id} user_id={self.user_id} status={self.status}>"

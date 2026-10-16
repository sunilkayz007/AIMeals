"""
=========================================================
AIMeals Backend
Report Model

Responsibilities:
    - Define the reports table schema (user feedback/reviews)
    - Define the report_comments table schema (the reply
      thread — admin replies AND any user follow-ups)
    - Define ReportCategory and ReportStatus enums

Dependencies:
    - app.B_database.Base
    - app.models.user.User

Notes:
    - This is the "Report" feature: users submit an honest
      review/report (bug, suggestion, complaint, or praise),
      and admin replies are posted as comments on the same
      thread — visible to the user, so the whole exchange is
      transparent rather than a black-box support inbox.
    - Every report and comment is a real, permanent row —
      the intent is this doubles as a durable feedback corpus
      Sunil can later mine to improve the app and the AI
      prompts, not just a live support queue.
    - is_admin_reply is denormalized onto the comment (rather
      than derived by joining back to the author's role every
      render) purely so the frontend can badge "Team reply"
      without an extra lookup — it's set once, at write time,
      from the author's actual role.
    - status auto-advances OPEN -> IN_PROGRESS the moment an
      admin posts the first reply (see ReportService), so a
      user immediately sees their report was actually seen.
      RESOLVED is set explicitly by admin via PATCH.

Example usage:
    from app.models.report import Report, ReportComment, ReportCategory, ReportStatus

    report = Report(
        user_id=user.id,
        category=ReportCategory.BUG,
        title="Water ring doesn't update",
        description="...",
    )
=========================================================
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, Boolean, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.B_database import Base


# =========================================================
# Enums
# =========================================================

class ReportCategory(str, enum.Enum):
    BUG = "bug"
    SUGGESTION = "suggestion"
    COMPLAINT = "complaint"
    PRAISE = "praise"


class ReportStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"


# =========================================================
# Report Model
# =========================================================

class Report(Base):
    """
    One user-submitted review/report.

    Table: reports
    """

    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    category: Mapped[ReportCategory] = mapped_column(
        Enum(ReportCategory, name="report_category"),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus, name="report_status"),
        nullable=False,
        default=ReportStatus.OPEN,
    )

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

    user = relationship("User")
    comments = relationship(
        "ReportComment",
        order_by="ReportComment.created_at",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Report id={self.id} category={self.category} status={self.status}>"


# =========================================================
# Report Comment Model
# =========================================================

class ReportComment(Base):
    """
    One reply in a report's thread — either the admin's
    response or a user follow-up.

    Table: report_comments
    """

    __tablename__ = "report_comments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    author_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Set once at write time from the author's actual role —
    # see module notes.
    is_admin_reply: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    comment_text: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    author = relationship("User")

    def __repr__(self) -> str:
        return f"<ReportComment id={self.id} report_id={self.report_id} is_admin_reply={self.is_admin_reply}>"
"""
=========================================================
AIMeals Backend
Coach Memory Fact Model

Responsibilities:
    - Persist discrete dietary-preference/goal facts the
      Nutrition Coach extracts from a conversation, so they
      carry over into FUTURE conversations (Part 1 of the
      Coach roadmap — see Claude outputs/coach-roadmap-plan.md)

Dependencies:
    - app.B_database.Base

Notes:
    - Deliberately structured rows (one fact per row), not a
      single prose "running summary" blob — per the plan's own
      reasoning, discrete facts are easier to show back to the
      user ("Coach remembers: ...") and easier to delete
      individually, which matters here since this is dietary/
      health-adjacent information (same "user-controlled, not
      just user-visible" reasoning already applied to Health
      Insights).
    - Scope is deliberately narrow: dietary preferences and
      goals ONLY. AIService._extract_and_store_coach_memory()'s
      extraction prompt explicitly excludes mood/emotional
      content — this was a deliberate product decision (see the
      plan's "Memory scope" open question), not an oversight.
    - fact is capped at 300 chars (matches the column) — the
      extraction prompt asks for well under that, this is a
      hard backstop, not the expected length.
    - No unique constraint on (user_id, fact) — de-duplication
      of near-identical facts and the retention cap (currently
      40 most recent per user) are both handled in
      CoachMemoryRepository.add_fact(), not at the DB level,
      since "near-identical" isn't something a DB constraint can
      express.

Example usage:
    from app.models.coach_memory import CoachMemoryFact

    fact = CoachMemoryFact(user_id=user.id, fact="prefers high-protein breakfasts")
=========================================================
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.B_database import Base


class CoachMemoryFact(Base):
    """
    One durable dietary-preference/goal fact remembered about a
    user, extracted from a past Coach conversation.

    Table: coach_memory_facts
    """

    __tablename__ = "coach_memory_facts"

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

    fact: Mapped[str] = mapped_column(String(300), nullable=False)

    # Which chat session this was extracted from — informational
    # only (debugging/auditing), not a foreign key since chat
    # sessions aren't a persisted table of their own (session_id
    # is just a UUID grouping AiInteraction rows).
    source_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<CoachMemoryFact user_id={self.user_id} fact={self.fact!r}>"

"""
=========================================================
AIMeals Backend
Coach Memory Fact Repository

Responsibilities:
    - Add a newly-extracted dietary/goal fact for a user,
      de-duplicating near-identical facts and enforcing a
      retention cap
    - Read a user's remembered facts (most recent first)
    - Clear all of a user's remembered facts (user-initiated,
      from Settings — see the plan's "Privacy / control" note)

Dependencies:
    - app.models.coach_memory.CoachMemoryFact

Example usage:
    from app.repositories.coach_memory_repository import CoachMemoryRepository

    repo = CoachMemoryRepository(db)
    repo.add_fact(user_id, "prefers high-protein breakfasts")
    facts = repo.get_recent(user_id, limit=15)
=========================================================
"""

import uuid
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.coach_memory import CoachMemoryFact

# Hard cap on how many facts are kept per user — this is this
# project's current answer to the roadmap plan's open "Retention"
# question (bounded by a simple FIFO cap rather than left to grow
# indefinitely or requiring a separate summarization pass).
MAX_FACTS_PER_USER = 40


class CoachMemoryRepository:
    """
    Encapsulates all direct database access for the
    CoachMemoryFact model.
    """

    def __init__(self, db: Session):
        self.db = db

    def add_fact(
        self,
        user_id: uuid.UUID,
        fact: str,
        source_session_id: Optional[uuid.UUID] = None,
    ) -> Optional[CoachMemoryFact]:
        """
        Stores a new remembered fact for this user.

        De-duplication: if the user already has a fact whose text
        matches (case-insensitively, exact match) the new one,
        this is a silent no-op — returns None rather than creating
        a duplicate row. This is a deliberately simple heuristic
        (not fuzzy/semantic matching) — a display-only nicety, not
        correctness-critical, matching this codebase's general
        approach to best-effort AI-adjacent bookkeeping.

        Retention: after inserting, if the user now has more than
        MAX_FACTS_PER_USER facts, the oldest are deleted until back
        at the cap — a simple FIFO bound rather than unbounded
        growth.
        """
        normalized = fact.strip()
        if not normalized:
            return None

        existing = self.db.execute(
            select(CoachMemoryFact).where(
                CoachMemoryFact.user_id == user_id,
                func.lower(CoachMemoryFact.fact) == normalized.lower(),
            )
        ).scalar_one_or_none()
        if existing is not None:
            return None

        new_fact = CoachMemoryFact(
            user_id=user_id,
            fact=normalized[:300],
            source_session_id=source_session_id,
        )
        self.db.add(new_fact)
        self.db.commit()
        self.db.refresh(new_fact)

        self._enforce_retention_cap(user_id)

        return new_fact

    def get_recent(self, user_id: uuid.UUID, limit: int = 15) -> List[CoachMemoryFact]:
        """Returns this user's most recently added facts, newest first."""
        return list(
            self.db.execute(
                select(CoachMemoryFact)
                .where(CoachMemoryFact.user_id == user_id)
                .order_by(CoachMemoryFact.created_at.desc())
                .limit(limit)
            ).scalars()
        )

    def clear_all(self, user_id: uuid.UUID) -> int:
        """
        Deletes every remembered fact for this user. Returns the
        number of rows deleted. User-initiated only (a "Clear"
        button in Settings) — never called automatically.
        """
        facts = list(
            self.db.execute(select(CoachMemoryFact).where(CoachMemoryFact.user_id == user_id)).scalars()
        )
        count = len(facts)
        for f in facts:
            self.db.delete(f)
        self.db.commit()
        return count

    def _enforce_retention_cap(self, user_id: uuid.UUID) -> None:
        all_facts = list(
            self.db.execute(
                select(CoachMemoryFact)
                .where(CoachMemoryFact.user_id == user_id)
                .order_by(CoachMemoryFact.created_at.desc())
            ).scalars()
        )
        if len(all_facts) <= MAX_FACTS_PER_USER:
            return
        for stale in all_facts[MAX_FACTS_PER_USER:]:
            self.db.delete(stale)
        self.db.commit()


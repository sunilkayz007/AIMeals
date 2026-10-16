"""
=========================================================
AIMeals Backend
AI Interaction Repository

Responsibilities:
    - Perform CRUD operations against the ai_interactions table
    - Contains NO business logic

Dependencies:
    - app.models.ai_interaction.AIInteraction

Notes:
    - get_total_tokens_used exists specifically to support
      auditing the tier-based cost control strategy: it lets
      the service layer (or an admin report) verify actual
      token spend per user, and cross-check that Free-tier
      users are genuinely being routed to the cheaper model
      as intended, rather than trusting the routing logic
      blindly.
    - get_all_users_token_usage is the aggregation query
      behind scripts/user_usage_report.py — it groups by user
      and sums tokens_used/input_tokens/output_tokens
      separately, so the report script can tell the
      difference between rows logged before and after the
      input/output split (see ai_interaction.py's model
      docstring for why that split exists).

Example usage:
    from app.repositories.ai_interaction_repository import AIInteractionRepository

    repo = AIInteractionRepository(db)
    chat_thread = repo.get_by_session(session_id)
=========================================================
"""

import uuid
from datetime import date
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.ai_interaction import AIInteraction, InteractionType
from app.models.user import User


# =========================================================
# AI Interaction Repository
# =========================================================

class AIInteractionRepository:
    """
    Encapsulates all direct database access for the AIInteraction model.
    """

    def __init__(self, db: Session):
        self.db = db

    # ---------------------------------------------------
    # Read
    # ---------------------------------------------------

    def get_by_id(self, interaction_id: uuid.UUID) -> Optional[AIInteraction]:
        return (
            self.db.query(AIInteraction)
            .filter(AIInteraction.id == interaction_id)
            .first()
        )

    def get_by_user(
        self,
        user_id: uuid.UUID,
        limit: Optional[int] = None,
    ) -> List[AIInteraction]:
        """
        Returns a user's AI interaction history, most recent
        first. Optionally limited to the N most recent.
        """
        query = (
            self.db.query(AIInteraction)
            .filter(AIInteraction.user_id == user_id)
            .order_by(AIInteraction.created_at.desc())
        )

        if limit is not None:
            query = query.limit(limit)

        return query.all()

    def get_by_session(self, session_id: uuid.UUID) -> List[AIInteraction]:
        """
        Returns all messages in one chat conversation, in
        chronological order (oldest first — natural order
        for reconstructing a chat thread).
        """
        return (
            self.db.query(AIInteraction)
            .filter(AIInteraction.session_id == session_id)
            .order_by(AIInteraction.created_at.asc())
            .all()
        )

    def get_total_tokens_used(
        self,
        user_id: uuid.UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> int:
        """
        Sums tokens_used for a user, optionally within a date
        range. Returns 0 if the user has no interactions
        (or none with tokens_used recorded) in range, rather
        than None, so callers can use the result directly in
        arithmetic without a None-check.
        """
        query = self.db.query(func.sum(AIInteraction.tokens_used)).filter(
            AIInteraction.user_id == user_id
        )

        if start_date is not None:
            query = query.filter(func.date(AIInteraction.created_at) >= start_date)
        if end_date is not None:
            query = query.filter(func.date(AIInteraction.created_at) <= end_date)

        total = query.scalar()
        return total or 0

    def get_token_usage_by_user_and_model(self) -> List[dict]:
        """
        Returns one row per (user, model_used) combination —
        NOT collapsed to one row per user — because different
        models are priced very differently by Anthropic (e.g.
        Haiku 4.5 vs Sonnet 5), so accurate dollar-cost
        calculation needs token sums broken out per model, not
        blended together. The report script (which owns all
        pricing logic — this repository stays pure data
        access) aggregates these rows into a final per-user
        dollar total.

        Uses a LEFT JOIN from users, so a user with ZERO AI
        interactions still appears (with model_used=None and
        all-zero counts) — the report should show every
        registered user, not just active ones.

        Each row: {
            "user_id": uuid.UUID,
            "email": str,
            "user_created_at": datetime,
            "model_used": Optional[str],  # None if this user has no interactions at all
            "total_tokens_used": int,
            "total_input_tokens": int,
            "total_output_tokens": int,
            "interaction_count": int,
            "split_interaction_count": int,  # how many of those interactions have real input/output split data
        }
        """
        rows = (
            self.db.query(
                User.id.label("user_id"),
                User.email.label("email"),
                User.created_at.label("user_created_at"),
                AIInteraction.model_used.label("model_used"),
                func.coalesce(func.sum(AIInteraction.tokens_used), 0).label("total_tokens_used"),
                func.coalesce(func.sum(AIInteraction.input_tokens), 0).label("total_input_tokens"),
                func.coalesce(func.sum(AIInteraction.output_tokens), 0).label("total_output_tokens"),
                func.count(AIInteraction.id).label("interaction_count"),
                func.count(AIInteraction.input_tokens).label("split_interaction_count"),
            )
            .outerjoin(AIInteraction, AIInteraction.user_id == User.id)
            .group_by(User.id, User.email, User.created_at, AIInteraction.model_used)
            .order_by(User.created_at.asc())
            .all()
        )

        return [
            {
                "user_id": row.user_id,
                "email": row.email,
                "user_created_at": row.user_created_at,
                "model_used": row.model_used,
                "total_tokens_used": row.total_tokens_used,
                "total_input_tokens": row.total_input_tokens,
                "total_output_tokens": row.total_output_tokens,
                "interaction_count": row.interaction_count,
                "split_interaction_count": row.split_interaction_count,
            }
            for row in rows
        ]

    # ---------------------------------------------------
    # Create
    # ---------------------------------------------------

    def create(
        self,
        user_id: uuid.UUID,
        interaction_type: InteractionType,
        prompt: str,
        response: str,
        model_used: str,
        session_id: Optional[uuid.UUID] = None,
        tokens_used: Optional[int] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        related_recipe_id: Optional[uuid.UUID] = None,
    ) -> AIInteraction:
        new_interaction = AIInteraction(
            user_id=user_id,
            related_recipe_id=related_recipe_id,
            interaction_type=interaction_type,
            session_id=session_id,
            prompt=prompt,
            response=response,
            model_used=model_used,
            tokens_used=tokens_used,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

        self.db.add(new_interaction)
        self.db.commit()
        self.db.refresh(new_interaction)

        return new_interaction
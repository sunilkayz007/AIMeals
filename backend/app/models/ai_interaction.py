"""
=========================================================
AIMeals Backend
AI Interaction Model

Responsibilities:
    - Define the ai_interactions table schema
    - Define the InteractionType enum

Dependencies:
    - app.B_database.Base
    - app.models.user.User
    - app.models.recipe.Recipe (nullable FK)

Notes:
    - This table merges what were originally two separate
      roadmap items (ChatHistory and AIHistory) into one,
      per project decision. It covers both:
        1. Conversational nutrition-coach chat (session_id
           groups messages into one ongoing conversation)
        2. One-off AI calls (recipe generation, food image
           analysis, etc. — session_id is null for these,
           since they aren't part of a back-and-forth
           conversation)
    - model_used, tokens_used, input_tokens, output_tokens
      exist specifically to support the tier-based cost
      control strategy: they let actual spend be audited per
      user/interaction, and let you verify that Free-tier
      users are actually being routed to the cheaper model as
      intended.
    - input_tokens/output_tokens were added after tokens_used
      already existed in production — they let a per-user
      dollar-cost report be calculated accurately (input and
      output tokens are priced very differently by Anthropic,
      e.g. Haiku 4.5 is $1/M input vs $5/M output, so a single
      combined number can't be converted to a real dollar
      figure). Both are nullable: interactions logged BEFORE
      this column existed will have tokens_used but NOT
      input_tokens/output_tokens — the usage report script
      handles that gap explicitly rather than silently
      treating null as zero.
    - related_recipe_id links back to a Recipe if this
      interaction generated one (e.g. a recipe_generation
      interaction). Nullable + ON DELETE SET NULL: deleting
      a recipe should never delete the interaction history
      that created it.
    - ALLERGEN_DEEP_INSIGHT (added 2026-08-06) backs the
      Allergies screen's paid "Know more" tap-through — see
      AIService.get_allergen_deep_insight() and
      SubscriptionService.INTERACTION_CREDIT_COSTS. Unlike
      every other type here, it's charged at most once per
      (user, allergen) pair — see that method's docstring.
    - HEALTH_REPORT_ANALYSIS (added Aug 2026) backs the
      Health Insights feature ("From Report to Plate") —
      extracting nutrition-relevant markers from an uploaded
      health/medical report. Priced like FOOD_IMAGE_ANALYSIS
      (a similar document/vision-heavy single call) — see
      SubscriptionService.INTERACTION_CREDIT_COSTS.
    - ESTIMATE_MEAL_NUTRITION (added Sep 2026) backs the
      "Estimate with AI" button on the manual meal-log form —
      a single, cheap text-only call estimating nutrition for
      a user-typed food description. See
      AIService.estimate_meal_nutrition() and
      SubscriptionService.INTERACTION_CREDIT_COSTS (priced at
      1 credit, similar weight to CHAT).

Example usage:
    from app.models.ai_interaction import AIInteraction, InteractionType

    interaction = AIInteraction(
        user_id=user.id,
        interaction_type=InteractionType.CHAT,
        prompt="What should I eat for dinner tonight?",
        response="Given your goals, I'd suggest...",
        session_id=chat_session_uuid,
        model_used="claude-sonnet-5",
        tokens_used=450,
        input_tokens=180,
        output_tokens=270,
    )
=========================================================
"""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.B_database import Base


# =========================================================
# Interaction Type Enum
# =========================================================

class InteractionType(str, enum.Enum):
    CHAT = "chat"
    RECIPE_GENERATION = "recipe_generation"
    MEAL_PLAN_GENERATION = "meal_plan_generation"
    FOOD_IMAGE_ANALYSIS = "food_image_analysis"
    PANTRY_SUGGESTION = "pantry_suggestion"
    INGREDIENT_IMAGE_IDENTIFY = "ingredient_image_identify"
    INGREDIENT_PHOTO_RECIPE = "ingredient_photo_recipe"
    ALLERGEN_DEEP_INSIGHT = "allergen_deep_insight"
    HEALTH_REPORT_ANALYSIS = "health_report_analysis"
    ESTIMATE_MEAL_NUTRITION = "estimate_meal_nutrition"


# =========================================================
# AI Interaction Model
# =========================================================

class AIInteraction(Base):
    """
    Represents a single AI call — either one message in an
    ongoing chat conversation, or a one-off AI-powered action.

    Table: ai_interactions
    """

    __tablename__ = "ai_interactions"

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

    related_recipe_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ---------------------------------------------------
    # Interaction Details
    # ---------------------------------------------------

    interaction_type: Mapped[InteractionType] = mapped_column(
        Enum(InteractionType, name="interaction_type"),
        nullable=False,
        index=True,
    )

    # Groups multiple CHAT messages into one ongoing
    # conversation. Null for one-off, non-conversational
    # interactions (recipe generation, image analysis, etc.)
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str] = mapped_column(Text, nullable=False)

    # ---------------------------------------------------
    # Cost Auditing
    # ---------------------------------------------------

    model_used: Mapped[str] = mapped_column(String(100), nullable=False)

    # Combined total, kept for backward compatibility with
    # code/reports written before the input/output split.
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Separate input/output counts — needed for accurate
    # dollar-cost calculation, since Anthropic prices input
    # and output tokens very differently per model. Nullable
    # because rows logged before this column existed won't
    # have these values (only tokens_used).
    input_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # ---------------------------------------------------
    # Timestamps
    # ---------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # ---------------------------------------------------
    # Relationships
    # ---------------------------------------------------

    user = relationship("User")
    related_recipe = relationship("Recipe")

    # ---------------------------------------------------
    # Representation
    # ---------------------------------------------------

    def __repr__(self) -> str:
        return f"<AIInteraction id={self.id} type={self.interaction_type} model={self.model_used}>"

"""
=========================================================
AIMeals Backend
AI Context Builder

Responsibilities:
    - Assemble a compact, deterministic context summary for
      personalizing AI responses: profile/allergies, recent
      conversation history, recent nutrition, saved recipes

Dependencies:
    - app.services.profile_service.ProfileService
    - app.repositories.ai_interaction_repository.AIInteractionRepository
    - app.repositories.nutrition_log_repository.NutritionLogRepository
    - app.repositories.recipe_repository.RecipeRepository

Notes:
    - This builder does NOT call Claude to summarize anything.
      "Summary" here means deterministic, programmatic
      condensing (truncation, averaging, listing titles) —
      not an AI-generated summary. A true AI-generated
      summary would require an extra Claude API call before
      every message, doubling cost and latency. This
      approach achieves the same practical goal (bounded,
      useful context) at zero extra API cost.
    - Conversation history is capped at the last 20
      exchanges even when summarizing "all" prior messages,
      so token cost stays bounded regardless of how long a
      conversation grows.
    - This class makes NO Claude API calls and consumes NO
      AI credits — it's pure data assembly.

Example usage:
    from app.services.ai_context_service import AIContextBuilder

    builder = AIContextBuilder(db)
    context = builder.build_context(user_id, session_id)
=========================================================
"""

import uuid
from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.repositories.ai_interaction_repository import AIInteractionRepository
from app.repositories.coach_memory_repository import CoachMemoryRepository
from app.repositories.nutrition_log_repository import NutritionLogRepository
from app.repositories.recipe_repository import RecipeRepository
from app.services.profile_service import ProfileService

# Hard cap on how many past exchanges get summarized, even
# in "all history" mode — keeps token cost bounded.
MAX_CONVERSATION_EXCHANGES = 20

# How far back to look for the nutrition summary.
NUTRITION_LOOKBACK_DAYS = 7

# Max snippet length for a single prompt/response in the
# conversation summary, to keep each line compact.
SNIPPET_MAX_CHARS = 80

# Max number of saved recipes to list by title.
MAX_RECIPES_LISTED = 10


# =========================================================
# AI Context Builder
# =========================================================

class AIContextBuilder:
    """
    Assembles context for personalizing AI responses.
    Pure data assembly — makes no API calls, consumes no credits.
    """

    def __init__(self, db: Session):
        self.db = db
        self.profile_service = ProfileService(db)
        self.interaction_repo = AIInteractionRepository(db)
        self.log_repo = NutritionLogRepository(db)
        self.recipe_repo = RecipeRepository(db)
        # Added for the Coach Roadmap cross-session memory feature --
        # see _build_persistent_memory_section()'s docstring. Still a
        # plain DB read, so this class's "zero extra API cost"
        # guarantee (see module docstring) is unaffected.
        self.coach_memory_repo = CoachMemoryRepository(db)

    # ---------------------------------------------------
    # Main Entry Point
    # ---------------------------------------------------

    def build_context(
        self,
        user_id: uuid.UUID,
        session_id: Optional[uuid.UUID] = None,
    ) -> str:
        """
        Returns a formatted context block combining profile,
        conversation history (if session_id is given),
        recent nutrition, and saved recipes.

        Returns an empty string if the user has none of this
        data yet (e.g. a brand new user) — callers should
        handle an empty context gracefully rather than
        assuming it's always populated.
        """
        sections = [
            self._build_profile_section(user_id),
            self._build_persistent_memory_section(user_id),
            self._build_conversation_section(session_id) if session_id else "",
            self._build_nutrition_section(user_id),
            self._build_recipes_section(user_id),
        ]

        non_empty_sections = [s for s in sections if s]

        if not non_empty_sections:
            return ""

        return (
            "USER CONTEXT (for personalizing your response — "
            "do not repeat this block back to the user verbatim):\n\n"
            + "\n\n".join(non_empty_sections)
        )

    def build_profile_context(self, user_id: uuid.UUID) -> str:
        """
        Returns JUST the profile/allergy/restriction section,
        without conversation history, nutrition, or recipes.
        Used by non-chat features (e.g. recipe generation)
        that need to know a user's allergies and restrictions
        but don't need the full chat-oriented context block.
        """
        section = self._build_profile_section(user_id)

        if not section:
            return ""

        return (
            "USER CONTEXT (for personalizing your response — "
            "do not repeat this block back to the user verbatim):\n\n"
            + section
        )

    # ---------------------------------------------------
    # Profile Section
    # ---------------------------------------------------

    def _build_profile_section(self, user_id: uuid.UUID) -> str:
        full_profile = self.profile_service.get_full_dietary_profile(user_id)
        profile = full_profile["profile"]
        allergies = full_profile["allergies"]
        restrictions = full_profile["dietary_restrictions"]

        if profile is None and not allergies and not restrictions:
            return ""

        lines = ["Profile:"]

        if profile is not None:
            details = []
            if profile.goal:
                details.append(f"Goal: {profile.goal.value}")
            if profile.activity_level:
                details.append(f"Activity: {profile.activity_level.value}")
            if profile.height_cm:
                details.append(f"Height: {profile.height_cm}cm")
            if profile.weight_kg:
                details.append(f"Weight: {profile.weight_kg}kg")
            if details:
                lines.append("- " + " | ".join(details))

        if allergies:
            allergy_strs = [
                f"{link.allergy.name} ({link.severity.value})" for link in allergies
            ]
            lines.append("- Allergies: " + ", ".join(allergy_strs))

        if restrictions:
            restriction_strs = [link.restriction.name for link in restrictions]
            lines.append("- Dietary restrictions: " + ", ".join(restriction_strs))

        return "\n".join(lines)

    # ---------------------------------------------------
    # Persistent Coach Memory Section (cross-session)
    # ---------------------------------------------------

    def _build_persistent_memory_section(self, user_id: uuid.UUID) -> str:
        """
        Surfaces durable dietary-preference/goal facts extracted
        from PAST conversations (possibly different sessions
        entirely) -- see AIService._extract_and_store_coach_memory()
        for how these get written. Distinct from
        _build_conversation_section() below, which only covers THIS
        session's own recent exchanges.

        Pure DB read, same as every other section here -- no Claude
        call, no extra cost.
        """
        facts = self.coach_memory_repo.get_recent(user_id, limit=15)

        if not facts:
            return ""

        lines = ["Remembered from past conversations (dietary preferences/goals):"]
        for fact in facts:
            lines.append(f"- {fact.fact}")

        return "\n".join(lines)

    # ---------------------------------------------------
    # Conversation History Section
    # ---------------------------------------------------

    def _build_conversation_section(self, session_id: uuid.UUID) -> str:
        exchanges = self.interaction_repo.get_by_session(session_id)

        if not exchanges:
            return ""

        # Cap even in "summary" mode, to bound token cost
        # regardless of how long the conversation has grown.
        recent_exchanges = exchanges[-MAX_CONVERSATION_EXCHANGES:]

        lines = ["Conversation so far (summary):"]
        for exchange in recent_exchanges:
            prompt_snippet = self._truncate(exchange.prompt)
            response_snippet = self._truncate(exchange.response)
            lines.append(f"- User asked: \"{prompt_snippet}\" — You replied: \"{response_snippet}\"")

        return "\n".join(lines)

    # ---------------------------------------------------
    # Recent Nutrition Section
    # ---------------------------------------------------

    def _build_nutrition_section(self, user_id: uuid.UUID) -> str:
        end_date = date.today()
        start_date = end_date - timedelta(days=NUTRITION_LOOKBACK_DAYS)

        logs = self.log_repo.get_by_user(user_id, start_date=start_date, end_date=end_date)

        if not logs:
            return ""

        num_days_with_logs = len({log.logged_at for log in logs})
        avg_calories = sum(log.calories for log in logs) / num_days_with_logs
        avg_protein = sum(log.protein_g for log in logs) / num_days_with_logs

        return (
            f"Recent nutrition (last {NUTRITION_LOOKBACK_DAYS} days): "
            f"{len(logs)} meals logged across {num_days_with_logs} day(s), "
            f"averaging {avg_calories:.0f} calories and {avg_protein:.0f}g protein per logged day."
        )

    # ---------------------------------------------------
    # Saved Recipes Section
    # ---------------------------------------------------

    def _build_recipes_section(self, user_id: uuid.UUID) -> str:
        recipes = self.recipe_repo.get_by_user(user_id)

        if not recipes:
            return ""

        titles = [recipe.title for recipe in recipes[:MAX_RECIPES_LISTED]]
        more_note = (
            f" (and {len(recipes) - MAX_RECIPES_LISTED} more)"
            if len(recipes) > MAX_RECIPES_LISTED
            else ""
        )

        return "Saved recipes: " + ", ".join(titles) + more_note

    # ---------------------------------------------------
    # Internal Helper
    # ---------------------------------------------------

    def _truncate(self, text: str) -> str:
        if len(text) <= SNIPPET_MAX_CHARS:
            return text
        return text[:SNIPPET_MAX_CHARS].rstrip() + "..."
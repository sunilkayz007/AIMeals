"""
=========================================================
AIMeals Backend
Micronutrient Helpers

Responsibilities:
    - Define the canonical set of 10 tracked micronutrient
      keys (matches app.core.rda's target keys exactly)
    - Provide shared scale/sum/sanitize helpers used by both
      NutritionLogService (portion scaling, daily totals) and
      AIService (parsing Claude's per-item estimates, summing
      a food image's per-item breakdown into a total)

Dependencies:
    - None (pure calculation, no database access)

Notes:
    - A single JSONB "micronutrients" column holds all 10
      values together on NutritionLog, Recipe, and FoodImage
      — deliberately NOT 10 separate float columns like Fiber
      got. That approach cost a full day of migrations/schema/
      repository/service/prompt changes for ONE nutrient, with
      several hidden copy-paste bugs along the way. A JSONB
      dict scales to all 10 (and any future addition) with
      zero new migrations — only this module and the AI
      prompts need to know the key list.
    - Every function here is defensive about missing/None/
      malformed input, since the dict ultimately comes from
      either a Claude response (never trusted blindly) or a
      nullable database column (a manual log entry may have
      no micronutrient data at all).

Example usage:
    from app.core.micronutrients import (
        MICRONUTRIENT_KEYS,
        empty_micronutrients,
        sanitize_micronutrients,
        scale_micronutrients,
        sum_micronutrients,
    )

    scaled = scale_micronutrients(recipe.micronutrients, 0.5)
=========================================================
"""

from typing import Any, Iterable, Optional


# Canonical key list — MUST match app.core.rda's NutrientTarget keys
# exactly, since the frontend pairs a target (from /rda-targets) with
# a consumed value (from this module's summed totals) using the same
# key names.
MICRONUTRIENT_KEYS = [
    "sodium_mg",
    "potassium_mg",
    "calcium_mg",
    "iron_mg",
    "magnesium_mg",
    "zinc_mg",
    "vitamin_a_mcg",
    "vitamin_b12_mcg",
    "vitamin_c_mg",
    "vitamin_d_mcg",
]


def empty_micronutrients() -> dict[str, float]:
    """Returns a dict with all 10 keys present, each 0.0."""
    return {key: 0.0 for key in MICRONUTRIENT_KEYS}


def sanitize_micronutrients(raw: Optional[dict[str, Any]]) -> dict[str, float]:
    """
    Defensively casts a raw dict (e.g. straight from a Claude JSON
    response) into a clean {key: float} dict with all 10 canonical
    keys present. Missing keys, None values, or non-numeric values
    all default to 0.0 — this is model-generated or possibly-absent
    data, never trusted blindly into arithmetic.

    Unknown keys in `raw` are silently dropped (not an error) — a
    stray extra key from a model response shouldn't fail the whole
    parse.
    """
    if not raw:
        return empty_micronutrients()

    result: dict[str, float] = {}
    for key in MICRONUTRIENT_KEYS:
        value = raw.get(key)
        try:
            result[key] = float(value) if value is not None else 0.0
        except (TypeError, ValueError):
            result[key] = 0.0
    return result


def scale_micronutrients(raw: Optional[dict[str, Any]], scale: float) -> dict[str, float]:
    """
    Sanitizes and scales every value by `scale` (e.g. a recipe's
    per-serving micronutrients scaled by portion_percentage / 100.0,
    same pattern as calories/protein_g/fiber_g elsewhere in
    NutritionLogService).
    """
    sanitized = sanitize_micronutrients(raw)
    return {key: value * scale for key, value in sanitized.items()}


def sum_micronutrients(dicts: Iterable[Optional[dict[str, Any]]]) -> dict[str, float]:
    """
    Sums a list of (possibly None/malformed) micronutrient dicts
    into one totals dict with all 10 keys present. Used both for
    a single food image's per-item breakdown (analyze_food_image)
    and a day's worth of logged meals (get_daily_totals) — same
    "always returns real zeros, never missing keys" guarantee the
    rest of this app's totals already follow.
    """
    total = empty_micronutrients()
    for raw in dicts:
        sanitized = sanitize_micronutrients(raw)
        for key in MICRONUTRIENT_KEYS:
            total[key] += sanitized[key]
    return total

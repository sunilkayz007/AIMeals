"""
=========================================================
AIMeals Backend
RDA (Recommended Dietary Allowance) Calculator

Responsibilities:
    - Compute personalized daily nutrient targets for the
      10 key vitamins/minerals (plus protein, which already
      has its own manual-target path elsewhere) from a
      user's age, gender, and weight.

Dependencies:
    - None (pure calculation, no database access)

Notes:
    - Reference values are drawn from published general adult
      RDA/AI (Adequate Intake) tables (US NIH Office of
      Dietary Supplements style figures). These are POPULATION
      AVERAGES for a general healthy adult — not a personalized
      medical assessment, and not adjusted for pregnancy,
      lactation, or any diagnosed condition. The frontend must
      display the one-line disclaimer alongside these values —
      see AIMeals mobile Home screen's micronutrient section.
    - Age bands used: 19-50, 51+ (a simplified two-band split —
      real RDA tables have finer bands like 51-70 / 70+, but
      the values are close enough across those splits that a
      two-band simplification is a reasonable approximation
      for a general wellness app, not a clinical tool). Ages
      under 19 fall back to the 19-50 band figures rather than
      extrapolating a separate adolescent table, since this
      app's primary audience is adults (see body-details
      screen's age roller, MIN_AGE=10 — a real child/adolescent
      table is a genuine gap if this app is ever used by
      younger teens, flagged here rather than silently guessed).
    - Sodium is a LIMIT (stay under), not a goal (reach it) —
      unlike every other nutrient here. See NutrientTarget.kind.
    - iron_mg is the largest male/female gap of any mineral
      here (menstrual iron loss) — deliberately NOT reduced
      for a "prefer_not_to_say"/"other" gender selection; those
      selections fall back to the female (higher) figure so
      the app never under-targets someone who may need the
      higher amount. This is a conservative default, not an
      assumption about the person's sex.

Example usage:
    from app.core.rda import compute_rda_targets

    targets = compute_rda_targets(age=34, gender="male", weight_kg=78)
    targets["iron_mg"].amount  # -> 8.0
=========================================================
"""

from dataclasses import dataclass
from typing import Literal, Optional


# =========================================================
# Nutrient Target Value Object
# =========================================================

@dataclass(frozen=True)
class NutrientTarget:
    """
    One computed nutrient target.

    kind:
        "goal"  -> more is better, up to this amount (the
                   normal case — protein, fiber, vitamins,
                   most minerals).
        "limit" -> less is better; this amount is a MAXIMUM
                   to stay under, not a minimum to reach
                   (currently only sodium). The frontend's
                   ring color logic must treat "limit" nutrients
                   with the opposite convention from "goal"
                   ones — see home.tsx's existing water-ring
                   reversed-color precedent for the same idea.
    """

    amount: float
    unit: str
    kind: Literal["goal", "limit"]


GenderInput = Literal["male", "female", "other", "prefer_not_to_say"]


# =========================================================
# Reference Tables (general healthy adult, ages 19-50 / 51+)
# =========================================================
# Structure: { nutrient_key: {"male": {...}, "female": {...}} }
# "female" values are also used as the fallback for
# "other"/"prefer_not_to_say" — see module docstring's note
# on iron_mg for why the higher figure is the safer default.

_ADULT_19_50 = {
    "sodium_mg": {"male": (1500, "limit"), "female": (1500, "limit")},
    "potassium_mg": {"male": (3400, "goal"), "female": (2600, "goal")},
    "calcium_mg": {"male": (1000, "goal"), "female": (1000, "goal")},
    "iron_mg": {"male": (8, "goal"), "female": (18, "goal")},
    "magnesium_mg": {"male": (400, "goal"), "female": (310, "goal")},
    "zinc_mg": {"male": (11, "goal"), "female": (8, "goal")},
    "vitamin_a_mcg": {"male": (900, "goal"), "female": (700, "goal")},
    "vitamin_b12_mcg": {"male": (2.4, "goal"), "female": (2.4, "goal")},
    "vitamin_c_mg": {"male": (90, "goal"), "female": (75, "goal")},
    "vitamin_d_mcg": {"male": (15, "goal"), "female": (15, "goal")},
}

_ADULT_51_PLUS = {
    "sodium_mg": {"male": (1500, "limit"), "female": (1500, "limit")},
    "potassium_mg": {"male": (3400, "goal"), "female": (2600, "goal")},
    "calcium_mg": {"male": (1000, "goal"), "female": (1200, "goal")},
    "iron_mg": {"male": (8, "goal"), "female": (8, "goal")},
    "magnesium_mg": {"male": (420, "goal"), "female": (320, "goal")},
    "zinc_mg": {"male": (11, "goal"), "female": (8, "goal")},
    "vitamin_a_mcg": {"male": (900, "goal"), "female": (700, "goal")},
    "vitamin_b12_mcg": {"male": (2.4, "goal"), "female": (2.4, "goal")},
    "vitamin_c_mg": {"male": (90, "goal"), "female": (75, "goal")},
    "vitamin_d_mcg": {"male": (20, "goal"), "female": (20, "goal")},
}

_UNITS = {
    "sodium_mg": "mg",
    "potassium_mg": "mg",
    "calcium_mg": "mg",
    "iron_mg": "mg",
    "magnesium_mg": "mg",
    "zinc_mg": "mg",
    "vitamin_a_mcg": "mcg",
    "vitamin_b12_mcg": "mcg",
    "vitamin_c_mg": "mg",
    "vitamin_d_mcg": "mcg",
}


# =========================================================
# Public API
# =========================================================

def compute_rda_targets(
    age: int,
    gender: Optional[GenderInput],
    weight_kg: Optional[float] = None,
) -> dict[str, NutrientTarget]:
    """
    Returns a dict of nutrient_key -> NutrientTarget for all
    10 supported minerals/vitamins, personalized by age and
    gender.

    weight_kg is accepted (not currently used to scale any of
    these 10 nutrients — the reference tables here are not
    weight-scaled in standard RDA guidance) but kept as a
    parameter for forward compatibility, since a future
    nutrient (e.g. a weight-scaled protein target) may need
    it — see the docstring on why protein itself isn't
    included in this module: it already has its own
    manually-settable target path (Profile.protein_g_target),
    separate from this auto-computed RDA set.

    gender values "other" and "prefer_not_to_say" use the
    female reference values — see module docstring.
    """
    table = _ADULT_19_50 if age < 51 else _ADULT_51_PLUS

    lookup_gender = "male" if gender == "male" else "female"

    targets: dict[str, NutrientTarget] = {}
    for nutrient_key, by_gender in table.items():
        amount, kind = by_gender[lookup_gender]
        targets[nutrient_key] = NutrientTarget(
            amount=float(amount),
            unit=_UNITS[nutrient_key],
            kind=kind,
        )

    return targets
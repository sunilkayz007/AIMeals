"""
=========================================================
AIMeals Backend
Core Exceptions

Responsibilities:
    - Define custom exceptions used across the service layer

Notes:
    - These exceptions are deliberately framework-agnostic.
      They know nothing about HTTP status codes. Translation
      from exception -> HTTP response happens in the
      controller/API layer, not here.
=========================================================
"""


# =========================================================
# Auth Exceptions
# =========================================================

class EmailAlreadyExistsError(Exception):
    """Raised when attempting to register an email that is already in use."""
    pass


class InvalidCredentialsError(Exception):
    """Raised when login email/password do not match any active account."""
    pass


class AccountDisabledError(Exception):
    """Raised when a valid login belongs to a deactivated account."""
    pass


class InvalidTokenError(Exception):
    """Raised when a JWT or refresh token is invalid, expired, or revoked."""
    pass


# =========================================================
# Profile Exceptions
# =========================================================

class DuplicateAllergyError(Exception):
    """Raised when attempting to link an allergy a user already has linked."""
    pass


class DuplicateRestrictionError(Exception):
    """Raised when attempting to link a dietary restriction a user already has linked."""
    pass


# =========================================================
# Subscription / AI Credit Exceptions
# =========================================================

class InsufficientCreditsError(Exception):
    """Raised when a user has no remaining AI credits this billing period."""
    pass


# =========================================================
# Recipe Exceptions
# =========================================================

class RecipeNotFoundError(Exception):
    """Raised when a recipe lookup by id finds nothing."""
    pass


class NotRecipeOwnerError(Exception):
    """Raised when a user attempts to edit/delete a recipe they don't own (including system recipes)."""
    pass


# =========================================================
# Nutrition Log Exceptions
# =========================================================

class NutritionLogNotFoundError(Exception):
    """Raised when a nutrition log lookup by id finds nothing."""
    pass


class NotLogOwnerError(Exception):
    """Raised when a user attempts to edit/delete a nutrition log they don't own."""
    pass


# =========================================================
# Meal Plan Exceptions
# =========================================================

class MealPlanNotFoundError(Exception):
    """Raised when a meal plan lookup by id finds nothing."""
    pass


class NotMealPlanOwnerError(Exception):
    """Raised when a user attempts to access/edit/delete a meal plan (or its meals) they don't own."""
    pass


# =========================================================
# Pantry Exceptions
# =========================================================

class PantryItemNotFoundError(Exception):
    """Raised when a pantry item lookup by id finds nothing."""
    pass


class NotPantryItemOwnerError(Exception):
    """Raised when a user attempts to edit/delete a pantry item they don't own."""
    pass


# =========================================================
# Progress Entry Exceptions
# =========================================================

class ProgressEntryNotFoundError(Exception):
    """Raised when a progress entry lookup by id finds nothing."""
    pass


class NotProgressEntryOwnerError(Exception):
    """Raised when a user attempts to edit/delete a progress entry they don't own."""
    pass


class DuplicateProgressEntryError(Exception):
    """Raised when attempting to log a second progress entry for a date the user already logged."""
    pass


# =========================================================
# Ingredient Scan Exceptions
# =========================================================

class IngredientScanNotFoundError(Exception):
    """Raised when an ingredient scan lookup by id finds nothing (including if it was already cleaned up by the TTL script)."""
    pass


class NotIngredientScanOwnerError(Exception):
    """Raised when a user attempts to access/confirm an ingredient scan they don't own."""
    pass


# =========================================================
# Food Image Exceptions
# =========================================================

class FoodImageNotFoundError(Exception):
    """Raised when a food image analysis lookup by id finds nothing."""
    pass


class NotFoodImageOwnerError(Exception):
    """Raised when a user attempts to access/resolve a food image analysis they don't own."""
    pass


class FoodImageNotConfirmedError(Exception):
    """
    Raised when attempting to log a nutrition entry from a
    FoodImage that's still PENDING (has unresolved ambiguous
    items). The totals aren't final until the user resolves
    every ambiguity via the existing free resolve endpoint —
    logging from an unresolved scan would record numbers that
    might be wrong.
    """
    pass


class InappropriateImageError(Exception):
    """
    Raised when Claude declines to analyze an uploaded image
    because it isn't food, or is inappropriate/harmful/unsafe.
    Distinct from FoodImageAnalysisError: this is a designed,
    intentional refusal signal from Claude (see the
    _FOOD_IMAGE_ANALYSIS_SYSTEM_PROMPT's REFUSAL instruction),
    not a parsing failure. No FoodImage row is created. NOT
    refunded — a real API cost was already incurred to receive
    this refusal.
    """
    pass


# =========================================================
# Health Report Exceptions
# =========================================================

class HealthReportNotFoundError(Exception):
    """Raised when a health report lookup by id finds nothing."""
    pass


class NotHealthReportOwnerError(Exception):
    """Raised when a user attempts to access/confirm/delete a health report they don't own."""
    pass


class UnrecognizedReportError(Exception):
    """
    Raised when Claude declines to extract data because the
    uploaded document doesn't appear to be a health/medical
    report at all. Mirrors InappropriateImageError's
    reasoning: a designed, intentional refusal signal from
    Claude (see _HEALTH_REPORT_EXTRACTION_SYSTEM_PROMPT's
    REFUSAL instruction), not a parsing failure. No
    HealthReport row is created. NOT refunded — a real API
    cost was already incurred to receive this refusal.
    """
    pass


class HealthReportAnalysisError(Exception):
    """
    Raised when Claude's response for a health report
    extraction call can't be parsed into valid structured
    markers. Same reasoning as FoodImageAnalysisError: the
    API call itself succeeded, so this is NOT refunded. No
    HealthReport row is created for this call.
    """
    pass


# =========================================================
# Meal Nutrition Estimate Exceptions
# =========================================================

class MealNutritionEstimateError(Exception):
    """
    Raised when Claude's response for the manual-meal-log
    "Estimate with AI" call can't be parsed into a valid
    nutrition estimate. Same reasoning as
    FoodImageAnalysisError/RecipeGenerationError: the API
    call itself succeeded, so this is NOT refunded. Nothing
    is created for this call (it never persists a row of its
    own — see AIService.estimate_meal_nutrition()'s
    docstring, the returned estimate is only used to pre-fill
    the manual-entry form, which the user still explicitly
    submits themselves).
    """
    pass


# =========================================================
# Upload Exceptions
# =========================================================

class UploadTooLargeError(Exception):
    """Raised when an uploaded file exceeds settings.MAX_UPLOAD_SIZE_MB. Checked BEFORE any credit is spent."""
    pass


class UnsupportedImageFormatError(Exception):
    """
    Raised when an uploaded image's media_type isn't one Claude's
    vision API accepts (image/jpeg, image/png, image/gif,
    image/webp) -- most commonly a HEIC/HEIF photo straight off an
    iPhone whose Camera format setting is "High Efficiency". Checked
    BEFORE any credit is spent, same as UploadTooLargeError. Without
    this check, the request reached Claude and failed there instead
    with an opaque anthropic.BadRequestError, refunding the credit
    but showing the user a raw API error message.
    """
    pass


# =========================================================
# Claude API Exceptions
# =========================================================

class ClaudeAPIError(Exception):
    """Raised when a call to the Claude API fails (network error, rate limit, API outage, etc.)."""
    pass


class RecipeGenerationError(Exception):
    """
    Raised when Claude's response for a recipe generation
    request can't be parsed into a valid recipe. Distinct
    from ClaudeAPIError: the API call itself succeeded (a
    real cost was incurred), Claude just didn't return
    usable structured output — so this is NOT refunded,
    same as any other post-success failure.
    """
    pass


class IngredientIdentificationError(Exception):
    """
    Raised when Claude's response for an ingredient photo
    identification call can't be parsed into a valid
    ingredient list. Same reasoning as RecipeGenerationError:
    the API call itself succeeded, so this is NOT refunded.
    """
    pass


class FoodImageAnalysisError(Exception):
    """
    Raised when Claude's response for a food image analysis
    call can't be parsed into a valid nutrition estimate.
    Same reasoning as RecipeGenerationError: the API call
    itself succeeded, so this is NOT refunded. No FoodImage
    row is created for this call (nothing to leave in a
    partial state — this project no longer stores images or
    creates an "uploading" placeholder row at all).
    """
    pass


class AllergenDetectedError(Exception):
    """
    Raised when a generated recipe contains an ingredient
    matching one of the user's known allergies, despite the
    prompt instructing Claude to avoid it. This is a
    deterministic, code-level safety check — it does not
    trust the model's compliance. Not refunded (a real API
    cost was incurred).

    UPDATED (fail-open-with-confirmation design): this
    exception now optionally carries a preview of the
    generated recipe and the specific allergens that were
    flagged. When confirm_allergen_override was NOT set on
    the request, recipe_preview/flagged_allergens are
    populated so the caller (the SSE route layer) can surface
    a "generate anyway?" choice to the user WITHOUT having
    saved anything yet. When confirm_allergen_override WAS
    set and this still gets raised (e.g. the semantic
    verification API call itself failed — a genuine system
    error, not a confirmable "this dish contains X" case),
    recipe_preview stays None: there's nothing safe to offer
    a preview of, and this remains a hard failure.

    sse_extra_data is read generically by
    app.core.sse_streaming.stream_ai_progress() and merged
    into the SSE error event's data payload — see that
    module's docstring. This keeps sse_streaming.py itself
    fully generic (it doesn't know anything about recipes or
    allergens); only this exception class knows what extra
    data is meaningful to attach.
    """

    def __init__(
        self,
        message: str,
        recipe_preview: dict | None = None,
        flagged_allergens: list[str] | None = None,
    ):
        super().__init__(message)
        self.recipe_preview = recipe_preview
        self.flagged_allergens = flagged_allergens or []

    @property
    def sse_extra_data(self) -> dict | None:
        """
        Returns the extra fields stream_ai_progress() should
        merge into the SSE error event, or None if this
        instance has no preview to offer (the hard-failure
        case described in the class docstring above).
        """
        if self.recipe_preview is None:
            return None
        return {
            "recipe_preview": self.recipe_preview,
            "flagged_allergens": self.flagged_allergens,
        }

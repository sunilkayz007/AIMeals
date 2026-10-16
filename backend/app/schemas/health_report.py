"""
=========================================================
AIMeals Backend
Health Report Schemas

Responsibilities:
    - Define request/response shapes for health report data

Dependencies:
    - app.models.health_report (HealthReportStatus)

Notes:
    - HealthMarkerOut mirrors FoodItemOut's shape/philosophy
      (see app.schemas.food_image): a small, defensively-typed
      per-entry shape, all numeric/optional fields safe to
      cast, matching how model-generated data is never trusted
      blindly elsewhere in this app.
    - reference_range is split into reference_range_min/max
      (for any future range-based UI logic, e.g. highlighting
      "below range") plus reference_range_text (the plain
      display string, since real lab reports don't always give
      a clean numeric range).
    - range_status is a COMPUTED field (a Pydantic model
      validator, not stored in the database) -- purely a
      factual comparison of value against
      reference_range_min/max ("below"/"within"/"above"),
      never a diagnostic judgment. This is deliberately NOT
      an AI-generated field -- it's plain Python arithmetic,
      computed fresh every time this schema serializes a
      marker, so it can never drift from the underlying
      numbers. Safety boundary: this field must NEVER contain
      a disease/condition name (no "prediabetic", "deficient",
      etc.) -- only the neutral below/within/above/unknown
      relationship to the report's own printed range.
    - HealthPriorityOut / nutrition_priorities on
      HealthReportOut back the Nutrition Focus Engine's
      output (Phase 6) -- see AIService.confirm_health_report()
      and _NUTRITION_FOCUS_SYSTEM_PROMPT. Also strictly
      non-diagnostic by construction -- see that prompt's own
      safety rules.

Example usage:
    from app.schemas.health_report import HealthReportOut

    def get_report(report: HealthReport) -> HealthReportOut:
        ...
=========================================================
"""

import uuid
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, model_validator

from app.models.health_report import HealthReportStatus


# =========================================================
# Response Schema — One Extracted Marker
# =========================================================

class HealthMarkerOut(BaseModel):
    """
    One nutrition-relevant marker extracted from a health
    report (e.g. "Vitamin D: 11.8 ng/ml"). Deliberately does
    NOT include any AI-generated diagnostic/interpretive
    field — range_status below is the one exception, and it
    is computed by plain arithmetic in this schema, not by
    the AI extraction step. See module docstring.
    """

    name: str
    value: float
    unit: Optional[str] = None
    reference_range_text: Optional[str] = None
    reference_range_min: Optional[float] = None
    reference_range_max: Optional[float] = None
    source_page: Optional[int] = None
    confidence: Optional[float] = None

    # Computed, not stored — see module docstring.
    range_status: Optional[Literal["below", "within", "above"]] = None

    @model_validator(mode="after")
    def _compute_range_status(self) -> "HealthMarkerOut":
        if self.reference_range_min is not None and self.value < self.reference_range_min:
            self.range_status = "below"
        elif self.reference_range_max is not None and self.value > self.reference_range_max:
            self.range_status = "above"
        elif self.reference_range_min is not None or self.reference_range_max is not None:
            self.range_status = "within"
        else:
            self.range_status = None
        return self


# =========================================================
# Response Schema — One Nutrition Priority
# =========================================================

class HealthPriorityOut(BaseModel):
    """
    One nutrition priority produced by the Nutrition Focus
    Engine (Phase 6) from a user's CONFIRMED markers. Strictly
    non-diagnostic by construction — see
    AIService._NUTRITION_FOCUS_SYSTEM_PROMPT's safety rules.
    guidance_type is "increase" (eat more of something),
    "limit" (eat less of something), or "prioritize" (favor
    an eating pattern) — never a treatment instruction.
    """

    key: str
    title: str
    priority: Literal["high", "medium", "low"]
    guidance_type: Literal["increase", "limit", "prioritize"]
    description: str
    action_items: List[str] = []
    foods_to_explore: List[str] = []


# =========================================================
# Response Schema — One Marker's Trend vs the Previous Report
# =========================================================

class MarkerTrendOut(BaseModel):
    """
    Compares a marker's value in THIS confirmed report against
    the same-named marker in the user's previous CONFIRMED
    report — see AIService._compute_marker_trends(). Purely
    arithmetic (distance from the report's own printed
    reference range, before vs after), never a diagnostic
    judgment — matches range_status's own safety philosophy.

    Computed on-the-fly every time a report is fetched/
    confirmed (never stored in the database), by comparing
    against whichever report is currently the "previous"
    CONFIRMED one at read time — see
    AIService._get_owned_health_report_or_raise() callers for
    where this gets attached.
    """

    name: str
    previous_value: float
    current_value: float
    unit: Optional[str] = None
    direction: Literal["improving", "worsening", "stable"]


# =========================================================
# Response Schema — Health Report
# =========================================================

class HealthReportOut(BaseModel):
    """
    Shape of health report data returned to the client.

    confirmed_markers is null until the user has explicitly
    confirmed (Phase 5) — the client should treat a null value
    here as "still awaiting your review," not missing data.
    nutrition_priorities is null until confirmation triggers
    the Nutrition Focus Engine (Phase 6) — same "not yet
    computed" meaning, not missing data. marker_trends is null
    when there's no previous CONFIRMED report to compare
    against (e.g. this is the user's first-ever report), or
    when this report itself isn't CONFIRMED yet.
    """

    id: uuid.UUID
    user_id: uuid.UUID
    report_label: Optional[str] = None
    status: HealthReportStatus
    extracted_markers: List[HealthMarkerOut]
    confirmed_markers: Optional[List[HealthMarkerOut]] = None
    nutrition_priorities: Optional[List[HealthPriorityOut]] = None
    marker_trends: Optional[List[MarkerTrendOut]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =========================================================
# Request Schema — Confirm Health Report
# =========================================================

class HealthReportConfirmRequest(BaseModel):
    """
    Shape of the payload accepted by
    POST /health-reports/{id}/confirm.

    markers is the user-reviewed list — may differ from
    extracted_markers if the user edited, removed, or added
    entries during review (Phase 5). range_status is ignored
    on input (it's always recomputed, never trusted from the
    client) — only name/value/unit/reference_range/source_page/
    confidence are meaningful here.
    """

    markers: List[HealthMarkerOut]
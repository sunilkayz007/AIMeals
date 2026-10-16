"""
=========================================================
AIMeals Backend
Achievement Schema

Responsibilities:
    - Define the response shape for GET /api/v1/achievements

Example usage:
    from app.schemas.achievement import AchievementOut, AchievementListOut
=========================================================
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class AchievementOut(BaseModel):
    key: str
    title: str
    description: str
    icon: str
    earned: bool
    earned_at: Optional[datetime] = None
    # True only on the fetch immediately after being newly earned
    # (i.e. it hadn't been marked seen yet before this request) —
    # lets the client show a one-time "New!" indicator without a
    # separate notifications endpoint.
    is_new: bool = False


class AchievementListOut(BaseModel):
    achievements: List[AchievementOut]

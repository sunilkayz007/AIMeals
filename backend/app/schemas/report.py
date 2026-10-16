"""
=========================================================
AIMeals Backend
Report Schemas

Responsibilities:
    - Define Pydantic request/response shapes for the
      reports API

Dependencies:
    - app.models.report.ReportCategory / ReportStatus
=========================================================
"""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.report import ReportCategory, ReportStatus


# =========================================================
# Requests
# =========================================================

class ReportCreate(BaseModel):
    category: ReportCategory
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)


class ReportCommentCreate(BaseModel):
    comment_text: str = Field(min_length=1)


class ReportStatusUpdate(BaseModel):
    status: ReportStatus


# =========================================================
# Responses
# =========================================================

class ReportCommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    report_id: uuid.UUID
    author_user_id: uuid.UUID
    author_email: str
    is_admin_reply: bool
    comment_text: str
    created_at: datetime


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    user_email: str
    category: ReportCategory
    title: str
    description: str
    status: ReportStatus
    created_at: datetime
    updated_at: datetime


class ReportDetailOut(ReportOut):
    comments: List[ReportCommentOut] = []
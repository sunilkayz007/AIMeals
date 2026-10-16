"""
=========================================================
AIMeals Backend
User Schemas

Responsibilities:
    - Define request/response shapes for user data
    - Enforce password strength on registration
    - Ensure hashed_password is never exposed in responses

Dependencies:
    - app.models.user.UserRole

Example usage:
    from app.schemas.user import UserCreate, UserOut

    def register(payload: UserCreate):
        ...
=========================================================
"""

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.models.user import UserRole


# =========================================================
# Request Schema — Registration
# =========================================================

class UserCreate(BaseModel):
    """
    Shape of the payload accepted by POST /register.

    Password is plaintext here — it is hashed in the
    service layer and never stored or returned as-is.
    """

    email: EmailStr
    password: str
    first_name: str
    last_name: str

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        """
        Enforces minimum password strength:
            - At least 8 characters
            - At least one uppercase letter
            - At least one lowercase letter
            - At least one digit
        """
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if not re.search(r"[A-Z]", value):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not re.search(r"[a-z]", value):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not re.search(r"\d", value):
            raise ValueError("Password must contain at least one digit.")
        return value

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name_not_blank(cls, value: str) -> str:
        """
        Ensures names are not empty or whitespace-only.
        """
        if not value.strip():
            raise ValueError("Name fields cannot be blank.")
        return value.strip()


# =========================================================
# Response Schema — Public User Representation
# =========================================================

class UserOut(BaseModel):
    """
    Shape of user data returned to the client.

    Deliberately excludes hashed_password and updated_at —
    these are internal fields and never sent to the client.
    """

    id: uuid.UUID
    email: EmailStr
    first_name: str
    last_name: str
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
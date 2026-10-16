"""
=========================================================
AIMeals Backend
Email Verification (OTP Signup) Schemas

Responsibilities:
    - Define request shapes for the two-step OTP signup flow

Notes:
    - Kept as its own file rather than added to
      app/schemas/auth.py, since this session never had that
      file's contents to safely extend blindly.
    - VerifySignupOTP's password validator is a deliberate
      exact mirror of UserCreate.validate_password_strength
      in app/schemas/user.py — same rules, so the frontend's
      existing password-strength UI (built against that
      validator) stays accurate without changes.

Example usage:
    from app.schemas.email_verification import RequestSignupOTP, VerifySignupOTP
=========================================================
"""

import re

from pydantic import BaseModel, EmailStr, field_validator


# =========================================================
# Request Schema — Step 1: Request OTP
# =========================================================

class RequestSignupOTP(BaseModel):
    """
    Shape of the payload accepted by
    POST /auth/register/request-otp.

    No password here — collected in step 2 (VerifySignupOTP)
    only after the email is proven to be real.
    """

    email: EmailStr
    first_name: str
    last_name: str

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Name fields cannot be blank.")
        return value.strip()


# =========================================================
# Request Schema — Step 2: Verify OTP + Set Password
# =========================================================

class VerifySignupOTP(BaseModel):
    """
    Shape of the payload accepted by
    POST /auth/register/verify-otp.
    """

    email: EmailStr
    otp_code: str
    password: str

    @field_validator("otp_code")
    @classmethod
    def validate_otp_format(cls, value: str) -> str:
        if not re.fullmatch(r"\d{6}", value.strip()):
            raise ValueError("OTP code must be exactly 6 digits.")
        return value.strip()

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        """
        Mirrors UserCreate.validate_password_strength exactly —
        see that validator's own docstring for the rules.
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
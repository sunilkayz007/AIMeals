"""
=========================================================
AIMeals Backend
Password Reset (Forgot Password) Schemas

Responsibilities:
    - Define request shapes for the two-step "forgot password"
      flow: request a code by email, then confirm it + set a
      new password.

Notes:
    - Kept as its own file, mirroring app/schemas/email_verification.py's
      own reasoning for why IT is a separate file rather than
      folded into app/schemas/auth.py.
    - ResetPasswordRequest's otp_code/new_password validators
      are an exact mirror of VerifySignupOTP's in
      email_verification.py -- same OTP format, same password
      strength rules -- since this reuses that exact same
      email_verifications OTP mechanism under the hood (see
      AuthService.request_password_reset()'s docstring).

Example usage:
    from app.schemas.password_reset import ForgotPasswordRequest, ResetPasswordRequest
=========================================================
"""

import re

from pydantic import BaseModel, EmailStr, field_validator


class ForgotPasswordRequest(BaseModel):
    """
    Shape of the payload accepted by
    POST /auth/forgot-password.
    """

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """
    Shape of the payload accepted by
    POST /auth/reset-password.
    """

    email: EmailStr
    otp_code: str
    new_password: str

    @field_validator("otp_code")
    @classmethod
    def validate_otp_format(cls, value: str) -> str:
        if not re.fullmatch(r"\d{6}", value.strip()):
            raise ValueError("OTP code must be exactly 6 digits.")
        return value.strip()

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        """
        Mirrors VerifySignupOTP.validate_password_strength (itself
        a mirror of UserCreate's) exactly -- see that validator's
        own docstring for the rules.
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

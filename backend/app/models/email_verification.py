"""
=========================================================
AIMeals Backend
Email Verification Model

Responsibilities:
    - Define the email_verifications table schema — short-
      lived OTP records for OTP-based signup

Notes:
    - This table holds PENDING signups only — no User row
      exists until the OTP is successfully verified (see
      AuthService.verify_signup_otp()). first_name/last_name
      are staged here temporarily since they're collected in
      step 1 (request OTP) but only actually used to create
      the User in step 2 (verify).
    - otp_hash, not the raw code — hashed the same way
      refresh tokens already are in this codebase (hash_token()
      from app.core.security), which is a deterministic hash,
      not a salted one, so it can be looked up/compared
      directly.
    - A row is deleted once consumed (successful verification)
      or superseded (a new OTP requested for the same email).
      There is no "expired but still present" cleanup job —
      expired rows are simply rejected on verify, and get
      cleared out naturally the next time that email requests
      a fresh code. Acceptable for this app's scale; a
      scheduled cleanup job would be the next step if this
      table ever grows large.

Example usage:
    from app.models.email_verification import EmailVerification
=========================================================
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.B_database import Base


class EmailVerification(Base):
    """
    One pending OTP-based signup attempt.

    Table: email_verifications
    """

    __tablename__ = "email_verifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    otp_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Staged here until verification succeeds — see module notes.
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<EmailVerification id={self.id} email={self.email} attempts={self.attempts}>"
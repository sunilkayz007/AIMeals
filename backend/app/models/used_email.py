"""
=========================================================
AIMeals Backend
Used Email Model

Responsibilities:
    - Define the used_emails table schema — anti-abuse
      credit-balance tracking that survives account deletion

Notes:
    - This table is DELIBERATELY not tied to any User row by
      foreign key, and is NEVER touched by account deletion's
      cascade — its entire purpose is remembering the unused
      credit balance an email had when its account was last
      deleted, independent of whatever account currently
      exists (or doesn't) for it.
    - REDESIGNED from a simple "has this email been used
      before" flag: the original version gave 0 fresh credits
      to any returning email, which correctly prevented
      farming but also unfairly zeroed out unused credits for
      someone who deleted their account for a completely
      legitimate reason. Storing the actual remaining_credits
      balance instead means resigning up with the same email
      resumes exactly where you left off — you can never GAIN
      credits by deleting (so farming is still pointless), but
      you never LOSE ones you hadn't used either. See
      AuthService's confirm_account_deletion() (writes this
      value) and _provision_new_account_credits() (reads it).
    - Stores a HASH of the email (via hash_token(), the same
      deterministic hash already used for OTP codes and
      refresh tokens), never the plaintext email — a genuine,
      deliberate exception to the "your data is fully deleted"
      promise in the privacy policy, disclosed there explicitly
      rather than left undocumented. The hash is one-way; this
      table cannot be used to recover anyone's actual email.

Example usage:
    from app.models.used_email import UsedEmail
=========================================================
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.B_database import Base


class UsedEmail(Base):
    """
    One email address (hashed), tracking the unused credit
    balance it had when its account was last deleted.

    Table: used_emails
    """

    __tablename__ = "used_emails"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    email_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    remaining_credits: Mapped[int] = mapped_column(Integer, nullable=False, default=20)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<UsedEmail id={self.id} remaining_credits={self.remaining_credits}>"
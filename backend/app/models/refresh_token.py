"""
=========================================================
AIMeals Backend
Refresh Token Model

Responsibilities:
    - Define the refresh_tokens table schema
    - Track issued refresh tokens so they can be revoked
      (enables real logout, unlike stateless-only JWTs)

Dependencies:
    - app.B_database.Base (declarative base)
    - app.models.user.User (foreign key target)

Notes:
    - Only a SHA-256 hash of the token is stored, never
      the raw token itself. This mirrors password hashing
      practice, but uses SHA-256 (fast, deterministic)
      rather than bcrypt (deliberately slow), since this
      is an exact-match lookup against a high-entropy JWT
      string, not a low-entropy password needing brute-
      force resistance.

Example usage:
    from app.models.refresh_token import RefreshToken

    token_row = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        expires_at=expires_at,
    )
=========================================================
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.B_database import Base


# =========================================================
# Refresh Token Model
# =========================================================

class RefreshToken(Base):
    """
    Represents a single issued refresh token.

    Table: refresh_tokens
    """

    __tablename__ = "refresh_tokens"

    # ---------------------------------------------------
    # Primary Key
    # ---------------------------------------------------

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ---------------------------------------------------
    # Foreign Key
    # ---------------------------------------------------

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ---------------------------------------------------
    # Token Data
    # ---------------------------------------------------

    token_hash: Mapped[str] = mapped_column(
        String(64),  # SHA-256 hex digest is always 64 chars
        unique=True,
        index=True,
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # ---------------------------------------------------
    # Timestamps
    # ---------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ---------------------------------------------------
    # Relationships
    # ---------------------------------------------------

    user = relationship("User")

    # ---------------------------------------------------
    # Representation
    # ---------------------------------------------------

    def __repr__(self) -> str:
        return f"<RefreshToken id={self.id} user_id={self.user_id} revoked={self.revoked}>"
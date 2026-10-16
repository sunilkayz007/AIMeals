"""
=========================================================
AIMeals Backend
User Model

Responsibilities:
    - Define the users table schema
    - Define the UserRole enum

Dependencies:
    - app.B_database.Base (declarative base)

Example usage:
    from app.models.user import User, UserRole

    new_user = User(
        email="jane@example.com",
        hashed_password=hash_password("secret"),
        first_name="Jane",
        last_name="Doe",
    )
=========================================================
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.B_database import Base


# =========================================================
# Role Enum
# =========================================================

class UserRole(str, enum.Enum):
    """
    Defines the set of allowed user roles.

    Stored in the database as a native Postgres ENUM type,
    so invalid values are rejected at the database level,
    not just in application code.
    """
    USER = "user"
    ADMIN = "admin"


# =========================================================
# User Model
# =========================================================

class User(Base):
    """
    Represents a registered AIMeals user.

    Table: users
    """

    __tablename__ = "users"

    # ---------------------------------------------------
    # Primary Key
    # ---------------------------------------------------

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ---------------------------------------------------
    # Identity / Credentials
    # ---------------------------------------------------

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # ---------------------------------------------------
    # Profile
    # ---------------------------------------------------

    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # ---------------------------------------------------
    # Role / Status
    # ---------------------------------------------------

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"),
        default=UserRole.USER,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
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

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ---------------------------------------------------
    # Representation
    # ---------------------------------------------------

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
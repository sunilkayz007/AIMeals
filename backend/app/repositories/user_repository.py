"""
=========================================================
AIMeals Backend
User Repository

Responsibilities:
    - Perform CRUD operations against the users table
    - Contains NO business logic (no password hashing,
      no validation, no token logic) — that belongs in
      the service layer

Dependencies:
    - app.models.user.User

Example usage:
    from app.repositories.user_repository import UserRepository

    repo = UserRepository(db)
    user = repo.get_by_email("jane@example.com")
=========================================================
"""

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.models.user import User, UserRole


# =========================================================
# User Repository
# =========================================================

class UserRepository:
    """
    Encapsulates all direct database access for the User model.
    """

    def __init__(self, db: Session):
        self.db = db

    # ---------------------------------------------------
    # Read
    # ---------------------------------------------------

    def get_by_email(self, email: str) -> Optional[User]:
        """
        Fetches a user by email address.
        Returns None if no matching user exists.
        """
        return self.db.query(User).filter(User.email == email).first()

    def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """
        Fetches a user by primary key.
        Returns None if no matching user exists.
        """
        return self.db.query(User).filter(User.id == user_id).first()

    # ---------------------------------------------------
    # Create
    # ---------------------------------------------------

    def create_user(
        self,
        email: str,
        hashed_password: str,
        first_name: str,
        last_name: str,
        role: UserRole = UserRole.USER,
    ) -> User:
        """
        Inserts a new user row.

        Expects an ALREADY HASHED password — this repository
        does not perform hashing. That responsibility belongs
        to the service layer.
        """
        new_user = User(
            email=email,
            hashed_password=hashed_password,
            first_name=first_name,
            last_name=last_name,
            role=role,
        )

        self.db.add(new_user)
        self.db.commit()
        self.db.refresh(new_user)

        return new_user

    # ---------------------------------------------------
    # Update
    # ---------------------------------------------------

    def deactivate_user(self, user: User) -> User:
        """
        Soft-disables a user account by setting is_active to False.
        Does not delete the row.
        """
        user.is_active = False
        self.db.commit()
        self.db.refresh(user)

        return user

    def update_password(self, user: User, hashed_password: str) -> User:
        """
        Sets a new (already-hashed) password on an existing user.
        Expects an ALREADY HASHED password, same convention as
        create_user() -- hashing stays the service layer's job.
        Used by AuthService.confirm_password_reset().
        """
        user.hashed_password = hashed_password
        self.db.commit()
        self.db.refresh(user)

        return user
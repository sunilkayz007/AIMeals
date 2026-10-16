"""
=========================================================
AIMeals Backend
Refresh Token Repository

Responsibilities:
    - Perform CRUD operations against the refresh_tokens table
    - Contains NO business logic (no token generation,
      no hashing) — that belongs in the service layer

Dependencies:
    - app.models.refresh_token.RefreshToken

Example usage:
    from app.repositories.refresh_token_repository import RefreshTokenRepository

    repo = RefreshTokenRepository(db)
    token_row = repo.get_by_hash(token_hash)
=========================================================
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.refresh_token import RefreshToken


# =========================================================
# Refresh Token Repository
# =========================================================

class RefreshTokenRepository:
    """
    Encapsulates all direct database access for the RefreshToken model.
    """

    def __init__(self, db: Session):
        self.db = db

    # ---------------------------------------------------
    # Read
    # ---------------------------------------------------

    def get_by_hash(self, token_hash: str) -> Optional[RefreshToken]:
        """
        Fetches a refresh token row by its hash.
        Returns None if no matching row exists.
        """
        return (
            self.db.query(RefreshToken)
            .filter(RefreshToken.token_hash == token_hash)
            .first()
        )

    # ---------------------------------------------------
    # Create
    # ---------------------------------------------------

    def create(
        self,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> RefreshToken:
        """
        Inserts a new refresh token row.
        """
        new_token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )

        self.db.add(new_token)
        self.db.commit()
        self.db.refresh(new_token)

        return new_token

    # ---------------------------------------------------
    # Update
    # ---------------------------------------------------

    def revoke(self, token_row: RefreshToken) -> RefreshToken:
        """
        Marks a refresh token row as revoked.
        Does not delete the row (kept for audit purposes).
        """
        token_row.revoked = True
        self.db.commit()
        self.db.refresh(token_row)

        return token_row
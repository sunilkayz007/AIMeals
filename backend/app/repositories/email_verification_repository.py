"""
=========================================================
AIMeals Backend
Email Verification Repository

Responsibilities:
    - Perform CRUD operations against email_verifications
    - Contains NO business logic

Dependencies:
    - app.models.email_verification.EmailVerification
=========================================================
"""

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.email_verification import EmailVerification


class EmailVerificationRepository:
    def __init__(self, db: Session):
        self.db = db

    # ---------------------------------------------------
    # Read
    # ---------------------------------------------------

    def get_latest_by_email(self, email: str) -> Optional[EmailVerification]:
        return (
            self.db.query(EmailVerification)
            .filter(EmailVerification.email == email)
            .order_by(EmailVerification.created_at.desc())
            .first()
        )

    # ---------------------------------------------------
    # Create
    # ---------------------------------------------------

    def create(
        self,
        email: str,
        otp_hash: str,
        first_name: str,
        last_name: str,
        expires_at: datetime,
    ) -> EmailVerification:
        new_row = EmailVerification(
            email=email,
            otp_hash=otp_hash,
            first_name=first_name,
            last_name=last_name,
            expires_at=expires_at,
        )
        self.db.add(new_row)
        self.db.commit()
        self.db.refresh(new_row)
        return new_row

    # ---------------------------------------------------
    # Update
    # ---------------------------------------------------

    def increment_attempts(self, row: EmailVerification) -> EmailVerification:
        row.attempts += 1
        self.db.commit()
        self.db.refresh(row)
        return row

    # ---------------------------------------------------
    # Delete
    # ---------------------------------------------------

    def delete(self, row: EmailVerification) -> None:
        self.db.delete(row)
        self.db.commit()

    def delete_all_for_email(self, email: str) -> None:
        """
        Clears any previous unconsumed OTP(s) for this email —
        called at the start of request_signup_otp() so only
        the most recently requested code is ever valid.
        """
        self.db.query(EmailVerification).filter(EmailVerification.email == email).delete()
        self.db.commit()
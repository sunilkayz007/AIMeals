"""
=========================================================
AIMeals Backend
Used Email Repository

Responsibilities:
    - Perform CRUD operations against used_emails
    - Contains NO business logic

Dependencies:
    - app.models.used_email.UsedEmail
=========================================================
"""

from sqlalchemy.orm import Session
from app.models.used_email import UsedEmail


class UsedEmailRepository:
    def __init__(self, db: Session):
        self.db = db

    def exists(self, email_hash: str) -> bool:
        return (
            self.db.query(UsedEmail).filter(UsedEmail.email_hash == email_hash).first()
            is not None
        )

    def get_by_email_hash(self, email_hash: str) -> UsedEmail | None:
        return (
            self.db.query(UsedEmail).filter(UsedEmail.email_hash == email_hash).first()
        )

    def create(self, email_hash: str) -> UsedEmail:
        new_row = UsedEmail(email_hash=email_hash)
        self.db.add(new_row)
        self.db.commit()
        self.db.refresh(new_row)
        return new_row
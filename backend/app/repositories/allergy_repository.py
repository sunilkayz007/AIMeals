"""
=========================================================
AIMeals Backend
Allergy Repositories

Responsibilities:
    - Perform CRUD operations against the allergies,
      dietary_restrictions, user_allergies, and
      user_dietary_restrictions tables
    - Contains NO business logic

Dependencies:
    - app.models.allergy

Example usage:
    from app.repositories.allergy_repository import (
        AllergyRepository, UserAllergyRepository
    )

    allergy_repo = AllergyRepository(db)
    all_allergies = allergy_repo.get_all()

    user_allergy_repo = UserAllergyRepository(db)
    user_allergy_repo.add_to_user(user.id, allergy.id, AllergySeverity.SEVERE)
=========================================================
"""

import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.allergy import (
    Allergy,
    AllergySeverity,
    DietaryRestriction,
    UserAllergy,
    UserDietaryRestriction,
)


# =========================================================
# Allergy Lookup Repository
# =========================================================

class AllergyRepository:
    """
    CRUD for the allergies lookup table (reference data).
    """

    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> List[Allergy]:
        """Returns the full master list of known allergies."""
        return self.db.query(Allergy).order_by(Allergy.name).all()

    def get_by_id(self, allergy_id: uuid.UUID) -> Optional[Allergy]:
        return self.db.query(Allergy).filter(Allergy.id == allergy_id).first()

    def get_by_name(self, name: str) -> Optional[Allergy]:
        return self.db.query(Allergy).filter(Allergy.name == name).first()

    def create(self, name: str) -> Allergy:
        """Adds a new allergy to the master lookup list."""
        new_allergy = Allergy(name=name)
        self.db.add(new_allergy)
        self.db.commit()
        self.db.refresh(new_allergy)
        return new_allergy


# =========================================================
# Dietary Restriction Lookup Repository
# =========================================================

class DietaryRestrictionRepository:
    """
    CRUD for the dietary_restrictions lookup table (reference data).
    """

    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> List[DietaryRestriction]:
        """Returns the full master list of known dietary restrictions."""
        return self.db.query(DietaryRestriction).order_by(DietaryRestriction.name).all()

    def get_by_id(self, restriction_id: uuid.UUID) -> Optional[DietaryRestriction]:
        return (
            self.db.query(DietaryRestriction)
            .filter(DietaryRestriction.id == restriction_id)
            .first()
        )

    def get_by_name(self, name: str) -> Optional[DietaryRestriction]:
        return (
            self.db.query(DietaryRestriction)
            .filter(DietaryRestriction.name == name)
            .first()
        )

    def create(self, name: str) -> DietaryRestriction:
        """Adds a new dietary restriction to the master lookup list."""
        new_restriction = DietaryRestriction(name=name)
        self.db.add(new_restriction)
        self.db.commit()
        self.db.refresh(new_restriction)
        return new_restriction


# =========================================================
# User <-> Allergy Junction Repository
# =========================================================

class UserAllergyRepository:
    """
    CRUD for a specific user's linked allergies.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_for_user(self, user_id: uuid.UUID) -> List[UserAllergy]:
        """Returns all allergies linked to a specific user."""
        return self.db.query(UserAllergy).filter(UserAllergy.user_id == user_id).all()

    def add_to_user(
        self,
        user_id: uuid.UUID,
        allergy_id: uuid.UUID,
        severity: AllergySeverity = AllergySeverity.MODERATE,
    ) -> UserAllergy:
        """
        Links an allergy to a user.

        Note: the database's unique constraint on
        (user_id, allergy_id) will raise an IntegrityError
        if this pairing already exists — the service layer
        should catch this and translate it to a clear error
        rather than a raw DB exception.
        """
        link = UserAllergy(user_id=user_id, allergy_id=allergy_id, severity=severity)
        self.db.add(link)
        self.db.commit()
        self.db.refresh(link)
        return link

    def remove_from_user(self, user_allergy: UserAllergy) -> None:
        """Removes an allergy link from a user."""
        self.db.delete(user_allergy)
        self.db.commit()


# =========================================================
# User <-> Dietary Restriction Junction Repository
# =========================================================

class UserDietaryRestrictionRepository:
    """
    CRUD for a specific user's linked dietary restrictions.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_for_user(self, user_id: uuid.UUID) -> List[UserDietaryRestriction]:
        """Returns all dietary restrictions linked to a specific user."""
        return (
            self.db.query(UserDietaryRestriction)
            .filter(UserDietaryRestriction.user_id == user_id)
            .all()
        )

    def add_to_user(
        self,
        user_id: uuid.UUID,
        restriction_id: uuid.UUID,
    ) -> UserDietaryRestriction:
        """
        Links a dietary restriction to a user.

        Note: same uniqueness caveat as UserAllergyRepository.add_to_user.
        """
        link = UserDietaryRestriction(user_id=user_id, restriction_id=restriction_id)
        self.db.add(link)
        self.db.commit()
        self.db.refresh(link)
        return link

    def remove_from_user(self, link: UserDietaryRestriction) -> None:
        """Removes a dietary restriction link from a user."""
        self.db.delete(link)
        self.db.commit()
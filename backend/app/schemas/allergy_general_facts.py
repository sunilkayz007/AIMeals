"""
=========================================================
AIMeals Backend
Allergy General Facts Schema

Responsibilities:
    - Define the response shape for GET /ai/allergy-facts

Example usage:
    from app.schemas.allergy_general_facts import AllergyFactOut, AllergyFactsOut
=========================================================
"""

from pydantic import BaseModel


class AllergyFactOut(BaseModel):
    text: str
    category: str


class AllergyFactsOut(BaseModel):
    facts: list[AllergyFactOut]
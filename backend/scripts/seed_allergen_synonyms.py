"""
=========================================================
AIMeals Backend
Seed: Allergen Synonyms

Purpose:
    Populates the allergies and allergen_synonyms tables
    with a baseline set of common allergens and their
    product-name synonyms.

Notes:
    - Grounded in the FDA's 9 recognized major food
      allergens (milk, eggs, fish, crustacean shellfish,
      tree nuts, peanuts, wheat, soybeans, sesame — sesame
      was added to the official FDA list in 2023). This is
      a real regulatory baseline, not an arbitrary list —
      but it is NOT exhaustive of every possible allergen
      or cross-contamination source.
    - Safe to run multiple times: uses get_by_name/create
      for allergies and bulk_create (which skips existing
      entries) for synonyms, so re-running won't create
      duplicates.

Usage:
    python -m scripts.seed_allergen_synonyms
=========================================================
"""

from app.B_database import SessionLocal
from app.repositories.allergen_synonym_repository import AllergenSynonymRepository
from app.repositories.allergy_repository import AllergyRepository
from app.B_database import SessionLocal
from app.models.user import User  # noqa: F401 — needed for UserAllergy's relationship("User")
from app.repositories.allergen_synonym_repository import AllergenSynonymRepository
from app.repositories.allergy_repository import AllergyRepository

# ... rest of the file stays exactly the same
# FDA's 9 major food allergens, with common product-name
# synonyms/variants for each. Not exhaustive — a real
# baseline, not a complete medical allergen database.
BASELINE_ALLERGENS: dict[str, list[str]] = {
    "Milk": [
        "dairy", "cheese", "butter", "cream", "yogurt", "whey",
        "casein", "lactose", "ghee", "buttermilk", "custard",
    ],
    "Eggs": [
        "egg", "mayonnaise", "mayo", "meringue", "albumin", "egg white", "egg yolk",
    ],
    "Fish": [
        "salmon", "tuna", "cod", "anchovy", "anchovies", "fish sauce",
        "fish stock", "bass", "trout", "halibut", "tilapia",
    ],
    "Shellfish": [
        "shrimp", "prawn", "crab", "lobster", "crayfish", "scallop",
        "clam", "mussel", "oyster", "squid", "calamari",
    ],
    "Tree Nuts": [
        "almond", "cashew", "walnut", "pecan", "pistachio",
        "hazelnut", "macadamia", "brazil nut", "pine nut", "nut butter",
    ],
    "Peanuts": [
        "peanut", "groundnut", "groundnuts", "peanut butter", "peanut oil",
    ],
    "Wheat": [
        "flour", "bread", "pasta", "couscous", "semolina",
        "durum", "bulgur", "seitan", "breadcrumbs",
    ],
    "Soy": [
        "soybean", "soya", "tofu", "edamame", "tamari",
        "soy sauce", "miso", "tempeh",
    ],
    "Sesame": [
        "sesame seed", "sesame oil", "tahini", "hummus", "halva",
    ],
}


def run_seed() -> None:
    db = SessionLocal()

    allergy_repo = AllergyRepository(db)
    synonym_repo = AllergenSynonymRepository(db)

    for allergen_name, synonyms in BASELINE_ALLERGENS.items():
        allergy = allergy_repo.get_by_name(allergen_name)
        if allergy is None:
            allergy = allergy_repo.create(allergen_name)
            print(f"Created allergy: {allergen_name}")
        else:
            print(f"Allergy already exists: {allergen_name}")

        created = synonym_repo.bulk_create(allergy.id, synonyms)
        print(f"  Added {len(created)} new synonym(s) for {allergen_name} "
              f"(skipped {len(synonyms) - len(created)} already present)")

    db.close()
    print("\nSeed complete.")


if __name__ == "__main__":
    run_seed()
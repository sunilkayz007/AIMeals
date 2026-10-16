from app.B_database import SessionLocal
from app.repositories.user_repository import UserRepository
from app.ai.allergen_checker import AllergenChecker

db = SessionLocal()

user_repo = UserRepository(db)
user = user_repo.get_by_email("testuser@example.com")

if user is None:
    print("ERROR: test user not found")
else:
    checker = AllergenChecker(db)

    # Test 1: text that clearly contains a known allergen (Peanuts)
    fake_ingredients_with_allergen = "2 tbsp peanut butter\n1 cup rice\n1 tsp soy sauce"
    fake_instructions = "Mix peanut butter with warm water to make a sauce."

    violations = checker.check_recipe_text(
        user.id, fake_ingredients_with_allergen, fake_instructions
    )
    print("Test 1 — text WITH peanut butter:")
    print("Violations found:", violations)
    assert "Peanuts" in violations, "FAILED: checker did not catch an obvious peanut ingredient!"
    print("PASSED — correctly detected the allergen.\n")

    # Test 2: a synonym, not the exact allergy name (groundnut)
    fake_ingredients_synonym = "1/4 cup groundnut oil\n2 cups vegetables"
    violations2 = checker.check_recipe_text(user.id, fake_ingredients_synonym, "")
    print("Test 2 — text WITH 'groundnut' (synonym, not literal 'peanut'):")
    print("Violations found:", violations2)
    assert "Peanuts" in violations2, "FAILED: checker did not catch the 'groundnut' synonym!"
    print("PASSED — correctly caught the synonym.\n")

    # Test 3: genuinely safe text, no allergens present
    safe_ingredients = "2 salmon fillets\n1 cup rice\n1 tbsp olive oil"
    violations3 = checker.check_recipe_text(user.id, safe_ingredients, "")
    print("Test 3 — genuinely safe text:")
    print("Violations found (should be empty):", violations3)
    assert violations3 == [], "FAILED: checker incorrectly flagged safe text!"
    print("PASSED — correctly found nothing.\n")

db.close()
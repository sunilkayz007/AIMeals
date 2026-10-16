from app.B_database import SessionLocal
from app.repositories.user_repository import UserRepository
from app.repositories.recipe_repository import RecipeRepository

db = SessionLocal()

user_repo = UserRepository(db)
user = user_repo.get_by_email("testuser@example.com")

if user is None:
    print("ERROR: test user not found")
else:
    recipe_repo = RecipeRepository(db)

    recipe = recipe_repo.create(
        title="Grilled Chicken Salad",
        instructions="1. Grill chicken.\n2. Chop vegetables.\n3. Combine.",
        ingredients="200g chicken breast\n1 cup lettuce\n1/2 cup cherry tomatoes",
        created_by_user_id=user.id,
        servings=2,
        calories_per_serving=450,
        protein_g=35,
        carbs_g=20,
        fat_g=22,
        is_ai_generated=True,
    )
    print("Created recipe:", recipe)

    fetched = recipe_repo.get_by_id(recipe.id)
    print("Fetched by id:", fetched)

    user_recipes = recipe_repo.get_by_user(user.id)
    print("User's recipes:", user_recipes)

    system_recipes = recipe_repo.get_system_recipes()
    print("System recipes (should be empty so far):", system_recipes)

    updated = recipe_repo.update(fetched, servings=4) if fetched else None
    print("Updated servings:", updated.servings if updated else "N/A")

db.close()
from app.B_database import SessionLocal
from app.repositories.user_repository import UserRepository
from app.services.recipe_service import RecipeService
from app.core.exceptions import NotRecipeOwnerError, RecipeNotFoundError

db = SessionLocal()

user_repo = UserRepository(db)
user = user_repo.get_by_email("testuser@example.com")

if user is None:
    print("ERROR: test user not found")
else:
    service = RecipeService(db)

    recipe = service.create_recipe(
        user_id=user.id,
        title="Service Test Recipe",
        instructions="Mix and cook.",
        ingredients="Flour, water, salt.",
        servings=2,
    )
    print("Created recipe:", recipe)

    # Owner can update their own recipe
    updated = service.update_recipe(recipe.id, user.id, servings=4)
    print("Owner updated servings:", updated.servings)

    # A different (fake) user id should NOT be able to update it
    import uuid
    fake_other_user_id = uuid.uuid4()

    try:
        service.update_recipe(recipe.id, fake_other_user_id, servings=99)
        print("ERROR: non-owner update was incorrectly allowed")
    except NotRecipeOwnerError as e:
        print("Correctly blocked non-owner update:", e)

    # Nonexistent recipe should raise RecipeNotFoundError
    try:
        service.update_recipe(uuid.uuid4(), user.id, servings=1)
        print("ERROR: nonexistent recipe update was incorrectly allowed")
    except RecipeNotFoundError as e:
        print("Correctly raised for nonexistent recipe:", e)

    # Owner can delete their own recipe
    service.delete_recipe(recipe.id, user.id)
    still_there = service.get_recipe(recipe.id)
    print("Recipe after deletion (should be None):", still_there)

db.close()
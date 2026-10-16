from app.B_database import SessionLocal
from app.repositories.user_repository import UserRepository
from app.repositories.food_image_repository import FoodImageRepository
from app.repositories.ai_interaction_repository import AIInteractionRepository
from app.models.ai_interaction import InteractionType
from app.models.recipe import Recipe  # noqa: F401 — needed for AIInteraction's relationship("Recipe")

db = SessionLocal()

user_repo = UserRepository(db)
user = user_repo.get_by_email("testuser@example.com")

if user is None:
    print("ERROR: test user not found")
else:
    image_repo = FoodImageRepository(db)
    interaction_repo = AIInteractionRepository(db)

    # Simulate: image uploaded first, analysis not done yet
    image = image_repo.create(
        user_id=user.id,
        image_url="app/uploads/food/test_meal.jpg",
    )
    print("Created image (pre-analysis):", image)
    print("ai_interaction_id before analysis:", image.ai_interaction_id)

    # Simulate: AI analysis completes
    interaction = interaction_repo.create(
        user_id=user.id,
        interaction_type=InteractionType.FOOD_IMAGE_ANALYSIS,
        prompt="Analyze this food image",
        response="This appears to be a grilled chicken salad, approximately 450 calories.",
        model_used="claude-sonnet-5",
        tokens_used=1200,
    )
    print("Created AI interaction for the analysis:", interaction)

    # Update the image with the analysis results
    updated_image = image_repo.update(
        image,
        ai_interaction_id=interaction.id,
        identified_food_name="Grilled Chicken Salad",
        estimated_calories=450,
        estimated_protein_g=35,
        estimated_carbs_g=20,
        estimated_fat_g=22,
    )
    print("Updated image (post-analysis):", updated_image)
    print("Identified food:", updated_image.identified_food_name)

    all_images = image_repo.get_by_user(user.id)
    print("User's food images:", all_images)

db.close()
import uuid
from app.B_database import SessionLocal
from app.repositories.user_repository import UserRepository
from app.repositories.ai_interaction_repository import AIInteractionRepository
from app.models.ai_interaction import InteractionType
from app.models.recipe import Recipe  # noqa: F401 — needed for AIInteraction's relationship("Recipe")

db = SessionLocal()

user_repo = UserRepository(db)
user = user_repo.get_by_email("testuser@example.com")

if user is None:
    print("ERROR: test user not found")
else:
    interaction_repo = AIInteractionRepository(db)

    chat_session = uuid.uuid4()

    msg1 = interaction_repo.create(
        user_id=user.id,
        interaction_type=InteractionType.CHAT,
        prompt="What should I eat for dinner?",
        response="Given your weight loss goal, I'd suggest grilled chicken with vegetables.",
        model_used="claude-haiku-4-5",
        session_id=chat_session,
        tokens_used=320,
    )
    print("Created chat message 1:", msg1)

    msg2 = interaction_repo.create(
        user_id=user.id,
        interaction_type=InteractionType.CHAT,
        prompt="Can you give me the recipe for that?",
        response="Sure — here's a simple grilled chicken recipe...",
        model_used="claude-haiku-4-5",
        session_id=chat_session,
        tokens_used=410,
    )
    print("Created chat message 2:", msg2)

    one_off = interaction_repo.create(
        user_id=user.id,
        interaction_type=InteractionType.RECIPE_GENERATION,
        prompt="Generate a high-protein breakfast recipe",
        response="Here's a protein-packed breakfast burrito recipe...",
        model_used="claude-sonnet-5",
        session_id=None,
        tokens_used=850,
    )
    print("Created one-off recipe generation:", one_off)

    thread = interaction_repo.get_by_session(chat_session)
    print("Chat thread (should be 2 messages, in order):", thread)

    all_history = interaction_repo.get_by_user(user.id)
    print("All history (should be 3):", all_history)

    limited = interaction_repo.get_by_user(user.id, limit=1)
    print("Limited to 1 (most recent):", limited)

    total_tokens = interaction_repo.get_total_tokens_used(user.id)
    print("Total tokens used (should be 320+410+850=1580):", total_tokens)

db.close()
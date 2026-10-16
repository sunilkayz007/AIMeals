from app.B_database import SessionLocal
from app.repositories.user_repository import UserRepository
from app.services.ai_service import AIService
from app.core.exceptions import InsufficientCreditsError, ClaudeAPIError
from app.models.recipe import Recipe  # noqa: F401 — needed for AIInteraction's relationship("Recipe")

db = SessionLocal()

user_repo = UserRepository(db)
user = user_repo.get_by_email("testuser@example.com")

if user is None:
    print("ERROR: test user not found")
else:
    service = AIService(db)

    try:
        reply = service.send_chat_message(
            user_id=user.id,
            user_message="Give me one quick tip for eating more protein.",
        )
        print("Claude replied:")
        print(reply)
    except InsufficientCreditsError as e:
        print("Blocked — insufficient credits:", e)
    except ClaudeAPIError as e:
        print("Claude API call failed:", e)

db.close()
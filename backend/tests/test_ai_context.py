from app.B_database import SessionLocal
from app.repositories.user_repository import UserRepository
from app.services.ai_service import AIService
from app.core.exceptions import InsufficientCreditsError, ClaudeAPIError
from app.models.recipe import Recipe  # noqa: F401

db = SessionLocal()

user_repo = UserRepository(db)
user = user_repo.get_by_email("testuser@example.com")

if user is None:
    print("ERROR: test user not found")
else:
    service = AIService(db)

    try:
        # First message — starts a new session
        reply1 = service.send_chat_message(
            user_id=user.id,
            user_message="My favorite fruit is mango. Remember that.",
        )
        print("Reply 1:", reply1)

        # We need the session_id used for message 1 to continue the SAME conversation.
        # Fetch it from the most recent interaction we just created.
        from app.repositories.ai_interaction_repository import AIInteractionRepository
        interaction_repo = AIInteractionRepository(db)
        recent = interaction_repo.get_by_user(user.id, limit=1)
        session_id = recent[0].session_id
        print("\nSession id:", session_id)

        # Second message — same session, should show awareness of message 1
        reply2 = service.send_chat_message(
            user_id=user.id,
            user_message="What's my favorite fruit that I just told you?",
            session_id=session_id,
        )
        print("\nReply 2:", reply2)

    except InsufficientCreditsError as e:
        print("Blocked — insufficient credits:", e)
    except ClaudeAPIError as e:
        print("Claude API call failed:", e)

db.close()
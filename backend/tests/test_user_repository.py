from app.B_database import SessionLocal
from app.repositories.user_repository import UserRepository
from app.core.security import hash_password

db = SessionLocal()
repo = UserRepository(db)

# Create a test user (only if one doesn't already exist)
existing = repo.get_by_email("testuser@example.com")
if existing:
    print("Test user already exists:", existing)
else:
    new_user = repo.create_user(
        email="testuser@example.com",
        hashed_password=hash_password("TestPass123"),
        first_name="Test",
        last_name="User",
    )
    print("Created user:", new_user)

# Fetch by email
fetched = repo.get_by_email("testuser@example.com")

if fetched is None:
    print("ERROR: user was not found after creation")
else:
    print("Fetched by email:", fetched)

    # Fetch by id
    fetched_by_id = repo.get_by_id(fetched.id)
    print("Fetched by id:", fetched_by_id)

db.close()
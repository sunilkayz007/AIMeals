from datetime import date, timedelta
from app.B_database import SessionLocal
from app.repositories.user_repository import UserRepository
from app.repositories.progress_entry_repository import ProgressEntryRepository

db = SessionLocal()

user_repo = UserRepository(db)
user = user_repo.get_by_email("testuser@example.com")

if user is None:
    print("ERROR: test user not found")
else:
    progress_repo = ProgressEntryRepository(db)

    today = date.today()
    week_ago = today - timedelta(days=7)

    # Only create if not already present (respects the one-per-day constraint)
    existing_today = progress_repo.get_by_user_and_date(user.id, today)
    if existing_today:
        print("Today's entry already exists:", existing_today)
        entry_today = existing_today
    else:
        entry_today = progress_repo.create(
            user_id=user.id,
            recorded_date=today,
            weight_kg=74.5,
        )
        print("Created today's entry:", entry_today)

    existing_week_ago = progress_repo.get_by_user_and_date(user.id, week_ago)
    if existing_week_ago:
        print("Week-ago entry already exists:", existing_week_ago)
    else:
        entry_week_ago = progress_repo.create(
            user_id=user.id,
            recorded_date=week_ago,
            weight_kg=76.0,
        )
        print("Created week-ago entry:", entry_week_ago)

    trend = progress_repo.get_by_user(user.id, start_date=week_ago, end_date=today)
    print("7-day trend (oldest first):", trend)

    updated = progress_repo.update(entry_today, weight_kg=74.2)
    print("Updated today's weight:", updated.weight_kg)

db.close()
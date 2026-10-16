from datetime import date, timedelta
from app.B_database import SessionLocal
from app.repositories.user_repository import UserRepository
from app.repositories.pantry_item_repository import PantryItemRepository

db = SessionLocal()

user_repo = UserRepository(db)
user = user_repo.get_by_email("testuser@example.com")

if user is None:
    print("ERROR: test user not found")
else:
    pantry_repo = PantryItemRepository(db)

    today = date.today()

    # Two batches of eggs, different expiration dates — tests the
    # "multiple rows per ingredient" design decision directly
    eggs_batch1 = pantry_repo.create(
        user_id=user.id,
        ingredient_name="Eggs",
        quantity=12,
        unit="pieces",
        expiration_date=today + timedelta(days=2),  # expiring soon
    )
    print("Created eggs batch 1 (expiring soon):", eggs_batch1)

    eggs_batch2 = pantry_repo.create(
        user_id=user.id,
        ingredient_name="Eggs",
        quantity=12,
        unit="pieces",
        expiration_date=today + timedelta(days=20),  # not expiring soon
    )
    print("Created eggs batch 2 (not expiring soon):", eggs_batch2)

    rice = pantry_repo.create(
        user_id=user.id,
        ingredient_name="Rice",
        quantity=2,
        unit="kg",
        expiration_date=None,  # no expiration tracked
    )
    print("Created rice (no expiration):", rice)

    all_items = pantry_repo.get_by_user(user.id)
    print("All pantry items:", all_items)

    expiring = pantry_repo.get_expiring_soon(user.id, within_days=3)
    print("Expiring within 3 days (should be only batch 1):", expiring)

    updated = pantry_repo.update(eggs_batch2, quantity=10)
    print("Updated batch 2 quantity:", updated.quantity)

db.close()
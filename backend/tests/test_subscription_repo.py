from app.B_database import SessionLocal
from app.repositories.user_repository import UserRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.models.subscription import SubscriptionTier

db = SessionLocal()

user_repo = UserRepository(db)
user = user_repo.get_by_email("testuser@example.com")

if user is None:
    print("ERROR: test user not found")
else:
    sub_repo = SubscriptionRepository(db)

    subscription = sub_repo.get_by_user_id(user.id)
    if subscription is None:
        subscription = sub_repo.create(user_id=user.id)
        print("Created subscription:", subscription)
    else:
        print("Subscription already exists:", subscription)

    print("Credits used before:", subscription.credits_used_this_period)

    sub_repo.increment_credits_used(subscription, amount=3)
    print("Credits used after +3:", subscription.credits_used_this_period)

    sub_repo.increment_credits_used(subscription)  # default amount=1
    print("Credits used after +1 more:", subscription.credits_used_this_period)

    upgraded = sub_repo.update(subscription, tier=SubscriptionTier.PLUS, monthly_credit_allowance=100)
    print("After upgrade to PLUS:", upgraded.tier, upgraded.monthly_credit_allowance)

    reset = sub_repo.reset_credits_for_new_period(subscription)
    print("Credits after reset:", reset.credits_used_this_period)

db.close()
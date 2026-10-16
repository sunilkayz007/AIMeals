from app.B_database import SessionLocal
from app.repositories.user_repository import UserRepository
from app.services.subscription_service import SubscriptionService
from app.models.ai_interaction import InteractionType
from app.models.subscription import SubscriptionTier
from app.core.exceptions import InsufficientCreditsError
from app.models.recipe import Recipe  # noqa: F401 — needed for AIInteraction's relationship("Recipe")

db = SessionLocal()

user_repo = UserRepository(db)
user = user_repo.get_by_email("testuser@example.com")

if user is None:
    print("ERROR: test user not found")
else:
    service = SubscriptionService(db)

    subscription = service.get_subscription(user.id)
    if subscription is None:
        print("ERROR: test user has no subscription — run test_subscription_repo.py first")
    else:
        print("Current subscription:", subscription)
        print("Current model routing:", service.get_model_for_user(user.id))

        service.reset_period(user.id)
        subscription = service.get_subscription(user.id)
        if subscription is None:
            print("ERROR: subscription vanished after reset")
        else:
            print(f"\nAfter reset — allowance: {subscription.monthly_credit_allowance}, used: {subscription.credits_used_this_period}")

            updated = service.check_and_consume_credit(user.id, InteractionType.CHAT)
            print(f"After 1 chat — used: {updated.credits_used_this_period}")

            updated = service.check_and_consume_credit(user.id, InteractionType.MEAL_PLAN_GENERATION)
            print(f"After 1 meal plan (+5) — used: {updated.credits_used_this_period}")

            from app.repositories.subscription_repository import SubscriptionRepository
            sub_repo = SubscriptionRepository(db)
            sub_repo.update(subscription, monthly_credit_allowance=6)

            try:
                service.check_and_consume_credit(user.id, InteractionType.CHAT)
                print("ERROR: overspend was incorrectly allowed")
            except InsufficientCreditsError as e:
                print("Correctly blocked overspend:", e)

            final = service.get_subscription(user.id)
            if final is not None:
                print(f"Final used (should still be 6, not 7): {final.credits_used_this_period}")

            upgraded = service.upgrade_tier(user.id, SubscriptionTier.PRO)
            print(f"\nAfter upgrade to PRO — tier: {upgraded.tier}, allowance: {upgraded.monthly_credit_allowance}")
            print("Model routing after upgrade:", service.get_model_for_user(user.id))

db.close()
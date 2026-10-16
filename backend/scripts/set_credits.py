"""
=========================================================
AIMeals Backend
Set User Credits (one-off script)

Usage:
    python scripts/set_credits.py your-email@example.com 1000

Notes:
    - Run this from the backend/ folder, with your venv active.
    - Sets monthly_credit_allowance to the given amount AND
      resets credits_used_this_period to 0, so the user
      actually has that many credits available right away —
      just raising the allowance without resetting usage
      would leave them with (new_allowance - already_used)
      remaining, not the full amount.
    - ASSUMPTION: imports Subscription from
      app.models.subscription. This matches every other
      model's naming convention seen this session (Report at
      app.models.report.Report, FoodImage at
      app.models.food_image.FoodImage, etc.), but wasn't
      independently confirmed the way User/UserRole was. If
      the import fails, that's the one line to adjust.
=========================================================
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.B_database import SessionLocal
from app.models.user import User
from app.models.subscription import Subscription


def set_credits(email: str, amount: int) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            print(f"No user found with email: {email}")
            return

        subscription = db.query(Subscription).filter(Subscription.user_id == user.id).first()
        if subscription is None:
            print(f"{email} has no subscription row — nothing to update.")
            return

        subscription.monthly_credit_allowance = amount
        subscription.credits_used_this_period = 0
        db.commit()

        print(f"Done — {email} now has {amount} credits available this period.")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scripts/set_credits.py your-email@example.com 1000")
        sys.exit(1)

    try:
        credit_amount = int(sys.argv[2])
    except ValueError:
        print("Credit amount must be a whole number.")
        sys.exit(1)

    set_credits(sys.argv[1], credit_amount)
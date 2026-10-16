"""
=========================================================
AIMeals Backend
Promote User to Admin (one-off script)

Usage:
    python scripts/promote_admin.py your-email@example.com

Notes:
    - Run this from the backend/ folder, with your venv active
      (same environment you run alembic/uvicorn from).
    - Uses the real User/UserRole model rather than raw SQL,
      so the role value written is guaranteed correct — no
      risk of a casing mismatch against whatever your enum's
      actual stored representation is.
    - ASSUMPTION: imports SessionLocal from app.B_database. If
      your session factory has a different name, this is the
      one line to adjust — everything else stays the same.
=========================================================
"""

import sys
from pathlib import Path

# Running this script directly only puts scripts/ on the import
# path, not backend/ above it — add it explicitly so `app` is
# importable no matter how this gets invoked.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.B_database import SessionLocal
from app.models.user import User, UserRole


def promote_to_admin(email: str) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()

        if user is None:
            print(f"No user found with email: {email}")
            return

        if user.role == UserRole.ADMIN:
            print(f"{email} is already an admin — nothing to do.")
            return

        user.role = UserRole.ADMIN
        db.commit()
        print(f"Done — {email} is now an admin.")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/promote_admin.py your-email@example.com")
        sys.exit(1)

    promote_to_admin(sys.argv[1])
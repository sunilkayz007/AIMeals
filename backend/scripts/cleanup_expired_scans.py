"""
=========================================================
AIMeals Backend
Cleanup: Expired Ingredient Scans

Purpose:
    Deletes ingredient_scans rows (any status — pending or
    confirmed) older than 24 hours. Per project decision,
    both abandoned scans (never confirmed) and confirmed
    scans (already consumed by generate_recipe_from_scan())
    are swept on the same timer, since neither is needed
    once the window has passed.

Notes:
    - Intended to be run on a schedule (cron / Windows Task
      Scheduler / etc.), not as part of request handling.
    - Safe to run repeatedly — each run only ever deletes
      rows already past the cutoff.

Usage:
    python -m scripts.cleanup_expired_scans
=========================================================
"""

from datetime import datetime, timedelta, timezone

from app.B_database import SessionLocal
from app.repositories.ingredient_scan_repository import IngredientScanRepository

TTL_HOURS = 24


def run_cleanup() -> None:
    db = SessionLocal()

    try:
        scan_repo = IngredientScanRepository(db)

        cutoff = datetime.now(timezone.utc) - timedelta(hours=TTL_HOURS)
        expired_scans = scan_repo.get_expired(cutoff_time=cutoff)

        if not expired_scans:
            print("No expired ingredient scans to clean up.")
            return

        for scan in expired_scans:
            print(f"Deleting scan {scan.id} (status={scan.status}, created_at={scan.created_at})")
            scan_repo.delete(scan)

        print(f"\nCleanup complete. Deleted {len(expired_scans)} expired scan(s).")

    finally:
        db.close()


if __name__ == "__main__":
    run_cleanup()
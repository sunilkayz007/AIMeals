"""
=========================================================
AIMeals Backend
Allergen Consent Ledger

Responsibilities:
    - Maintain a live-updating JSON file mirroring every
      allergen-override consent record, as a convenient
      human-readable/grep-able export alongside the
      authoritative database row.

Dependencies:
    - none beyond the standard library — same design
      constraint as usage_ledger.py

Notes:
    - DELIBERATE DEVIATION from usage_ledger.py's pattern:
      that ledger silently swallows write failures ("usage
      tracking must never break a user-facing feature," which
      is the right call for analytics). This ledger does the
      OPPOSITE — record() raises on failure. A consent record
      that silently failed to write is a liability gap, not a
      minor inconvenience, and the caller (AIService) needs to
      know immediately if the mirror write failed so it can
      decide how to handle that (at minimum: log loudly; at
      most: this is exactly the kind of failure that should
      page someone).
    - The DATABASE ROW (AllergenOverrideConsent, written via
      AllergenConsentRepository) is the authoritative record.
      This JSON file is a MIRROR for convenience — grep-able
      without a DB connection, easy to export wholesale for a
      legal request. If the two ever disagree, the database
      row is correct.
    - Append-only by design: entries are keyed by consent_id
      and never modified or removed once written, matching
      the insert-only nature of the DB table it mirrors.
    - Writes are ATOMIC (write to a .tmp file, then swap it
      into place) so a crash mid-write can't leave a
      half-written, corrupted JSON file behind — same
      technique as usage_ledger.py.
    - Guarded by a module-level threading.Lock, same reasoning
      as usage_ledger.py: FastAPI's sync route handlers can
      run concurrently across worker threads.
    - Default path is app/data/consent_ledger.json, matching
      usage_ledger.json's convention of living under app/data/.

Example usage:
    from app.core.consent_ledger import ConsentLedger

    ledger = ConsentLedger()
    ledger.record(
        consent_id=consent.id,
        user_id=user.id,
        user_email_snapshot=user.email,
        recipe_id=recipe.id,
        recipe_title_snapshot=recipe.title,
        flagged_allergens=["peanuts"],
        warning_text_shown="...",
    )
=========================================================
"""

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


class ConsentLedgerWriteError(Exception):
    """
    Raised when a consent record could not be written to the
    JSON mirror file. The database row (the authoritative
    record) has already been committed by this point — this
    exception signals that the convenience mirror is now out
    of sync, which should be logged loudly and investigated,
    not silently ignored.
    """
    pass


_lock = threading.Lock()

_EMPTY_LEDGER = {
    "consents": {},
    "last_updated": None,
}


# =========================================================
# Consent Ledger
# =========================================================

class ConsentLedger:
    """
    Maintains data/consent_ledger.json: an append-only mirror
    of every allergen-override consent record, keyed by
    consent_id.
    """

    def __init__(self, path: Optional[str] = None):
        self.path = Path(path or "app/data/consent_ledger.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------
    # Internal — Load / Save
    # ---------------------------------------------------

    def _load(self) -> dict:
        if not self.path.exists():
            return dict(_EMPTY_LEDGER, consents={})

        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            # Unlike usage_ledger.py, a corrupted file here is
            # NOT quietly replaced with an empty one — that
            # would silently discard every prior consent
            # record's mirror. Surface it loudly instead.
            raise ConsentLedgerWriteError(
                f"consent_ledger.json exists but could not be read/parsed: {e}. "
                f"Refusing to overwrite it with an empty ledger — investigate manually."
            ) from e

    def _save_atomic(self, data: dict) -> None:
        tmp_path = self.path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        tmp_path.replace(self.path)  # atomic swap

    # ---------------------------------------------------
    # Record
    # ---------------------------------------------------

    def record(
        self,
        consent_id: uuid.UUID,
        user_id: uuid.UUID,
        user_email_snapshot: str,
        recipe_id: uuid.UUID,
        recipe_title_snapshot: str,
        flagged_allergens: List[str],
        warning_text_shown: str,
    ) -> None:
        """
        Appends one consent record to the ledger and writes
        the file back to disk atomically.

        Raises ConsentLedgerWriteError on ANY failure — see
        the module docstring for why this deliberately does
        NOT swallow exceptions the way usage_ledger.py does.
        The caller (AIService.generate_recipe) should log this
        loudly; the database row has already been committed
        by the time this is called, so the consent itself is
        not lost, but the mirror is now out of sync and that
        needs attention.
        """
        try:
            with _lock:
                data = self._load()

                if "consents" not in data:
                    data["consents"] = {}

                data["consents"][str(consent_id)] = {
                    "consent_id": str(consent_id),
                    "user_id": str(user_id),
                    "user_email_snapshot": user_email_snapshot,
                    "recipe_id": str(recipe_id),
                    "recipe_title_snapshot": recipe_title_snapshot,
                    "flagged_allergens": flagged_allergens,
                    "warning_text_shown": warning_text_shown,
                    "confirmed_at": datetime.now(timezone.utc).isoformat(),
                }
                data["last_updated"] = datetime.now(timezone.utc).isoformat()

                self._save_atomic(data)
        except ConsentLedgerWriteError:
            raise
        except Exception as e:
            raise ConsentLedgerWriteError(
                f"Failed to write consent record {consent_id} to consent_ledger.json: {e}"
            ) from e
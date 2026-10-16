"""
=========================================================
AIMeals Backend
Auth Service

Responsibilities:
    - Orchestrate registration, login, token refresh, and logout
    - Orchestrate OTP-based signup (request + verify)
    - Contains ALL business logic for authentication
    - Framework-agnostic: raises custom exceptions, knows
      nothing about HTTP status codes

Dependencies:
    - app.repositories.user_repository.UserRepository
    - app.repositories.refresh_token_repository.RefreshTokenRepository
    - app.repositories.email_verification_repository.EmailVerificationRepository
    - app.services.subscription_service.SubscriptionService
    - app.core.security
    - app.core.email
    - app.core.exceptions
    - app.schemas.user.UserCreate
    - app.schemas.auth.Token
    - app.schemas.email_verification.RequestSignupOTP, VerifySignupOTP

Notes:
    - register() creates a default Free-tier Subscription
      immediately after creating the User row. Without this,
      a new user has no Subscription at all, and
      SubscriptionService.check_and_consume_credit() treats
      "no subscription" as InsufficientCreditsError — meaning
      a newly registered user could never use any AI feature,
      not "runs out of credits" but zero credits from day one.
      This was a real gap found during Phase 9 work, not
      present in earlier live testing because the existing
      test fixture already had a Subscription row from before
      this gap was introduced.
    - verify_signup_otp() is an ALTERNATE path to the exact
      same account-creation outcome as register() (same
      hash_password/create_user/create_default_subscription
      sequence) — register() itself is completely unchanged
      and still works exactly as before. verify_signup_otp()
      additionally issues tokens immediately (auto-login),
      unlike register(), since by that point the person has
      already proven their email and set a password in one
      combined step, so there's no reason to make them log in
      again right after.
    - InvalidOTPError is defined locally in this module rather
      than in app.core.exceptions, since this session never
      had that file's contents to safely extend blindly.
      Functionally identical either way.

Example usage:
    from app.services.auth_service import AuthService

    service = AuthService(db)
    user = service.register(user_create_payload)
    tokens = service.login(email, password)
=========================================================
"""

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import (
    AccountDisabledError,
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    InvalidTokenError,
)
from app.core.email import send_otp_email
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    verify_password,
    decode_token,
)
from app.models.user import User
from app.repositories.email_verification_repository import EmailVerificationRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.used_email_repository import UsedEmailRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import Token
from app.schemas.email_verification import RequestSignupOTP, VerifySignupOTP
from app.schemas.password_reset import ForgotPasswordRequest, ResetPasswordRequest
from app.schemas.user import UserCreate
from app.services.subscription_service import SubscriptionService


# =========================================================
# OTP Signup Constants
# =========================================================

OTP_EXPIRY_MINUTES = 10
MAX_OTP_ATTEMPTS = 5


# =========================================================
# OTP-Specific Exception
# =========================================================

class InvalidOTPError(Exception):
    """
    Raised when an OTP is missing (never requested, or already
    consumed), expired, has exceeded MAX_OTP_ATTEMPTS, or does
    not match what was stored. See module notes on why this
    lives here rather than in app.core.exceptions.
    """
    pass


class AccountDeletionError(Exception):
    """
    Raised when account deletion fails at the database level —
    specifically, an IntegrityError, which almost certainly
    means some table with a foreign key to users.id is missing
    ON DELETE CASCADE. The message includes the raw database
    error so it's immediately clear which table needs fixing,
    rather than surfacing a generic 500. See
    delete_account()'s docstring for the full reasoning.
    """
    pass


# =========================================================
# Auth Service
# =========================================================

class AuthService:
    """
    Contains the business logic for authentication.
    """

    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.token_repo = RefreshTokenRepository(db)
        self.email_verification_repo = EmailVerificationRepository(db)
        self.used_email_repo = UsedEmailRepository(db)
        self.subscription_service = SubscriptionService(db)

    # ---------------------------------------------------
    # Internal Helper — Anti-Abuse Credit Provisioning
    # ---------------------------------------------------

    def _provision_new_account_credits(self, user: User) -> None:
        """
        Creates the new user's default Subscription — the SAME
        outcome register() always had, EXCEPT if this email has
        a prior deletion on record (tracked by UsedEmail, which
        deliberately survives account deletion — see that
        model's own docstring), the credit allowance resumes at
        exactly whatever balance remained when that account was
        deleted, instead of the normal fresh Free-tier default.
        Prevents delete-account-then-resignup-with-same-email
        from being a way to gain credits (you can never end up
        with more than you had), while not unfairly zeroing out
        credits for someone who deletes for a legitimate reason
        (you never lose ones you hadn't used either).

        Called by both register() and verify_signup_otp() —
        the two real account-creation paths.
        """
        email_hash = hash_token(user.email.strip().lower())
        prior_record = self.used_email_repo.get_by_email_hash(email_hash)

        self.subscription_service.create_default_subscription(
            user.id,
            credit_allowance_override=prior_record.remaining_credits if prior_record else None,
        )

    # ---------------------------------------------------
    # Registration
    # ---------------------------------------------------

    def register(self, user_data: UserCreate) -> User:
        """
        Registers a new user and provisions their default
        Free-tier subscription, so every user has a working
        AI credit allowance from the moment they sign up.

        Raises:
            EmailAlreadyExistsError: if the email is already registered.
        """
        existing = self.user_repo.get_by_email(user_data.email)
        if existing is not None:
            raise EmailAlreadyExistsError(
                f"An account with email '{user_data.email}' already exists."
            )

        hashed = hash_password(user_data.password)

        new_user = self.user_repo.create_user(
            email=user_data.email,
            hashed_password=hashed,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
        )

        # Every user needs a Subscription row to use any AI
        # feature — check_and_consume_credit() treats a missing
        # subscription as InsufficientCreditsError, not as "no
        # limit" or "unlimited". Provisioning it here, right at
        # registration, means this is never a state a real user
        # can end up in. Also handles anti-abuse credit
        # provisioning — see _provision_new_account_credits().
        self._provision_new_account_credits(new_user)

        return new_user

    # ---------------------------------------------------
    # OTP Signup — Step 1: Request Code
    # ---------------------------------------------------

    def request_signup_otp(self, payload: RequestSignupOTP) -> None:
        """
        Step 1 of OTP-based signup. Generates a 6-digit code,
        stores it hashed with a short expiry, and emails it.
        Does NOT create a User or Subscription — nothing
        permanent happens until verify_signup_otp() succeeds.

        Any previous unconsumed OTP for this email is cleared
        first, so only the most recently requested code is
        ever valid (prevents an old, possibly-leaked code from
        a prior attempt staying usable).

        Raises:
            EmailAlreadyExistsError: if a real account with
                this email already exists.
        """
        existing = self.user_repo.get_by_email(payload.email)
        if existing is not None:
            raise EmailAlreadyExistsError(
                f"An account with email '{payload.email}' already exists."
            )

        self.email_verification_repo.delete_all_for_email(payload.email)

        otp_code = f"{secrets.randbelow(1_000_000):06d}"
        otp_hash = hash_token(otp_code)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)

        self.email_verification_repo.create(
            email=payload.email,
            otp_hash=otp_hash,
            first_name=payload.first_name,
            last_name=payload.last_name,
            expires_at=expires_at,
        )

        send_otp_email(payload.email, otp_code, payload.first_name)

    # ---------------------------------------------------
    # OTP Signup — Step 2: Verify + Create Account
    # ---------------------------------------------------

    def verify_signup_otp(self, payload: VerifySignupOTP) -> Token:
        """
        Step 2 of OTP-based signup. Verifies the code, then —
        only on success — performs exactly the same account
        creation as register() (hash password, create User,
        provision default Subscription), then issues tokens
        immediately (auto-login), unlike register().

        Raises:
            InvalidOTPError: no pending OTP exists for this
                email (never requested, or already consumed),
                it's expired, too many incorrect attempts have
                been made, or the code doesn't match.
            EmailAlreadyExistsError: a real account with this
                email was created in the meantime (e.g. a
                second attempt completed registration first) —
                closes a rare race between request and verify.
        """
        row = self.email_verification_repo.get_latest_by_email(payload.email)

        if row is None:
            raise InvalidOTPError(
                "No verification code was requested for this email, or it has already been used."
            )

        if row.attempts >= MAX_OTP_ATTEMPTS:
            raise InvalidOTPError("Too many incorrect attempts. Please request a new code.")

        now = datetime.now(timezone.utc)
        expires_at = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=timezone.utc)
        if now > expires_at:
            raise InvalidOTPError("This code has expired. Please request a new one.")

        if hash_token(payload.otp_code) != row.otp_hash:
            self.email_verification_repo.increment_attempts(row)
            raise InvalidOTPError("Incorrect code. Please try again.")

        # Re-check uniqueness right before creating — closes the
        # rare race described above.
        existing = self.user_repo.get_by_email(payload.email)
        if existing is not None:
            self.email_verification_repo.delete(row)
            raise EmailAlreadyExistsError(
                f"An account with email '{payload.email}' already exists."
            )

        hashed = hash_password(payload.password)
        new_user = self.user_repo.create_user(
            email=payload.email,
            hashed_password=hashed,
            first_name=row.first_name,
            last_name=row.last_name,
        )
        self._provision_new_account_credits(new_user)

        # Consume the OTP — it can never be reused.
        self.email_verification_repo.delete(row)

        return self._issue_tokens(new_user)

    # ---------------------------------------------------
    # Authentication
    # ---------------------------------------------------

    def authenticate(self, email: str, password: str) -> User:
        """
        Verifies email/password credentials.

        Raises:
            InvalidCredentialsError: if email/password do not match.
            AccountDisabledError: if the account exists but is inactive.

        Note:
            Deliberately raises the SAME error for "email not found"
            and "wrong password" — revealing which one occurred would
            let an attacker enumerate valid emails.
        """
        user = self.user_repo.get_by_email(email)

        if user is None or not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError("Invalid email or password.")

        if not user.is_active:
            raise AccountDisabledError("This account has been disabled.")

        return user

    # ---------------------------------------------------
    # Login
    # ---------------------------------------------------

    def login(self, email: str, password: str) -> Token:
        """
        Authenticates a user and issues a new access/refresh token pair.
        """
        user = self.authenticate(email, password)
        return self._issue_tokens(user)

    # ---------------------------------------------------
    # Token Refresh (with rotation)
    # ---------------------------------------------------

    def refresh_access_token(self, raw_refresh_token: str) -> Token:
        """
        Validates a refresh token and issues a new token pair.

        Implements refresh token rotation: the old refresh token
        is revoked and a new one is issued alongside the new
        access token. This limits the damage if a refresh token
        is ever stolen — reuse of a revoked token is detectable.

        Raises:
            InvalidTokenError: if the token is invalid, expired,
                revoked, or does not belong to an active user.
        """
        payload = decode_token(raw_refresh_token)

        if payload is None or payload.get("type") != "refresh":
            raise InvalidTokenError("Invalid or expired refresh token.")

        token_hash = hash_token(raw_refresh_token)
        token_row = self.token_repo.get_by_hash(token_hash)

        if token_row is None or token_row.revoked:
            raise InvalidTokenError("Refresh token has been revoked or does not exist.")

        user = self.user_repo.get_by_id(token_row.user_id)

        if user is None or not user.is_active:
            raise InvalidTokenError("Refresh token does not belong to an active user.")

        # Rotate: revoke the old token before issuing new ones
        self.token_repo.revoke(token_row)

        return self._issue_tokens(user)

    # ---------------------------------------------------
    # Logout
    # ---------------------------------------------------

    def logout(self, raw_refresh_token: str) -> None:
        """
        Revokes a refresh token, effectively logging the user out.

        Silently does nothing if the token does not exist or is
        already revoked — logout should be idempotent and should
        never leak whether a token was valid.
        """
        token_hash = hash_token(raw_refresh_token)
        token_row = self.token_repo.get_by_hash(token_hash)

        if token_row is not None and not token_row.revoked:
            self.token_repo.revoke(token_row)

    # ---------------------------------------------------
    # Account Deletion
    # ---------------------------------------------------

    def request_account_deletion_otp(self, user_id: uuid.UUID, password: str) -> None:
        """
        Step 1 of account deletion. Verifies the password, and
        only if correct, sends a 6-digit OTP to the account's
        own email — reusing the exact same email_verifications
        mechanism built for signup (see request_signup_otp()).
        Nothing is deleted yet.

        Raises:
            InvalidCredentialsError: if the password is wrong.
        """
        user = self.user_repo.get_by_id(user_id)

        if user is None or not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError("Invalid email or password.")

        self.email_verification_repo.delete_all_for_email(user.email)

        otp_code = f"{secrets.randbelow(1_000_000):06d}"
        otp_hash = hash_token(otp_code)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)

        # first_name/last_name are staged here purely to satisfy
        # email_verifications' schema (built for signup, where
        # those fields matter) — unused for deletion, since the
        # user already exists.
        self.email_verification_repo.create(
            email=user.email,
            otp_hash=otp_hash,
            first_name=user.first_name,
            last_name=user.last_name,
            expires_at=expires_at,
        )

        send_otp_email(user.email, otp_code, user.first_name)

    def confirm_account_deletion(self, user_id: uuid.UUID, otp_code: str) -> None:
        """
        Step 2 of account deletion. Verifies the OTP sent by
        request_account_deletion_otp(), and only on success,
        permanently deletes the account and, via database-level
        ON DELETE CASCADE foreign keys, every piece of data
        tied to it. Hard delete — no recovery path once this
        succeeds.

        Deliberately does NOT rely on this codebase's own ORM-
        level relationship() cascade config (the User model
        defines none) — it relies entirely on each child
        table's own database-level ON DELETE CASCADE, which is
        how every table built during this AI-assisted session
        was actually configured. Tables that predate this
        session were not all individually verified to follow
        the same convention. Rather than risk a silent partial
        deletion, a failure here is deliberately loud: see the
        IntegrityError handling below.

        Raises:
            InvalidOTPError: no pending OTP exists for this
                account (never requested, or already consumed),
                it's expired, too many incorrect attempts have
                been made, or the code doesn't match.
            AccountDeletionError: if the delete fails at the
                database level — almost certainly an
                IntegrityError from a table whose foreign key
                to users.id is missing ON DELETE CASCADE. The
                raw database error is included in the message
                so the exact table is immediately identifiable,
                rather than surfacing a generic 500.
        """
        user = self.user_repo.get_by_id(user_id)
        if user is None:
            raise InvalidOTPError("No pending deletion request found.")

        row = self.email_verification_repo.get_latest_by_email(user.email)

        if row is None:
            raise InvalidOTPError(
                "No verification code was requested, or it has already been used."
            )

        if row.attempts >= MAX_OTP_ATTEMPTS:
            raise InvalidOTPError("Too many incorrect attempts. Please request a new code.")

        now = datetime.now(timezone.utc)
        expires_at = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=timezone.utc)
        if now > expires_at:
            raise InvalidOTPError("This code has expired. Please request a new one.")

        if hash_token(otp_code) != row.otp_hash:
            self.email_verification_repo.increment_attempts(row)
            raise InvalidOTPError("Incorrect code. Please try again.")

        self.email_verification_repo.delete(row)

        # Compute the unused credit balance BEFORE deleting —
        # the Subscription row is about to be cascade-deleted
        # along with the user, so this is the last chance to
        # read it. Deliberately NOT written to used_emails yet:
        # if the delete below fails (see IntegrityError
        # handling), the account still exists, and writing this
        # now would incorrectly show a reduced balance for an
        # account that was never actually deleted.
        email_hash = hash_token(user.email.strip().lower())
        remaining_credits = self.subscription_service.get_available_credits(user.id)

        try:
            self.db.delete(user)
            self.db.commit()
        except IntegrityError as e:
            self.db.rollback()
            raise AccountDeletionError(
                f"Account deletion failed — a related table's foreign key to "
                f"users.id is likely missing ON DELETE CASCADE. Raw error: {e}"
            ) from e

        # Only reaches here once the delete has actually
        # succeeded — now it's safe to record the balance for
        # restoration on resignup.
        self.used_email_repo.upsert(email_hash, remaining_credits)

    # ---------------------------------------------------
    # Password Reset ("Forgot Password")
    # ---------------------------------------------------

    def request_password_reset(self, payload: ForgotPasswordRequest) -> None:
        """
        Step 1 of "forgot password". Sends a 6-digit OTP to the
        given email, reusing the exact same email_verifications
        mechanism as signup and account deletion (see
        request_signup_otp() / request_account_deletion_otp()).

        Deliberately does NOT raise, and behaves IDENTICALLY,
        whether or not an account exists for this email -- this
        is the one OTP flow in this app where revealing email
        registration status would be a real vulnerability
        (unlike signup, which explicitly WANTS to tell you an
        email is already taken). The route always returns the
        same generic success response regardless of what
        happens in here.

        Note: like request_account_deletion_otp(), this clears
        any other pending OTP for this email first (shared
        table) -- so requesting a password reset invalidates an
        in-flight signup or account-deletion OTP for the same
        email, and vice versa. Accepted as-is, matching the
        existing account-deletion reuse of this same mechanism.
        """
        user = self.user_repo.get_by_email(payload.email)
        if user is None:
            return

        self.email_verification_repo.delete_all_for_email(user.email)

        otp_code = f"{secrets.randbelow(1_000_000):06d}"
        otp_hash = hash_token(otp_code)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)

        # first_name/last_name staged purely to satisfy the
        # shared table's schema -- unused here, same as
        # request_account_deletion_otp().
        self.email_verification_repo.create(
            email=user.email,
            otp_hash=otp_hash,
            first_name=user.first_name,
            last_name=user.last_name,
            expires_at=expires_at,
        )

        send_otp_email(user.email, otp_code, user.first_name)

    def confirm_password_reset(self, payload: ResetPasswordRequest) -> Token:
        """
        Step 2 of "forgot password". Verifies the OTP, and only
        on success, sets the new password and issues fresh
        tokens immediately (auto-login) -- same UX precedent as
        verify_signup_otp().

        The email->user lookup happens AFTER the OTP checks
        below (not before), so a non-existent email produces
        exactly the same "no pending OTP" outcome an existing-
        but-never-requested email would (request_password_reset()
        never created a row for an email with no account) --
        no separate code path that could leak registration
        status by its error message or timing.

        Raises:
            InvalidOTPError: no pending OTP for this email, it's
                expired, too many incorrect attempts, or the
                code doesn't match.
        """
        row = self.email_verification_repo.get_latest_by_email(payload.email)

        if row is None:
            raise InvalidOTPError(
                "No verification code was requested for this email, or it has already been used."
            )

        if row.attempts >= MAX_OTP_ATTEMPTS:
            raise InvalidOTPError("Too many incorrect attempts. Please request a new code.")

        now = datetime.now(timezone.utc)
        expires_at = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=timezone.utc)
        if now > expires_at:
            raise InvalidOTPError("This code has expired. Please request a new one.")

        if hash_token(payload.otp_code) != row.otp_hash:
            self.email_verification_repo.increment_attempts(row)
            raise InvalidOTPError("Incorrect code. Please try again.")

        user = self.user_repo.get_by_email(payload.email)
        if user is None:
            # Should be unreachable -- a row only ever gets created for
            # a real user (see request_password_reset()) -- but handled
            # defensively rather than assuming it can't happen.
            self.email_verification_repo.delete(row)
            raise InvalidOTPError("Invalid or expired code.")

        hashed = hash_password(payload.new_password)
        self.user_repo.update_password(user, hashed)

        # Consume the OTP -- it can never be reused.
        self.email_verification_repo.delete(row)

        return self._issue_tokens(user)

    # ---------------------------------------------------
    # Internal Helper
    # ---------------------------------------------------

    def _issue_tokens(self, user: User) -> Token:
        """
        Issues a new access + refresh token pair for a user,
        and stores the refresh token's hash in the database.
        """
        access_token = create_access_token(
            subject=str(user.id),
            extra_claims={"role": user.role.value},
        )

        raw_refresh_token, expires_at = create_refresh_token(subject=str(user.id))
        token_hash = hash_token(raw_refresh_token)

        self.token_repo.create(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )

        return Token(
            access_token=access_token,
            refresh_token=raw_refresh_token,
            token_type="bearer",
        )
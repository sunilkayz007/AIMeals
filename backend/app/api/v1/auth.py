"""
=========================================================
AIMeals Backend
Auth API Routes

Endpoints:
    POST /api/v1/auth/register              - create a new account (unchanged, one-step)
    POST /api/v1/auth/register/request-otp  - OTP signup step 1: email a 6-digit code
    POST /api/v1/auth/register/verify-otp   - OTP signup step 2: verify + set password + auto-login
    POST /api/v1/auth/login                 - authenticate, receive tokens
    POST /api/v1/auth/refresh               - rotate tokens
    POST /api/v1/auth/logout                - revoke a refresh token
    GET  /api/v1/auth/me                    - return the current user (protected)
    POST /api/v1/auth/forgot-password       - password reset step 1: email a 6-digit code
    POST /api/v1/auth/reset-password        - password reset step 2: verify + set new password + auto-login

Dependencies:
    - app.controller.auth_controller.AuthController
    - app.core.dependencies.get_current_user
    - app.B_database.get_db

Notes:
    - /register is completely unchanged — the OTP endpoints
      are an alternate path to account creation, not a
      replacement. Both can coexist.
    - /register/verify-otp returns Token (auto-login), unlike
      /register which returns UserOut and expects a separate
      /login call — see AuthService.verify_signup_otp()'s
      docstring for why.
    - /forgot-password ALWAYS returns 204 regardless of whether
      the email is registered — see AuthService.request_password_reset()'s
      docstring for the anti-enumeration reasoning. /reset-password
      returns Token (auto-login), same precedent as /register/verify-otp.
=========================================================
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.B_database import get_db
from app.controller.auth_controller import AuthController
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import RefreshTokenRequest, Token, UserLogin
from app.schemas.email_verification import RequestSignupOTP, VerifySignupOTP
from app.schemas.password_reset import ForgotPasswordRequest, ResetPasswordRequest
from app.schemas.user import UserCreate, UserOut

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


class DeleteAccountRequest(BaseModel):
    """
    Shape of the payload accepted by POST /auth/me/request-deletion-otp.
    Kept here directly (not in schemas/auth.py, which this
    session never had access to) since it's a single required
    field.
    """
    password: str


class ConfirmAccountDeletionRequest(BaseModel):
    """
    Shape of the payload accepted by DELETE /auth/me.
    """
    otp_code: str


# =========================================================
# Register
# =========================================================

@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> UserOut:
    """
    Creates a new user account.
    """
    controller = AuthController(db)
    return controller.register(payload)


# =========================================================
# OTP Signup — Step 1: Request Code
# =========================================================

@router.post(
    "/register/request-otp",
    status_code=status.HTTP_204_NO_CONTENT,
)
def request_signup_otp(payload: RequestSignupOTP, db: Session = Depends(get_db)) -> None:
    """
    Sends a 6-digit verification code to the given email.
    Creates no account yet — see /register/verify-otp.
    """
    controller = AuthController(db)
    controller.request_signup_otp(payload)


# =========================================================
# OTP Signup — Step 2: Verify + Create Account
# =========================================================

@router.post(
    "/register/verify-otp",
    response_model=Token,
    status_code=status.HTTP_200_OK,
)
def verify_signup_otp(payload: VerifySignupOTP, db: Session = Depends(get_db)) -> Token:
    """
    Verifies the code and, only on success, creates the real
    account and issues tokens immediately (auto-login).
    """
    controller = AuthController(db)
    return controller.verify_signup_otp(payload)


# =========================================================
# Login
# =========================================================

@router.post(
    "/login",
    response_model=Token,
    status_code=status.HTTP_200_OK,
)
def login(payload: UserLogin, db: Session = Depends(get_db)) -> Token:
    """
    Authenticates a user and returns an access/refresh token pair.
    """
    controller = AuthController(db)
    return controller.login(payload)


# =========================================================
# Refresh
# =========================================================

@router.post(
    "/refresh",
    response_model=Token,
    status_code=status.HTTP_200_OK,
)
def refresh(payload: RefreshTokenRequest, db: Session = Depends(get_db)) -> Token:
    """
    Rotates a refresh token and returns a new access/refresh token pair.
    """
    controller = AuthController(db)
    return controller.refresh(payload.refresh_token)


# =========================================================
# Logout
# =========================================================

@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
def logout(payload: RefreshTokenRequest, db: Session = Depends(get_db)) -> None:
    """
    Revokes a refresh token, logging the user out.
    """
    controller = AuthController(db)
    controller.logout(payload.refresh_token)


# =========================================================
# Current User (Protected)
# =========================================================

@router.get(
    "/me",
    response_model=UserOut,
    status_code=status.HTTP_200_OK,
)
def read_current_user(current_user: User = Depends(get_current_user)) -> UserOut:
    """
    Returns the currently authenticated user.

    Requires a valid access token in the Authorization header:
        Authorization: Bearer <access_token>
    """
    return UserOut.model_validate(current_user)


# =========================================================
# Request Account Deletion OTP (Protected)
# =========================================================

@router.post(
    "/me/request-deletion-otp",
    status_code=status.HTTP_204_NO_CONTENT,
)
def request_deletion_otp(
    payload: DeleteAccountRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """
    Step 1 of account deletion. Verifies the password, and
    only if correct, emails a 6-digit code to confirm deletion.
    Nothing is deleted yet.
    """
    controller = AuthController(db)
    controller.request_deletion_otp(current_user.id, payload.password)


# =========================================================
# Confirm Account Deletion (Protected)
# =========================================================

@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
)
def confirm_account_deletion(
    payload: ConfirmAccountDeletionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """
    Step 2 of account deletion. Verifies the code sent by
    /me/request-deletion-otp, and only on success, permanently
    deletes the account and all associated data. Irreversible.
    """
    controller = AuthController(db)
    controller.confirm_account_deletion(current_user.id, payload.otp_code)


# =========================================================
# Forgot Password — Step 1: Request Code
# =========================================================

@router.post(
    "/forgot-password",
    status_code=status.HTTP_204_NO_CONTENT,
)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)) -> None:
    """
    Sends a 6-digit reset code to the given email, if an account
    exists for it. Always returns 204 regardless of whether the
    email is registered — see AuthService.request_password_reset()'s
    docstring for the anti-enumeration reasoning.
    """
    controller = AuthController(db)
    controller.request_password_reset(payload)


# =========================================================
# Forgot Password — Step 2: Verify + Set New Password
# =========================================================

@router.post(
    "/reset-password",
    response_model=Token,
    status_code=status.HTTP_200_OK,
)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)) -> Token:
    """
    Verifies the reset code and, only on success, sets the new
    password and issues tokens immediately (auto-login) — same
    precedent as /register/verify-otp.
    """
    controller = AuthController(db)
    return controller.confirm_password_reset(payload)
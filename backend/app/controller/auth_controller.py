"""
=========================================================
AIMeals Backend
Auth Controller

Responsibilities:
    - Orchestrate calls to AuthService
    - Translate framework-agnostic service exceptions into
      HTTPException with correct status codes
    - Convert SQLAlchemy models into Pydantic response schemas

Dependencies:
    - app.services.auth_service.AuthService
    - app.core.exceptions

Notes:
    - Controllers contain NO business logic. They orchestrate
      and translate only. All actual logic lives in the
      service layer.
=========================================================
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.exceptions import (
    AccountDisabledError,
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    InvalidTokenError,
)
from app.schemas.auth import Token, UserLogin
from app.schemas.email_verification import RequestSignupOTP, VerifySignupOTP
from app.schemas.password_reset import ForgotPasswordRequest, ResetPasswordRequest
from app.schemas.user import UserCreate, UserOut
from app.services.auth_service import AuthService, AccountDeletionError, InvalidOTPError


# =========================================================
# Auth Controller
# =========================================================

class AuthController:
    """
    Thin orchestration layer between API routes and AuthService.
    """

    def __init__(self, db: Session):
        self.service = AuthService(db)

    # ---------------------------------------------------
    # Register
    # ---------------------------------------------------

    def register(self, payload: UserCreate) -> UserOut:
        try:
            user = self.service.register(payload)
        except EmailAlreadyExistsError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e),
            )

        return UserOut.model_validate(user)

    # ---------------------------------------------------
    # OTP Signup — Step 1: Request Code
    # ---------------------------------------------------

    def request_signup_otp(self, payload: RequestSignupOTP) -> None:
        try:
            self.service.request_signup_otp(payload)
        except EmailAlreadyExistsError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e),
            )

    # ---------------------------------------------------
    # OTP Signup — Step 2: Verify + Create Account
    # ---------------------------------------------------

    def verify_signup_otp(self, payload: VerifySignupOTP) -> Token:
        try:
            return self.service.verify_signup_otp(payload)
        except InvalidOTPError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        except EmailAlreadyExistsError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e),
            )

    # ---------------------------------------------------
    # Login
    # ---------------------------------------------------

    def login(self, payload: UserLogin) -> Token:
        try:
            return self.service.login(payload.email, payload.password)
        except InvalidCredentialsError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
                headers={"WWW-Authenticate": "Bearer"},
            )
        except AccountDisabledError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e),
            )

    # ---------------------------------------------------
    # Refresh
    # ---------------------------------------------------

    def refresh(self, raw_refresh_token: str) -> Token:
        try:
            return self.service.refresh_access_token(raw_refresh_token)
        except InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
                headers={"WWW-Authenticate": "Bearer"},
            )

    # ---------------------------------------------------
    # Logout
    # ---------------------------------------------------

    def logout(self, raw_refresh_token: str) -> None:
        # Logout is intentionally silent on invalid/missing tokens —
        # see AuthService.logout() docstring for reasoning.
        self.service.logout(raw_refresh_token)

    # ---------------------------------------------------
    # Delete Account
    # ---------------------------------------------------

    def request_deletion_otp(self, user_id, password: str) -> None:
        try:
            self.service.request_account_deletion_otp(user_id, password)
        except InvalidCredentialsError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
                headers={"WWW-Authenticate": "Bearer"},
            )

    def confirm_account_deletion(self, user_id, otp_code: str) -> None:
        try:
            self.service.confirm_account_deletion(user_id, otp_code)
        except InvalidOTPError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        except AccountDeletionError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e),
            )

    # ---------------------------------------------------
    # Password Reset ("Forgot Password")
    # ---------------------------------------------------

    def request_password_reset(self, payload: ForgotPasswordRequest) -> None:
        # Deliberately no exception translation here -- the service
        # method never raises, by design (see its docstring for the
        # anti-enumeration reasoning).
        self.service.request_password_reset(payload)

    def confirm_password_reset(self, payload: ResetPasswordRequest) -> Token:
        try:
            return self.service.confirm_password_reset(payload)
        except InvalidOTPError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
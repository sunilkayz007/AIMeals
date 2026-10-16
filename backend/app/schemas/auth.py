"""
=========================================================
AIMeals Backend
Auth Schemas

Responsibilities:
    - Define request/response shapes for login and tokens

Example usage:
    from app.schemas.auth import UserLogin, Token

    def login(payload: UserLogin) -> Token:
        ...
=========================================================
"""

from pydantic import BaseModel, EmailStr


# =========================================================
# Request Schema — Login
# =========================================================

class UserLogin(BaseModel):
    """
    Shape of the payload accepted by POST /login.
    """

    email: EmailStr
    password: str


# =========================================================
# Request Schema — Refresh / Logout
# =========================================================

class RefreshTokenRequest(BaseModel):
    """
    Shape of the payload accepted by POST /refresh and POST /logout.
    """

    refresh_token: str


# =========================================================
# Response Schema — Issued Tokens
# =========================================================

class Token(BaseModel):
    """
    Shape of the token pair returned on successful
    login or refresh.
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# =========================================================
# Internal Schema — Decoded Token Payload
# =========================================================

class TokenPayload(BaseModel):
    """
    Represents the decoded claims of a JWT.

    Used internally by dependencies (e.g. get_current_user)
    to validate and read token contents. Never returned
    directly to the client.
    """

    sub: str
    exp: int
    type: str
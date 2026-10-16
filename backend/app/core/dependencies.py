"""
=========================================================
AIMeals Backend
Core Dependencies

Responsibilities:
    - Provide FastAPI dependencies for route protection
    - Resolve the Authorization header into a User
    - Enforce role-based access (admin-only routes)

Dependencies:
    - app.core.security.decode_token
    - app.repositories.user_repository.UserRepository
    - app.B_database.get_db

Notes:
    - This is the correct boundary for translating internal
      auth failures into HTTP responses (401 / 403). The
      service layer stays framework-agnostic; this file is
      where FastAPI-specific concerns are allowed.

Example usage:
    from app.core.dependencies import get_current_user

    @router.get("/me")
    def read_me(current_user: User = Depends(get_current_user)):
        return current_user
=========================================================
"""

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.B_database import get_db
from app.core.security import decode_token
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository

# =========================================================
# Bearer Token Scheme
# =========================================================

# auto_error=True means FastAPI automatically returns 401
# if the Authorization header is missing entirely.
_bearer_scheme = HTTPBearer(auto_error=True)


# =========================================================
# Current User Dependency
# =========================================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Resolves the Authorization: Bearer <token> header into a User.

    Raises:
        HTTPException 401: if the token is missing, invalid,
            expired, not an access token, or the user no
            longer exists / is inactive.

    Usage:
        @router.get("/protected")
        def protected_route(current_user: User = Depends(get_current_user)):
            ...
    """
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(credentials.credentials)

    if payload is None or payload.get("type") != "access":
        raise unauthorized

    user_id_raw = payload.get("sub")
    if user_id_raw is None:
        raise unauthorized

    try:
        user_id = uuid.UUID(user_id_raw)
    except ValueError:
        raise unauthorized

    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)

    if user is None or not user.is_active:
        raise unauthorized

    return user


# =========================================================
# Current Admin User Dependency
# =========================================================

def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Builds on get_current_user, additionally requiring
    the user to have the ADMIN role.

    Raises:
        HTTPException 403: if the user is authenticated
            but not an admin.

    Usage:
        @router.delete("/admin/users/{id}")
        def admin_route(current_user: User = Depends(get_current_admin_user)):
            ...
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires administrator privileges.",
        )

    return current_user
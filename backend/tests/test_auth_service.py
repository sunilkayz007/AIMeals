from app.B_database import SessionLocal
from app.services.auth_service import AuthService
from app.schemas.user import UserCreate
from app.core.exceptions import EmailAlreadyExistsError, InvalidCredentialsError, InvalidTokenError

db = SessionLocal()
service = AuthService(db)

TEST_EMAIL = "authflow@example.com"
TEST_PASSWORD = "TestPass123"

# --- Register (or skip if already exists) ---
try:
    user = service.register(UserCreate(
        email=TEST_EMAIL,
        password=TEST_PASSWORD,
        first_name="Auth",
        last_name="Flow",
    ))
    print("Registered:", user)
except EmailAlreadyExistsError:
    print("User already registered, continuing.")

# --- Login ---
tokens = service.login(TEST_EMAIL, TEST_PASSWORD)
print("\nLogin successful.")
print("Access token (first 40 chars):", tokens.access_token[:40], "...")
print("Refresh token (first 40 chars):", tokens.refresh_token[:40], "...")

old_refresh_token = tokens.refresh_token

# --- Wrong password should fail ---
try:
    service.login(TEST_EMAIL, "WrongPassword123")
    print("\nERROR: wrong password was incorrectly accepted")
except InvalidCredentialsError:
    print("\nWrong password correctly rejected.")

# --- Refresh (rotates the token) ---
new_tokens = service.refresh_access_token(old_refresh_token)
print("\nRefresh successful. New refresh token issued (rotation working).")

# --- Reusing the OLD refresh token should now fail ---
try:
    service.refresh_access_token(old_refresh_token)
    print("ERROR: old (rotated) refresh token was incorrectly accepted")
except InvalidTokenError:
    print("Old refresh token correctly rejected after rotation.")

# --- Logout using the NEW refresh token ---
service.logout(new_tokens.refresh_token)
print("\nLogged out.")

# --- Using the token after logout should now fail ---
try:
    service.refresh_access_token(new_tokens.refresh_token)
    print("ERROR: refresh token still worked after logout")
except InvalidTokenError:
    print("Refresh token correctly rejected after logout.")

db.close()
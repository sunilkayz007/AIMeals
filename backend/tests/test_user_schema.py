from app.schemas.user import UserCreate
from app.schemas.auth import UserLogin, Token

# Valid case
valid = UserCreate(email="jane@example.com", password="Secret123", first_name="Jane", last_name="Doe")
print("Valid user created:", valid)

# Invalid case — should raise a validation error
try:
    UserCreate(email="jane@example.com", password="weak", first_name="Jane", last_name="Doe")
    print("ERROR: weak password was incorrectly accepted")
except Exception as e:
    print("Weak password correctly rejected:", str(e).splitlines()[0])

login = UserLogin(email="jane@example.com", password="whatever")
print("Login schema works:", login)

token = Token(access_token="abc", refresh_token="def")
print("Token schema works:", token)
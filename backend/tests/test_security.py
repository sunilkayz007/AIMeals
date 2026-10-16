from app.core.security import hash_password, verify_password, create_access_token, decode_token

hashed = hash_password("testpass123")
print("Hash works:", verify_password("testpass123", hashed))
print("Wrong pass rejected:", not verify_password("wrongpass", hashed))

token = create_access_token(subject="1")
payload = decode_token(token)
print("Token payload:", payload)
from app.B_database import Base, engine
from app.models.user import User, UserRole

# Just verify the model is registered with Base metadata
print("Tables registered:", list(Base.metadata.tables.keys()))
print("User role enum values:", [r.value for r in UserRole])
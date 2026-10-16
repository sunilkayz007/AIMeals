from sqlalchemy import create_engine, text
from app.A_config import settings

print(settings.DATABASE_URL)

try:
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        version = conn.execute(text("SELECT version()")).scalar()
    print("\n✅ SUCCESS")
    print(version)
except Exception as e:
    print("\n❌ FAILED")
    print(type(e))
    print(e)
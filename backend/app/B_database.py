"""
=========================================================
AIMeals Backend
Database Manager

Responsibilities:
    - Create SQLAlchemy Engine
    - Manage Connection Pool
    - Provide Database Sessions
    - Define Base Model Class
=========================================================
"""

from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.A_config import settings
from app.C_logger import app_logger


# =========================================================
# SQLAlchemy Base Class
# =========================================================

class Base(DeclarativeBase):
    """
    Base class for all database models.
    Every model should inherit from this class.
    """
    pass


# =========================================================
# Database Engine
# =========================================================

# Note: SQLAlchemy 2.x engines are "future-style" by default,
# so the future=True flag from 1.x is no longer needed.
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,
)


# =========================================================
# Session Factory
# =========================================================

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=Session,
)


# =========================================================
# Dependency for FastAPI
# =========================================================

def get_db() -> Generator[Session, None, None]:
    """
    Provides a database session.

    Usage:

        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()

    try:
        yield db

    except Exception:
        db.rollback()
        app_logger.exception("Database transaction rolled back.")
        raise

    finally:
        db.close()


# =========================================================
# Database Initialization
# =========================================================

def init_database() -> None:
    """
    Startup hook, called once from main.py's lifespan.

    UPDATE (Aug 31 2026): this USED to call
    Base.metadata.create_all(bind=engine) directly, per the
    original "During development we will use this. Later
    Alembic will manage migrations." comment. That "later" has
    arrived — the project now has a real, ongoing Alembic
    migration chain, and create_all() running on every app
    startup was found to silently auto-create tables for any
    newly-imported model (via app/models/__init__.py) OUTSIDE
    Alembic's tracking. Concretely: AdRewardTransaction's table
    got created by this call the first time the server ran
    after the model was added, and the very next
    `alembic upgrade head` then failed with DuplicateTable,
    because Alembic had no idea the table already existed.

    create_all() is intentionally NOT called anymore. Schema
    changes must go through an Alembic migration
    (`alembic upgrade head`) — that is now the single source of
    truth for the database schema, matching what
    app/models/__init__.py's own docstring already assumes
    (Alembic's --autogenerate reads target_metadata from that
    file). This function is kept (rather than removed and
    updating main.py's lifespan) purely as a clear place to log
    that startup happened; it does not touch the schema.
    """
    app_logger.info(
        "Database schema is managed by Alembic migrations "
        "(run `alembic upgrade head`) — init_database() no "
        "longer auto-creates tables."
    )


# =========================================================
# Connection Test Utility
# =========================================================

def test_database_connection() -> bool:
    """
    Test the database connection by executing a simple query.
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        app_logger.info("Database connection successful.")
        return True

    except Exception as e:
        app_logger.exception(f"Database connection failed: {e}")
        return False
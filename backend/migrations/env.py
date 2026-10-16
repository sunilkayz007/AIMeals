from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# =========================================================
# AIMeals: Import settings and models
# =========================================================
# These imports let Alembic:
#   1. Read DATABASE_URL from the same singleton settings
#      object the rest of the app uses (never hardcoded).
#   2. See every model class so --autogenerate can detect
#      schema changes. Same "must be imported to be seen"
#      rule that applies to Base.metadata.create_all().
#
# IMPORTANT: model imports go through app.models (the
# central registry — see that package's __init__.py
# docstring) rather than being individually listed here.
# This file previously hand-maintained its own separate
# import list, which drifted out of sync with app.models
# over time and was missing several real tables (DailyTip,
# AllergyGeneralFacts, AllergenInsight,
# UserAllergenDeepUnlock, WaterLog, Report/ReportComment,
# MealPlanChunk, EmailVerification,
# AllergenOverrideConsent, UsedEmail,
# MealConfirmationDismissal). Because --autogenerate only
# "sees" a table if its model class has been imported
# somewhere before target_metadata is read, that drift
# caused --autogenerate to think those tables didn't exist
# in the models and propose DROPping them — a real, nearly
# catastrophic bug caught before ever being applied. Using
# app.models here guarantees this file can never drift out
# of sync with the actual model set again.

from app.A_config import settings
from app.B_database import Base
import app.models  # noqa: F401  (imports every model class — see app/models/__init__.py)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Override the sqlalchemy.url from alembic.ini with the
# real DATABASE_URL from settings, so credentials live in
# exactly one place (.env), not duplicated into alembic.ini.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
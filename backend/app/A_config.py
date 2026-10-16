"""
=========================================================
AIMeals Backend
Configuration Manager

Purpose:
    - Load all application settings from .env
    - Provide a single configuration object to the project
=========================================================
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application Settings
    Values are loaded from .env if available.
    Otherwise the default values below are used.
    """

    # =====================================================
    # Application
    # =====================================================

    APP_NAME: str = "AIMeals"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # =====================================================
    # Security
    # =====================================================

    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    # =====================================================
    # Claude AI
    # =====================================================

    CLAUDE_API_KEY: str = ""
    CLAUDE_MODEL: str = "claude-sonnet-4-20250514"
    GMAIL_ADDRESS: str = ""
    GMAIL_APP_PASSWORD: str = ""

    # =====================================================
    # Database
    # =====================================================

    DATABASE_URL: str = ""

    # =====================================================
    # Logging
    # =====================================================

    LOG_LEVEL: str = "INFO"

    # =====================================================
    # Uploads
    # =====================================================

    MAX_UPLOAD_SIZE_MB: int = 20
    UPLOAD_FOLDER: str = "app/uploads"

    # =====================================================
    # RevenueCat
    # =====================================================

    # Shared secret configured in the RevenueCat dashboard
    # (Project Settings -> Integrations -> Webhooks -> Authorization
    # header value). RevenueCat sends this back as
    # "Authorization: Bearer <this value>" on every webhook POST —
    # it's the ONLY thing proving a request actually came from
    # RevenueCat (no signature scheme, unlike AdMob's SSV). Must be
    # set in .env before the webhook endpoint can accept anything;
    # left blank by default so a misconfigured deployment fails
    # closed (rejects every request) rather than silently accepting
    # unauthenticated ones.
    REVENUECAT_WEBHOOK_SECRET: str = ""

    # =====================================================
    # Pydantic Settings
    # =====================================================

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.

    Only one Settings object is created during
    the lifetime of the application.
    """
    return Settings()


# =========================================================
# Global Settings Object
# =========================================================

settings = get_settings()
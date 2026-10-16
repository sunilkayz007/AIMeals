from pathlib import Path
import sys

from loguru import logger

from app.A_config import Settings

settings = Settings()


# ----------------------------------------------------
# Create Logs Directory
# ----------------------------------------------------

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


# ----------------------------------------------------
# Remove Default Logger
# ----------------------------------------------------

logger.remove()


# ----------------------------------------------------
# Console Logger
# ----------------------------------------------------

logger.add(
    sys.stdout,
    level=settings.LOG_LEVEL,
    colorize=True,
    enqueue=True,
    backtrace=True,
    diagnose=True,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    ),
)


# ----------------------------------------------------
# File Logger
# ----------------------------------------------------

logger.add(
    LOG_DIR / "aimeals.log",
    rotation="1 day",
    retention="30 days",
    compression="zip",
    level=settings.LOG_LEVEL,
    enqueue=True,
    backtrace=True,
    diagnose=True,
    format=(
        "{time:YYYY-MM-DD HH:mm:ss} | "
        "{level} | "
        "{name}:{function}:{line} | "
        "{message}"
    ),
)


# ----------------------------------------------------
# Export Logger
# ----------------------------------------------------

app_logger = logger

if __name__ == "__main__":
    app_logger.info("Logger test successful.")
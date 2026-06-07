"""
app/core/logging.py
───────────────────
Loguru-based structured logging configuration.
Outputs human-readable logs in development, JSON in production.
"""
import sys
from typing import Any

from loguru import logger

from app.core.config import settings


def _dev_format(record: dict[str, Any]) -> str:
    """Rich, colorized format for development."""
    return (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>\n{exception}"
    )


def setup_logging() -> None:
    """
    Configure loguru sinks.

    - Development: human-readable, colorized stdout.
    - Production:  JSON-structured stdout (suitable for log aggregators).
    """
    logger.remove()  # Remove default handler

    if settings.is_production:
        logger.add(
            sys.stdout,
            level=settings.log_level,
            serialize=True,           # JSON output
            backtrace=False,
            diagnose=False,
            enqueue=True,             # Thread-safe async-safe logging
        )
    else:
        logger.add(
            sys.stdout,
            level=settings.log_level,
            format=_dev_format,
            colorize=True,
            backtrace=True,
            diagnose=True,
        )

    logger.info(
        "Logging initialised",
        env=settings.app_env,
        level=settings.log_level,
        version=settings.app_version,
    )

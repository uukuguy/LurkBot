"""Logging configuration using loguru."""

import sys

from loguru import logger


def setup_logging(level: str = "INFO", json_format: bool = False) -> None:
    """Configure application logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Whether to output logs in JSON format
    """
    logger.remove()

    if json_format:
        logger.add(
            sys.stderr,
            level=level,
            format="{message}",
            serialize=True,
        )
    else:
        logger.add(
            sys.stderr,
            level=level,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                "<level>{message}</level>"
            ),
            colorize=True,
        )

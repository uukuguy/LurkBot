"""Logging configuration.

This module provides structured logging using loguru,
following MoltBot's logging patterns with subsystem support.
"""

import sys
from typing import Any

from loguru import logger


def setup_logging(level: str = "INFO", subsystem: str | None = None) -> None:
    """Configure logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR).
        subsystem: Optional subsystem name for filtering.
    """
    # Remove default handler
    logger.remove()

    # Add console handler with custom format
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
    )

    if subsystem:
        log_format += f"<cyan>{subsystem}</cyan> | "

    log_format += "<level>{message}</level>"

    logger.add(
        sys.stderr,
        format=log_format,
        level=level.upper(),
        colorize=True,
    )


def get_logger(subsystem: str | None = None) -> Any:
    """Get a logger instance for a subsystem.

    Args:
        subsystem: Optional subsystem name to bind to the logger.

    Returns:
        A loguru logger instance.
    """
    if subsystem:
        return logger.bind(subsystem=subsystem)
    return logger


# Pre-configured loggers for common subsystems
agent_logger = get_logger("agent")
gateway_logger = get_logger("gateway")
channel_logger = get_logger("channel")
tool_logger = get_logger("tool")
memory_logger = get_logger("memory")
cron_logger = get_logger("cron")

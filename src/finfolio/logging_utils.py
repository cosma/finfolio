"""Structured JSON logging utilities."""

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any


def configure_logging(level: str = "INFO") -> logging.Logger:
    """Configure structured JSON logging.

    Logs to stderr with JSON format: {timestamp, level, message, event_data}.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("finfolio")
    logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create JSON formatter
    class JSONFormatter(logging.Formatter):
        """Format log records as JSON."""

        def format(self, record: logging.LogRecord) -> str:
            """Format log record as JSON."""
            log_entry = {
                "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "level": record.levelname,
                "message": record.getMessage(),
                "logger": record.name,
            }

            # Add extra fields from record.__dict__
            if hasattr(record, "__dict__"):
                for key, value in record.__dict__.items():
                    if key not in (
                        "name",
                        "msg",
                        "args",
                        "created",
                        "filename",
                        "funcName",
                        "levelname",
                        "levelno",
                        "lineno",
                        "module",
                        "msecs",
                        "message",
                        "pathname",
                        "process",
                        "processName",
                        "relativeCreated",
                        "thread",
                        "threadName",
                        "exc_info",
                        "exc_text",
                        "stack_info",
                        "asctime",
                    ):
                        if not key.startswith("_"):
                            try:
                                json.dumps(value)  # Ensure JSON serializable
                                log_entry[key] = value
                            except (TypeError, ValueError):
                                log_entry[key] = str(value)

            return json.dumps(log_entry, default=str)

    # Setup stderr handler with JSON formatter
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)

    return logger


def log_operation(
    event: str, status: str, logger: logging.Logger | None = None, **kwargs: Any
) -> None:
    """Log a structured operation event.

    Args:
        event: Event name (e.g., "claim_verified", "search_performed")
        status: Status (e.g., "success", "failed", "partial")
        logger: Logger instance (uses root finfolio logger if None)
        **kwargs: Additional event data
    """
    if logger is None:
        logger = logging.getLogger("finfolio")

    logger.info(f"{event}: {status}", extra={"event": event, "status": status, **kwargs})

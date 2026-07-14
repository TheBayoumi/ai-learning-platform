"""Structured logging setup for local process diagnostics."""

import json
import logging
import logging.config
from typing import override


class JsonFormatter(logging.Formatter):
    """Emit a minimal, machine-readable log record without request content."""

    @override
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        return json.dumps(payload, sort_keys=True)


def configure_logging(log_level: str) -> None:
    """Configure process logging without selecting a telemetry vendor."""
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {"json": {"()": JsonFormatter}},
            "handlers": {
                "stderr": {
                    "class": "logging.StreamHandler",
                    "formatter": "json",
                    "stream": "ext://sys.stderr",
                }
            },
            "root": {"handlers": ["stderr"], "level": log_level},
        }
    )

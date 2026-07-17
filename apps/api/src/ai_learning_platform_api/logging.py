"""Confidential structured logging for bounded process diagnostics."""

import json
import logging
import logging.config
from typing import override

from ai_learning_platform_api.diagnostics import ApiHealthRequestCompleted


class JsonFormatter(logging.Formatter):
    """Emit only fixed fields and never interpolate arbitrary log content."""

    @override
    def format(self, record: logging.LogRecord) -> str:
        diagnostic_event = getattr(record, "diagnostic_event", None)
        if type(diagnostic_event) is ApiHealthRequestCompleted:
            payload = diagnostic_event.to_payload()
        else:
            payload = {
                "schema_version": 1,
                "event": "process.log",
                "service": "api",
                "outcome": "error" if record.levelno >= logging.ERROR else "status",
                "reason": "unstructured_suppressed",
                "severity": self._severity(record.levelno),
            }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _severity(level: int) -> str:
        if level >= logging.CRITICAL:
            return "critical"
        if level >= logging.ERROR:
            return "error"
        if level >= logging.WARNING:
            return "warning"
        if level >= logging.INFO:
            return "info"
        return "debug"


def configure_logging(log_level: str) -> None:
    """Configure bounded process logging without selecting a telemetry vendor."""
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
            "loggers": {
                "uvicorn.error": {
                    "handlers": ["stderr"],
                    "level": log_level,
                    "propagate": False,
                },
                "uvicorn.access": {
                    "handlers": [],
                    "level": "CRITICAL",
                    "propagate": False,
                },
            },
            "root": {"handlers": ["stderr"], "level": log_level},
        }
    )
    logging.getLogger("uvicorn.access").disabled = True

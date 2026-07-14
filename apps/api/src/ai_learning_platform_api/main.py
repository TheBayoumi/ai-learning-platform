"""ASGI entrypoint with a fail-closed confidential bootstrap boundary."""

import logging

from ai_learning_platform_api.app import create_app

try:
    app = create_app()
except Exception:
    logging.getLogger("ai_learning_platform_api.bootstrap").error("bootstrap failed")
    raise SystemExit(1) from None

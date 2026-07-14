"""ASGI entrypoint for local development and deployment-neutral smoke tests."""

from ai_learning_platform_api.app import create_app

app = create_app()

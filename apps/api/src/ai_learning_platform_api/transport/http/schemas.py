"""Typed HTTP response schemas for role-neutral transport endpoints."""

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """A deliberately narrow process-health response."""

    status: Literal["ok"]
    detail: str

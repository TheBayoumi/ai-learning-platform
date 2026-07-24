"""Async SQLAlchemy runtime with explicit serverless-safe lifecycle."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool


@dataclass(frozen=True, slots=True)
class DatabaseRuntime:
    """Own the async engine and its bounded shutdown lifecycle."""

    engine: AsyncEngine

    @classmethod
    def create(cls, database_url: str) -> DatabaseRuntime:
        """Create a lazy engine; no connection is opened during application import."""
        return cls(
            engine=create_async_engine(
                database_url,
                poolclass=NullPool,
                pool_pre_ping=True,
                connect_args={"connect_timeout": 5},
            )
        )

    async def shutdown(self) -> None:
        """Dispose all engine resources owned by this application instance."""
        await self.engine.dispose()

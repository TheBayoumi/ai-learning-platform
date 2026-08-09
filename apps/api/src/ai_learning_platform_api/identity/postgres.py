"""PostgreSQL implementation of provider-neutral identity ownership."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import delete, insert, select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from ai_learning_platform_api.identity.contracts import (
    AccountRole,
    AnonymousClaimError,
    IdentityRepository,
    IdentityUnavailableError,
    OidcPrincipal,
    PlatformIdentity,
)
from ai_learning_platform_api.identity.models import account_identities, account_roles, identity_claims
from ai_learning_platform_api.persistence.models import (
    accounts,
    learner_events,
    learner_states,
    task_exposures,
)

_ALLOWED_ROLES = frozenset({"learner", "reviewer", "admin"})


class PostgresIdentityRepository(IdentityRepository):
    """Map managed OIDC subjects to stable platform account IDs and explicit roles."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def resolve(self, principal: OidcPrincipal) -> PlatformIdentity:
        """Resolve or atomically create a learner account for one issuer/subject pair."""
        now = datetime.now(UTC)
        try:
            async with self._engine.begin() as connection:
                existing = await _identity_row(
                    connection,
                    issuer=principal.issuer,
                    subject=principal.subject,
                )
                if existing is None:
                    account_id = str(uuid4())
                    await connection.execute(
                        insert(accounts).values(
                            id=account_id,
                            created_at=now,
                            updated_at=now,
                        )
                    )
                    await connection.execute(
                        insert(account_identities).values(
                            id=uuid4(),
                            account_id=account_id,
                            issuer=principal.issuer,
                            subject=principal.subject,
                            email=principal.email,
                            created_at=now,
                            last_seen_at=now,
                        )
                    )
                    await connection.execute(
                        insert(account_roles).values(
                            account_id=account_id,
                            role="learner",
                            created_at=now,
                        )
                    )
                else:
                    account_id = str(existing["account_id"])
                    await connection.execute(
                        update(account_identities)
                        .where(
                            account_identities.c.issuer == principal.issuer,
                            account_identities.c.subject == principal.subject,
                        )
                        .values(email=principal.email, last_seen_at=now)
                    )
                    await connection.execute(
                        update(accounts).where(accounts.c.id == account_id).values(updated_at=now)
                    )
                roles = await _roles(connection, account_id=account_id)
                return _platform_identity(principal, account_id=account_id, roles=roles)
        except IntegrityError:
            # Concurrent first-login resolution may race on the unique issuer/subject pair.
            # Re-read the winning identity rather than creating a second platform account.
            return await self._resolve_after_race(principal)
        except SQLAlchemyError as error:
            raise IdentityUnavailableError from error

    async def _resolve_after_race(self, principal: OidcPrincipal) -> PlatformIdentity:
        try:
            async with self._engine.connect() as connection:
                existing = await _identity_row(
                    connection,
                    issuer=principal.issuer,
                    subject=principal.subject,
                )
                if existing is None:
                    raise IdentityUnavailableError
                account_id = str(existing["account_id"])
                roles = await _roles(connection, account_id=account_id)
        except SQLAlchemyError as error:
            raise IdentityUnavailableError from error
        return _platform_identity(principal, account_id=account_id, roles=roles)

    async def claim_anonymous_account(
        self,
        *,
        identity: PlatformIdentity,
        anonymous_account_id: str,
    ) -> bool:
        """Move one unbound anonymous account into the authenticated account exactly once."""
        if anonymous_account_id == identity.account_id:
            return False
        source_hash = hashlib.sha256(anonymous_account_id.encode("utf-8")).hexdigest()
        now = datetime.now(UTC)
        try:
            async with self._engine.begin() as connection:
                prior_claim = (
                    await connection.execute(
                        select(identity_claims.c.id).where(
                            identity_claims.c.source_account_sha256 == source_hash
                        )
                    )
                ).scalar_one_or_none()
                if prior_claim is not None:
                    return False
                source_exists = (
                    await connection.execute(
                        select(accounts.c.id).where(accounts.c.id == anonymous_account_id)
                    )
                ).scalar_one_or_none()
                target_exists = (
                    await connection.execute(
                        select(accounts.c.id).where(accounts.c.id == identity.account_id)
                    )
                ).scalar_one_or_none()
                if source_exists is None or target_exists is None:
                    raise AnonymousClaimError
                source_identity = (
                    await connection.execute(
                        select(account_identities.c.id).where(
                            account_identities.c.account_id == anonymous_account_id
                        )
                    )
                ).scalar_one_or_none()
                if source_identity is not None:
                    raise AnonymousClaimError

                for table in (learner_states, learner_events, task_exposures):
                    await connection.execute(
                        update(table)
                        .where(table.c.account_id == anonymous_account_id)
                        .values(account_id=identity.account_id)
                    )
                await connection.execute(
                    postgresql_insert(identity_claims)
                    .values(
                        id=uuid4(),
                        source_account_sha256=source_hash,
                        target_account_id=identity.account_id,
                        claimed_at=now,
                    )
                    .on_conflict_do_nothing(index_elements=[identity_claims.c.source_account_sha256])
                )
                await connection.execute(delete(accounts).where(accounts.c.id == anonymous_account_id))
                return True
        except AnonymousClaimError:
            raise
        except IntegrityError as error:
            raise AnonymousClaimError from error
        except SQLAlchemyError as error:
            raise IdentityUnavailableError from error


async def _identity_row(
    connection: AsyncConnection,
    *,
    issuer: str,
    subject: str,
):
    result = await connection.execute(
        select(account_identities.c.account_id).where(
            account_identities.c.issuer == issuer,
            account_identities.c.subject == subject,
        )
    )
    return result.mappings().one_or_none()


async def _roles(connection: AsyncConnection, *, account_id: str) -> tuple[AccountRole, ...]:
    values = (
        await connection.execute(
            select(account_roles.c.role)
            .where(account_roles.c.account_id == account_id)
            .order_by(account_roles.c.role)
        )
    ).scalars().all()
    if not values or any(value not in _ALLOWED_ROLES for value in values):
        raise IdentityUnavailableError
    return tuple(values)  # type: ignore[return-value]


def _platform_identity(
    principal: OidcPrincipal,
    *,
    account_id: str,
    roles: tuple[AccountRole, ...],
) -> PlatformIdentity:
    return PlatformIdentity(
        account_id=account_id,
        issuer=principal.issuer,
        subject=principal.subject,
        roles=roles,
    )

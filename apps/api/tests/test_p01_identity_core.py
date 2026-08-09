from __future__ import annotations

import pytest

from ai_learning_platform_api.identity.claim import AnonymousAccountClaimProof
from ai_learning_platform_api.identity.contracts import OidcPrincipal, PlatformIdentity

_SECRET = "p01-anonymous-claim-secret-long-enough-for-hmac"


def test_principal_and_platform_identity_are_bounded_and_role_safe() -> None:
    principal = OidcPrincipal(
        issuer="https://tenant.example/",
        subject="auth0|learner-1",
        email="learner@example.com",
    )
    identity = PlatformIdentity(
        account_id="11111111-1111-4111-8111-111111111111",
        issuer=principal.issuer,
        subject=principal.subject,
        roles=("learner",),
    )

    assert identity.roles == ("learner",)
    with pytest.raises(ValueError, match="learner role"):
        PlatformIdentity(
            account_id=identity.account_id,
            issuer=principal.issuer,
            subject=principal.subject,
            roles=("reviewer",),
        )
    with pytest.raises(ValueError, match="unique"):
        PlatformIdentity(
            account_id=identity.account_id,
            issuer=principal.issuer,
            subject=principal.subject,
            roles=("learner", "learner"),
        )


def test_anonymous_claim_proof_is_exact_and_tamper_evident() -> None:
    proof = AnonymousAccountClaimProof(_SECRET)
    account = "22222222-2222-4222-8222-222222222222"
    signature = proof.sign(account)

    assert len(signature) == 64
    assert proof.verify(account, signature)
    assert not proof.verify("33333333-3333-4333-8333-333333333333", signature)
    assert not proof.verify(account, "0" * 63)


def test_anonymous_claim_secret_is_not_allowed_to_be_weak() -> None:
    with pytest.raises(ValueError, match="at least 32"):
        AnonymousAccountClaimProof("short")

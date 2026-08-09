"""Bounded HMAC proof for one-time anonymous-account migration through the trusted BFF."""

from __future__ import annotations

import hashlib
import hmac


class AnonymousAccountClaimProof:
    """Verify that the server-side BFF authorized migration of one anonymous cookie account."""

    def __init__(self, secret: str) -> None:
        encoded = secret.encode("utf-8")
        if len(encoded) < 32:
            raise ValueError("anonymous claim secret must contain at least 32 UTF-8 bytes")
        self._secret = encoded

    def sign(self, account_id: str) -> str:
        return hmac.new(self._secret, account_id.encode("ascii"), hashlib.sha256).hexdigest()

    def verify(self, account_id: str, proof: str) -> bool:
        if len(proof) != 64:
            return False
        try:
            expected = self.sign(account_id)
        except (UnicodeEncodeError, ValueError):
            return False
        return hmac.compare_digest(expected, proof.lower())

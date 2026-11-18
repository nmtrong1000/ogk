"""Only policies whose Ed25519 signature verifies are kept; the DB is not trusted, so every load re-verifies
the stored canonical bytes. canonical_json must stay byte-identical to ogk-server app/core/signing.py
(checked by docs/test_vectors.json). A batch from the server is all-or-nothing: one bad signature or a
version lower than the one held rejects the whole batch and the current set stays. Without a usable public
key every policy is rejected (fail closed).
Methods are synchronous; async callers run them in a worker thread.
"""

import base64
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from service.core.local_db import LocalDb, PolicyRow

log = logging.getLogger("ogk.policy")

FORMAT = 1


class PolicyRejected(Exception):
    pass


@dataclass(frozen=True)
class SignedPolicy:
    child_id: int
    version: int
    document: dict[str, Any]
    canonical: str
    signature: str


def _check_value(value: Any) -> None:
    if isinstance(value, float):
        raise ValueError("canonical JSON does not allow floats")
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("canonical JSON keys must be strings")
            _check_value(item)
    elif isinstance(value, list):
        for item in value:
            _check_value(item)


def canonical_json(obj: Any) -> bytes:
    _check_value(obj)
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def _b64url_decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def load_public_key(path: Path) -> Ed25519PublicKey:
    try:
        key = serialization.load_pem_public_key(path.read_bytes())
    except (OSError, ValueError) as exc:
        raise PolicyRejected(f"policy public key unusable: {path}: {exc}") from None
    if not isinstance(key, Ed25519PublicKey):
        raise PolicyRejected(f"policy public key is not Ed25519: {path}")
    return key


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def verify_bytes(public_key: Ed25519PublicKey, canonical: bytes, signature: str) -> SignedPolicy:
    try:
        public_key.verify(_b64url_decode(signature), canonical)
    except (InvalidSignature, ValueError, TypeError):
        raise PolicyRejected("bad signature") from None
    document = json.loads(canonical)
    if not isinstance(document, dict) or document.get("format") != FORMAT:
        raise PolicyRejected("unsupported policy format")
    child_id, version = document.get("child_id"), document.get("policy_version")
    if not _is_int(child_id) or not _is_int(version) or version < 1:
        raise PolicyRejected("policy is missing child_id or policy_version")
    return SignedPolicy(child_id, version, document, canonical.decode(), signature)


def verify_document(public_key: Ed25519PublicKey, document: Any, signature: Any) -> SignedPolicy:
    if not isinstance(document, dict) or not isinstance(signature, str):
        raise PolicyRejected("malformed policy envelope")
    try:
        canonical = canonical_json(document)
    except ValueError as exc:
        raise PolicyRejected(str(exc)) from None
    return verify_bytes(public_key, canonical, signature)


class PolicyStore:
    def __init__(self, db: LocalDb, public_key_path: Path | None) -> None:
        self._db = db
        self._key_path = public_key_path
        self._key: Ed25519PublicKey | None = None
        self._current: dict[int, SignedPolicy] = {}
        self._loaded = False

    def _public_key(self) -> Ed25519PublicKey:
        if self._key is None:
            if self._key_path is None:
                raise PolicyRejected("no policy public key configured")
            try:
                self._key = load_public_key(self._key_path)
            except PolicyRejected as exc:
                log.error("%s; every policy is rejected", exc)
                raise
        return self._key

    def current(self) -> dict[int, SignedPolicy]:
        return dict(self._current)

    def versions(self) -> dict[int, int]:
        return {child_id: policy.version for child_id, policy in self._current.items()}

    def load(self) -> dict[int, SignedPolicy]:
        valid: dict[int, SignedPolicy] = {}
        rows = self._db.load_policies()
        for row in rows:
            try:
                policy = verify_bytes(self._public_key(), row.payload.encode(), row.signature)
                if (policy.child_id, policy.version) != (row.child_id, row.version):
                    raise PolicyRejected("row does not match signed document")
            except PolicyRejected as exc:
                log.warning("policy for child %s rejected: %s", row.child_id, exc)
                continue
            valid[policy.child_id] = policy
        self._current = valid
        self._loaded = True
        return dict(valid)

    def save(self, body: Any, received_at: datetime | None = None) -> dict[int, SignedPolicy]:
        if not self._loaded:
            self.load()
        envelopes = body.get("policies") if isinstance(body, dict) else None
        if not isinstance(envelopes, list):
            raise PolicyRejected("malformed policy response")
        incoming: dict[int, SignedPolicy] = {}
        for envelope in envelopes:
            if not isinstance(envelope, dict):
                raise PolicyRejected("malformed policy envelope")
            policy = verify_document(self._public_key(), envelope.get("policy"), envelope.get("signature"))
            held = self._current.get(policy.child_id)
            if held is not None and policy.version < held.version:
                raise PolicyRejected(
                    f"policy for child {policy.child_id} has version {policy.version}, older than {held.version}"
                )
            if policy.child_id in incoming:
                raise PolicyRejected(f"duplicate policy for child {policy.child_id}")
            incoming[policy.child_id] = policy
        rows = [PolicyRow(p.child_id, p.version, p.canonical, p.signature) for p in incoming.values()]
        self._db.replace_policies(rows, received_at or datetime.now(UTC))
        self._current = incoming
        return dict(incoming)

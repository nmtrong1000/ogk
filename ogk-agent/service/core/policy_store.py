"""Only policies whose Ed25519 signature verifies are kept; the DB is not trusted, so every load re-verifies
the stored canonical bytes. canonical_json must stay byte-identical to ogk-server app/core/signing.py
(checked by docs/test_vectors.json). A batch from the server is all-or-nothing: one bad signature or a
version lower than the one held rejects the whole batch and the current set stays. Without a usable public
key every policy is rejected (fail closed).
The default policy (data/default_policy.json) is unsigned because it ships inside the installer, not from the
server. It applies to every child while expired is set, and to any child with no signed policy at all, so a
child is never left without rules.
A correctly signed policy whose rules, accounts or set_by are malformed is rejected like a bad signature, so
enforcement never has to guess. The one exception is a missing app_rules, read as []: policies signed before
app_rules existed carry none, and rejecting them would also drop their quota and schedule.
child_for_sid uses the signed accounts even while the policies are expired, because the default policy still
needs to know which child is logged on.
Methods are synchronous; async callers run them in a worker thread.
"""

import base64
import json
import logging
import re
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
DEFAULT_VERSION = 0
MAX_QUOTA_MINUTES = 1440
MAX_APP_RULES = 200
MAX_APP_NAME = 255
APP_ACTIONS = ("allow", "block")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
DAYS_PER_WEEK = 7
SLOTS_PER_DAY = 48
MODE_CACHED = "cached"
MODE_DEFAULT = "default"


class PolicyRejected(Exception):
    pass


@dataclass(frozen=True)
class SignedPolicy:
    child_id: int
    version: int
    document: dict[str, Any]
    canonical: str
    signature: str


@dataclass(frozen=True)
class DefaultPolicy:
    rules: dict[str, Any]


@dataclass(frozen=True)
class EffectivePolicy:
    child_id: int
    version: int
    rules: dict[str, Any]
    source: str
    set_by: str = ""


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


def _quota_ok(value: Any) -> bool:
    return _is_int(value) and 0 <= value <= MAX_QUOTA_MINUTES


def _app_rule_ok(rule: Any) -> bool:
    if not isinstance(rule, dict):
        return False
    name, sha256, action = rule.get("name"), rule.get("sha256"), rule.get("action")
    return (
        isinstance(name, str)
        and 1 <= len(name) <= MAX_APP_NAME
        and name == name.lower()
        and "/" not in name
        and "\\" not in name
        and (sha256 is None or (isinstance(sha256, str) and SHA256_RE.match(sha256) is not None))
        and action in APP_ACTIONS
    )


def _app_rules_ok(value: Any) -> bool:
    return isinstance(value, list) and len(value) <= MAX_APP_RULES and all(_app_rule_ok(r) for r in value)


def rules_ok(rules: Any) -> bool:
    return (
        isinstance(rules, dict)
        and _quota_ok(rules.get("weekday_quota_minutes"))
        and _quota_ok(rules.get("weekend_quota_minutes"))
        and _schedule_ok(rules.get("weekly_schedule"))
        and _app_rules_ok(rules.get("app_rules", []))
    )


def _with_defaults(rules: dict) -> dict:
    return {"app_rules": [], **rules}


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
    accounts = document.get("accounts")
    if not isinstance(accounts, list) or not all(isinstance(sid, str) and sid for sid in accounts):
        raise PolicyRejected("policy accounts must be a list of SIDs")
    if not isinstance(document.get("set_by"), str):
        raise PolicyRejected("policy set_by must be a string")
    if not rules_ok(document.get("rules")):
        raise PolicyRejected("policy rules are malformed")
    return SignedPolicy(child_id, version, document, canonical.decode(), signature)


def verify_document(public_key: Ed25519PublicKey, document: Any, signature: Any) -> SignedPolicy:
    if not isinstance(document, dict) or not isinstance(signature, str):
        raise PolicyRejected("malformed policy envelope")
    try:
        canonical = canonical_json(document)
    except ValueError as exc:
        raise PolicyRejected(str(exc)) from None
    return verify_bytes(public_key, canonical, signature)


def _schedule_ok(schedule: Any) -> bool:
    return (
        isinstance(schedule, list)
        and len(schedule) == DAYS_PER_WEEK
        and all(isinstance(day, str) and len(day) == SLOTS_PER_DAY and set(day) <= {"0", "1"} for day in schedule)
    )


def load_default_policy(path: Path) -> DefaultPolicy:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PolicyRejected(f"default policy unusable: {path}: {exc}") from None
    if not isinstance(document, dict) or document.get("format") != FORMAT:
        raise PolicyRejected(f"default policy has an unsupported format: {path}")
    if document.get("policy_version") != DEFAULT_VERSION:
        raise PolicyRejected(f"default policy must have policy_version {DEFAULT_VERSION}: {path}")
    rules = document.get("rules")
    if not rules_ok(rules):
        raise PolicyRejected(
            f"default policy needs weekday/weekend quotas of 0-{MAX_QUOTA_MINUTES} minutes and a weekly_schedule "
            f"of 7 strings of 48 '0'/'1' slots: {path}"
        )
    return DefaultPolicy(rules)


class PolicyStore:
    def __init__(self, db: LocalDb, public_key_path: Path | None, default: DefaultPolicy | None = None) -> None:
        self._db = db
        self._key_path = public_key_path
        self._key: Ed25519PublicKey | None = None
        self._current: dict[int, SignedPolicy] = {}
        self._loaded = False
        self._default = default
        self._expired = False

    @property
    def mode(self) -> str:
        return MODE_DEFAULT if self._expired and self._default is not None else MODE_CACHED

    def set_expired(self, expired: bool) -> bool:
        changed = expired != self._expired
        self._expired = expired
        return changed

    def _default_for(self, child_id: int) -> EffectivePolicy:
        return EffectivePolicy(child_id, DEFAULT_VERSION, _with_defaults(self._default.rules), MODE_DEFAULT)

    def rules_for(self, child_id: int) -> EffectivePolicy | None:
        signed = self._current.get(child_id)
        if self.mode == MODE_CACHED and signed is not None:
            return EffectivePolicy(
                child_id,
                signed.version,
                _with_defaults(signed.document["rules"]),
                MODE_CACHED,
                signed.document["set_by"],
            )
        if self._default is None:
            return None
        return self._default_for(child_id)

    def effective(self) -> dict[int, EffectivePolicy]:
        return {child_id: self.rules_for(child_id) for child_id in self._current}

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

    def child_for_sid(self, sid: str) -> int | None:
        if not sid:
            return None
        for child_id, policy in sorted(self._current.items()):
            if sid in policy.document["accounts"]:
                return child_id
        return None

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

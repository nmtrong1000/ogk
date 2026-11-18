"""Ed25519 signing of policies over canonical JSON; the agent repeats the same canonicalization byte for byte.

Floats are rejected because their text form differs between JSON libraries, which would break signatures.
The private key file must not be readable by group or others; a looser mode is refused rather than trusted.
"""

import base64
import hashlib
import json
import os
import stat
from functools import lru_cache
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from app.core.config import ConfigError, get_settings

KEY_HINT = "(python -m app.cli gen-policy-key)"


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


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def b64url_decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def raw_public_key(public_key: Ed25519PublicKey) -> bytes:
    return public_key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def key_id(public_key: Ed25519PublicKey) -> str:
    return hashlib.sha256(raw_public_key(public_key)).hexdigest()[:16]


def sign_with(private_key: Ed25519PrivateKey, doc: dict[str, Any]) -> str:
    return b64url(private_key.sign(canonical_json(doc)))


def verify(public_key: Ed25519PublicKey, doc: dict[str, Any], signature: str) -> bool:
    try:
        public_key.verify(b64url_decode(signature), canonical_json(doc))
    except (InvalidSignature, ValueError):
        return False
    return True


def load_private_key(path: Path) -> Ed25519PrivateKey:
    try:
        mode = path.stat().st_mode
        data = path.read_bytes()
    except OSError:
        raise ConfigError(f"Policy signing key not found: {path} {KEY_HINT}") from None
    if os.name == "posix" and mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise ConfigError(f"Policy signing key {path} must not be readable by group or others (chmod 600)")
    try:
        key = serialization.load_pem_private_key(data, password=None)
    except ValueError:
        key = None
    if not isinstance(key, Ed25519PrivateKey):
        raise ConfigError(f"Policy signing key {path} is not an Ed25519 PEM private key {KEY_HINT}")
    return key


@lru_cache
def get_signing_key() -> Ed25519PrivateKey:
    path = get_settings().policy_signing_key
    if path is None:
        raise ConfigError(f"OGK_POLICY_SIGNING_KEY is not set {KEY_HINT}")
    return load_private_key(path)


def sign(doc: dict[str, Any]) -> str:
    return sign_with(get_signing_key(), doc)


def signing_key_id() -> str:
    return key_id(get_signing_key().public_key())


def generate_key_pair(out_dir: Path) -> tuple[Path, Path]:
    private_path = out_dir / "policy_signing.pem"
    public_path = out_dir / "policy_public.pem"
    if private_path.exists() or public_path.exists():
        raise FileExistsError(f"Refusing to overwrite existing key in {out_dir}")
    key = Ed25519PrivateKey.generate()
    out_dir.mkdir(parents=True, exist_ok=True)
    private_pem = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    )
    fd = os.open(private_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(private_pem)
    public_path.write_bytes(
        key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    )
    return private_path, public_path

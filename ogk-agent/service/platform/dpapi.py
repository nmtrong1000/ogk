"""DPAPI uses machine scope (CRYPTPROTECT_LOCAL_MACHINE) because the enroll command runs as an
administrator while the service runs as SYSTEM; both must decrypt the same blobs. Machine scope means
any local process can decrypt, so the real protection is the ACL on the data directory (core/local_db.py).
The Mac fake is AES-GCM with a key file in the fake data dir. It only exists so the logic can be tested;
it is not a security boundary. win32crypt is imported lazily so Mac never loads pywin32.
"""

import os
import sys
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ENTROPY = b"OGK-agent-local-db"
FAKE_PREFIX = b"FAKEDPAPI1"
FAKE_KEY_FILE = "fake-dpapi.key"


class DpapiError(Exception):
    pass


def _fake_key() -> bytes:
    from service.platform import fake

    path: Path = fake.data_dir() / FAKE_KEY_FILE
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_bytes(AESGCM.generate_key(bit_length=256))
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    return path.read_bytes()


def protect(data: bytes) -> bytes:
    if sys.platform == "win32":
        import win32crypt

        return win32crypt.CryptProtectData(data, None, ENTROPY, None, None, win32crypt.CRYPTPROTECT_LOCAL_MACHINE)
    nonce = os.urandom(12)
    return FAKE_PREFIX + nonce + AESGCM(_fake_key()).encrypt(nonce, data, ENTROPY)


def unprotect(blob: bytes) -> bytes:
    if sys.platform == "win32":
        import pywintypes
        import win32crypt

        try:
            return win32crypt.CryptUnprotectData(blob, ENTROPY, None, None, 0)[1]
        except pywintypes.error as exc:
            raise DpapiError(f"DPAPI decrypt failed: {exc}") from None
    if not blob.startswith(FAKE_PREFIX):
        raise DpapiError("blob was not produced by fake DPAPI")
    body = blob[len(FAKE_PREFIX) :]
    try:
        return AESGCM(_fake_key()).decrypt(body[:12], body[12:], ENTROPY)
    except InvalidTag:
        raise DpapiError("fake DPAPI decrypt failed") from None

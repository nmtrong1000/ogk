"""Mã hóa trường nhạy cảm bằng AES-256-GCM. Khóa đọc từ biến môi trường OGK_DATA_KEY."""

import base64
import binascii
import os
from functools import lru_cache

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import LargeBinary
from sqlalchemy.types import TypeDecorator

from app.core.config import ConfigError, get_settings

KEY_SIZE = 32
NONCE_SIZE = 12
VERSION = b"\x01"


def generate_key() -> str:
    return base64.urlsafe_b64encode(os.urandom(KEY_SIZE)).decode()


def decode_key(value: str) -> bytes:
    try:
        key = base64.urlsafe_b64decode(value.strip().encode())
    except (binascii.Error, ValueError):
        key = b""
    if len(key) != KEY_SIZE:
        raise ConfigError("OGK_DATA_KEY phải là base64url của 32 byte (python -m app.cli gen-data-key)")
    return key


@lru_cache
def get_cipher() -> AESGCM:
    return AESGCM(decode_key(get_settings().data_key.get_secret_value()))


def encrypt(plaintext: bytes, aad: bytes, cipher: AESGCM | None = None) -> bytes:
    """Trả về version (1 byte) || nonce (12 byte) || ciphertext kèm tag."""
    nonce = os.urandom(NONCE_SIZE)
    return VERSION + nonce + (cipher or get_cipher()).encrypt(nonce, plaintext, aad)


def decrypt(blob: bytes, aad: bytes, cipher: AESGCM | None = None) -> bytes:
    """Sai khóa, sai AAD hoặc dữ liệu bị sửa thì ném cryptography.exceptions.InvalidTag."""
    if len(blob) < 1 + NONCE_SIZE or blob[:1] != VERSION:
        raise ValueError("Bản mã không đúng định dạng")
    nonce, ciphertext = blob[1 : 1 + NONCE_SIZE], blob[1 + NONCE_SIZE :]
    return (cipher or get_cipher()).decrypt(nonce, ciphertext, aad)


class EncryptedString(TypeDecorator):
    """Cột chuỗi được mã hóa khi ghi, giải mã khi đọc. AAD gắn bản mã với đúng bảng và cột."""

    impl = LargeBinary
    cache_ok = True

    def __init__(self, aad: str) -> None:
        super().__init__()
        self.aad = aad.encode()

    def process_bind_param(self, value: str | None, _dialect) -> bytes | None:
        return None if value is None else encrypt(value.encode(), self.aad)

    def process_result_value(self, value: bytes | None, _dialect) -> str | None:
        return None if value is None else decrypt(value, self.aad).decode()


class EncryptedInt(EncryptedString):
    def process_bind_param(self, value: int | None, dialect) -> bytes | None:
        return super().process_bind_param(None if value is None else str(int(value)), dialect)

    def process_result_value(self, value: bytes | None, dialect) -> int | None:
        text = super().process_result_value(value, dialect)
        return None if text is None else int(text)

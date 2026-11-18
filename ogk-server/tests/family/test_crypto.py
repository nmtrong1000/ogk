import base64
import os

import pytest
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core import crypto
from app.core.config import ConfigError


def test_roundtrip(settings_env):
    blob = crypto.encrypt("Nguyễn Văn An".encode(), b"children.name")
    assert crypto.decrypt(blob, b"children.name").decode() == "Nguyễn Văn An"
    assert "Nguyễn".encode() not in blob


def test_same_plaintext_gives_different_ciphertext(settings_env):
    a = crypto.encrypt(b"An", b"children.name")
    b = crypto.encrypt(b"An", b"children.name")
    assert a != b
    assert len(a) == 1 + crypto.NONCE_SIZE + len(b"An") + 16


def test_wrong_key_fails(settings_env):
    blob = crypto.encrypt(b"An", b"children.name")
    with pytest.raises(InvalidTag):
        crypto.decrypt(blob, b"children.name", cipher=AESGCM(os.urandom(32)))


def test_tampered_ciphertext_fails(settings_env):
    blob = bytearray(crypto.encrypt(b"An", b"children.name"))
    blob[-1] ^= 0x01
    with pytest.raises(InvalidTag):
        crypto.decrypt(bytes(blob), b"children.name")


def test_wrong_aad_fails(settings_env):
    blob = crypto.encrypt(b"2017", b"children.birth_year")
    with pytest.raises(InvalidTag):
        crypto.decrypt(blob, b"children.name")


def test_bad_format_rejected(settings_env):
    with pytest.raises(ValueError):
        crypto.decrypt(b"\x02" + os.urandom(30), b"children.name")


@pytest.mark.parametrize("value", ["", "khong-phai-base64!!", base64.urlsafe_b64encode(os.urandom(16)).decode()])
def test_bad_key_raises_config_error(value):
    with pytest.raises(ConfigError):
        crypto.decode_key(value)


def test_key_from_env(settings_env, monkeypatch):
    key = crypto.generate_key()
    monkeypatch.setenv("OGK_DATA_KEY", key)
    from app.core.config import get_settings

    get_settings.cache_clear()
    crypto.get_cipher.cache_clear()
    blob = crypto.encrypt(b"An", b"x")
    assert AESGCM(base64.urlsafe_b64decode(key)).decrypt(blob[1:13], blob[13:], b"x") == b"An"

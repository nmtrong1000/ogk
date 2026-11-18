import os

import pytest
from cryptography.hazmat.primitives import serialization

from app.cli import main as cli_main
from app.core import signing
from app.core.config import ConfigError


def test_sign_and_verify_round_trip(settings_env):
    doc = {"b": 1, "a": "Bé An"}
    signature = signing.sign(doc)
    public_key = signing.get_signing_key().public_key()
    assert signing.verify(public_key, doc, signature)
    assert not signing.verify(public_key, {"b": 2, "a": "Bé An"}, signature)


def test_canonical_json_sorts_keys_and_keeps_unicode():
    assert signing.canonical_json({"b": [1, {"d": None, "c": True}], "a": "ê"}) == (
        '{"a":"ê","b":[1,{"c":true,"d":null}]}'.encode()
    )


@pytest.mark.parametrize("value", [1.5, {"a": [0.0]}, {1: "x"}])
def test_canonical_json_rejects_floats_and_non_string_keys(value):
    with pytest.raises(ValueError):
        signing.canonical_json(value)


def test_missing_key_file(settings_env, monkeypatch, tmp_path):
    monkeypatch.setenv("OGK_POLICY_SIGNING_KEY", str(tmp_path / "missing.pem"))
    signing.get_settings.cache_clear()
    with pytest.raises(ConfigError, match="not found"):
        signing.get_signing_key()


def test_unset_key(settings_env, monkeypatch):
    monkeypatch.delenv("OGK_POLICY_SIGNING_KEY")
    signing.get_settings.cache_clear()
    with pytest.raises(ConfigError, match="OGK_POLICY_SIGNING_KEY"):
        signing.get_signing_key()


@pytest.mark.skipif(os.name != "posix", reason="POSIX file modes")
def test_key_readable_by_others_is_refused(settings_env, tmp_path):
    path = tmp_path / "keys" / "policy_signing.pem"
    path.chmod(0o644)
    with pytest.raises(ConfigError, match="chmod 600"):
        signing.get_signing_key()


def test_non_ed25519_key_is_refused(settings_env, tmp_path):
    path = tmp_path / "keys" / "policy_signing.pem"
    path.write_text("not a key")
    with pytest.raises(ConfigError, match="Ed25519"):
        signing.get_signing_key()


def test_cli_generates_key_pair_and_refuses_overwrite(tmp_path, capsys):
    out = tmp_path / "out"
    assert cli_main(["gen-policy-key", "--out", str(out)]) == 0
    private_path = out / "policy_signing.pem"
    assert private_path.stat().st_mode & 0o777 == 0o600
    private_key = signing.load_private_key(private_path)
    public_key = serialization.load_pem_public_key((out / "policy_public.pem").read_bytes())
    assert signing.verify(public_key, {"a": 1}, signing.sign_with(private_key, {"a": 1}))
    assert cli_main(["gen-policy-key", "--out", str(out)]) == 1
    assert "Refusing to overwrite" in capsys.readouterr().err

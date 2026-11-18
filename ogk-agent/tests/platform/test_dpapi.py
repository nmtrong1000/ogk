import pytest

from service.platform import dpapi


def test_round_trip(data_dir):
    blob = dpapi.protect(b"refresh-token")
    assert b"refresh-token" not in blob
    assert dpapi.unprotect(blob) == b"refresh-token"


def test_same_input_gives_different_blobs(data_dir):
    assert dpapi.protect(b"x") != dpapi.protect(b"x")


def test_tampered_blob_is_rejected(data_dir):
    blob = bytearray(dpapi.protect(b"secret"))
    blob[-1] ^= 1
    with pytest.raises(dpapi.DpapiError):
        dpapi.unprotect(bytes(blob))


def test_foreign_blob_is_rejected(data_dir):
    with pytest.raises(dpapi.DpapiError):
        dpapi.unprotect(b"not a dpapi blob")


def test_other_key_cannot_decrypt(data_dir, tmp_path, monkeypatch):
    blob = dpapi.protect(b"secret")
    other = tmp_path / "other"
    monkeypatch.setenv("OGK_DATA_DIR", str(other))
    with pytest.raises(dpapi.DpapiError):
        dpapi.unprotect(blob)


def test_key_file_is_owner_only(data_dir):
    dpapi.protect(b"x")
    assert (data_dir / dpapi.FAKE_KEY_FILE).stat().st_mode & 0o777 == 0o600

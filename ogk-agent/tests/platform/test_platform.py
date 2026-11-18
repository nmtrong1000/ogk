import sys

from service.platform import fake, get_platform


def test_fake_platform_on_mac():
    assert get_platform() is fake
    assert "service.platform.windows" not in sys.modules


def test_fake_data_dir_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("OGK_DATA_DIR", str(tmp_path))
    assert fake.data_dir() == tmp_path.resolve()


def test_fake_admin_from_env(monkeypatch):
    monkeypatch.delenv("OGK_FAKE_ADMIN", raising=False)
    assert fake.is_admin()
    monkeypatch.setenv("OGK_FAKE_ADMIN", "0")
    assert not fake.is_admin()


def test_fake_fingerprint_is_stable_per_data_dir(data_dir, tmp_path, monkeypatch):
    first = fake.machine_fingerprint()
    assert first == fake.machine_fingerprint()
    assert len(first) == 64
    monkeypatch.setenv("OGK_DATA_DIR", str(tmp_path / "other"))
    assert fake.machine_fingerprint() != first


def test_fake_accounts(monkeypatch):
    monkeypatch.delenv("OGK_FAKE_ACCOUNTS", raising=False)
    assert len(fake.list_windows_accounts()) == 2
    monkeypatch.setenv("OGK_FAKE_ACCOUNTS", "an:S-1-5-21-9-1001, chi:S-1-5-21-9-1003")
    assert fake.list_windows_accounts() == [("an", "S-1-5-21-9-1001"), ("chi", "S-1-5-21-9-1003")]


def test_fake_secure_path_modes(tmp_path):
    directory = tmp_path / "d"
    directory.mkdir()
    file = directory / "f"
    file.write_text("x")
    fake.secure_path(directory)
    fake.secure_path(file)
    assert directory.stat().st_mode & 0o777 == 0o700
    assert file.stat().st_mode & 0o777 == 0o600
    fake.secure_path(file, user_readable=True)
    assert file.stat().st_mode & 0o777 == 0o644

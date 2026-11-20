import sys

from tray.platform import fake, get_platform


def test_fake_platform_on_mac():
    assert get_platform() is fake
    assert "tray.platform.windows" not in sys.modules


def test_fake_data_dir_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("OGK_DATA_DIR", str(tmp_path))
    assert fake.data_dir() == tmp_path.resolve()


def test_fake_foreground_app(data_dir):
    assert fake.foreground_app() is None
    (data_dir / fake.FOREGROUND_FILE).write_text("Chrome.exe\n", encoding="utf-8")
    assert fake.foreground_app() == "chrome.exe"
    (data_dir / fake.FOREGROUND_FILE).write_text("  ", encoding="utf-8")
    assert fake.foreground_app() is None

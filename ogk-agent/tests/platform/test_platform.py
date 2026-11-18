import asyncio
import sys

import pytest

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


@pytest.fixture
def session_state():
    yield
    fake.set_session_listener(None)
    fake.dispatch_session_event(fake.SessionEvent("logon", fake.FAKE_SESSION_ID))


def test_fake_session_command_and_reader(tmp_path, capsys):
    path = tmp_path / fake.SESSION_FILE
    for kind in ("lock", "unlock", "logoff", "logon"):
        assert fake.session_command([kind], tmp_path) == 0
    assert fake.session_command(["reboot"], tmp_path) == 2
    assert "usage" in capsys.readouterr().err
    events, offset = fake.read_session_events(path, 0)
    assert [e.kind for e in events] == ["lock", "unlock", "logoff", "logon"]
    assert {e.session_id for e in events} == {fake.FAKE_SESSION_ID}
    assert offset == path.stat().st_size
    assert fake.read_session_events(path, offset) == ([], offset)


def test_fake_reader_skips_bad_and_partial_lines(tmp_path, caplog):
    path = tmp_path / fake.SESSION_FILE
    path.write_text('not json\n{"event": "lock", "session_id": 1}\n{"event": "unl', encoding="utf-8")
    events, offset = fake.read_session_events(path, 0)
    assert [e.kind for e in events] == ["lock"]
    assert offset < path.stat().st_size
    assert "ignoring bad line" in caplog.text


def test_fake_dispatch_tracks_logon_state(session_state):
    seen = []
    fake.set_session_listener(seen.append)
    assert fake.current_session() is not None
    fake.dispatch_session_event(fake.SessionEvent("logoff", 1))
    assert fake.current_session() is None
    fake.dispatch_session_event(fake.SessionEvent("logon", 1))
    assert fake.current_session().session_id == 1
    assert [e.kind for e in seen] == ["logoff", "logon"]


@pytest.mark.anyio
async def test_fake_watcher_emits_only_new_events(tmp_path, session_state):
    fake.session_command(["lock"], tmp_path)
    seen = []
    fake.set_session_listener(seen.append)
    task = asyncio.create_task(fake.watch_session_file(tmp_path / fake.SESSION_FILE, interval=0.01))
    await asyncio.sleep(0.03)
    fake.session_command(["unlock"], tmp_path)
    for _ in range(100):
        if seen:
            break
        await asyncio.sleep(0.01)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    assert [e.kind for e in seen] == ["unlock"]


def test_fake_launch_tray_override(monkeypatch, data_dir):
    monkeypatch.setenv("OGK_FAKE_TRAY_CMD", "sleep 30")
    process = fake.launch_tray(1)
    assert process.alive()
    process.terminate()
    assert not process.alive()


def test_fake_launch_tray_blocked(monkeypatch, data_dir):
    monkeypatch.setenv("OGK_FAKE_TRAY_CMD", "/usr/bin/false")
    process = fake.launch_tray(1)
    process._process.wait(5)
    assert not process.alive()


def test_fake_default_tray_command(monkeypatch):
    monkeypatch.delenv("OGK_FAKE_TRAY_CMD", raising=False)
    command = fake.tray_command()
    assert command[-1].endswith("ogk_tray.py")

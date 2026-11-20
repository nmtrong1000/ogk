import hashlib
import os

from service.modules.appcontrol.hashing import HashCache


def test_hash_matches_and_is_cached(tmp_path):
    exe = tmp_path / "game.exe"
    exe.write_bytes(b"x" * 3_000_000)
    cache = HashCache()
    expected = hashlib.sha256(b"x" * 3_000_000).hexdigest()
    assert cache.get(str(exe)) == expected
    assert cache.get(str(exe)) == expected
    assert cache.computed == 1


def test_changed_file_is_hashed_again(tmp_path):
    exe = tmp_path / "game.exe"
    exe.write_bytes(b"one")
    cache = HashCache()
    first = cache.get(str(exe))
    exe.write_bytes(b"two!")
    assert cache.get(str(exe)) == hashlib.sha256(b"two!").hexdigest() != first
    assert cache.computed == 2


def test_same_size_new_mtime_is_hashed_again(tmp_path):
    exe = tmp_path / "game.exe"
    exe.write_bytes(b"aaa")
    cache = HashCache()
    cache.get(str(exe))
    exe.write_bytes(b"bbb")
    stat = exe.stat()
    os.utime(exe, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))
    assert cache.get(str(exe)) == hashlib.sha256(b"bbb").hexdigest()


def test_missing_or_empty_path_gives_none(tmp_path):
    cache = HashCache()
    assert cache.get("") is None
    assert cache.get(str(tmp_path / "missing.exe")) is None


def test_uses_the_given_reader(tmp_path):
    exe = tmp_path / "locked.exe"
    exe.write_bytes(b"on disk")
    calls = []

    def reader(path, size):
        calls.append(path)
        yield b"read past the dacl"

    assert HashCache(reader).get(str(exe)) == hashlib.sha256(b"read past the dacl").hexdigest()
    assert calls == [str(exe)]


def test_reader_error_returns_none(tmp_path):
    exe = tmp_path / "locked.exe"
    exe.write_bytes(b"x")

    def reader(path, size):
        raise PermissionError(5, "Access is denied", path)
        yield b""

    assert HashCache(reader).get(str(exe)) is None

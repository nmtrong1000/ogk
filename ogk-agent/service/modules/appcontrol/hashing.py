"""HashCache methods block on file I/O; the module calls them through asyncio.to_thread.
A file that changed size or mtime is hashed again, so swapping a game in place of an allowed exe under the
same path is not hidden by the cache. The reader comes from platform/ so Windows can read past a DACL that
denies SYSTEM; get() returns None when the file still cannot be read, and the caller decides what that means.
"""

import hashlib
import os
import threading
from collections.abc import Callable, Iterator
from pathlib import Path

CHUNK_SIZE = 1024 * 1024

Reader = Callable[[str, int], Iterator[bytes]]


def read_file(path: str, size: int) -> Iterator[bytes]:
    with Path(path).open("rb") as file:
        while chunk := file.read(size):
            yield chunk


def sha256_file(path: str, reader: Reader = read_file) -> str:
    digest = hashlib.sha256()
    for chunk in reader(path, CHUNK_SIZE):
        digest.update(chunk)
    return digest.hexdigest()


class HashCache:
    def __init__(self, reader: Reader = read_file) -> None:
        self._reader = reader
        self._entries: dict[str, tuple[int, int, str]] = {}
        self._lock = threading.Lock()
        self.computed = 0

    def get(self, path: str) -> str | None:
        if not path:
            return None
        try:
            stat = os.stat(path)
        except OSError:
            return None
        with self._lock:
            entry = self._entries.get(path)
        if entry is not None and entry[:2] == (stat.st_size, stat.st_mtime_ns):
            return entry[2]
        try:
            value = sha256_file(path, self._reader)
        except OSError:
            return None
        with self._lock:
            self._entries[path] = (stat.st_size, stat.st_mtime_ns, value)
            self.computed += 1
        return value

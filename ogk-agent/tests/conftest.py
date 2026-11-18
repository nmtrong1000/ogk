"""data_dir points the fake platform (and fake DPAPI key) at a temp dir so tests never touch .ogk-data."""

import json

import pytest


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def write_config(tmp_path):
    def _write(data) -> None:
        (tmp_path / "config.json").write_text(json.dumps(data), encoding="utf-8")

    return _write


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("OGK_DATA_DIR", str(tmp_path))
    return tmp_path

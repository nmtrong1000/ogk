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

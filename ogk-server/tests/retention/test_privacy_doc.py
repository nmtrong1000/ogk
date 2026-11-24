"""app.main is imported so every module's models are registered on Base.metadata before it is read."""

import re
from pathlib import Path

import app.main
from app.core.db import Base

PRIVACY = Path(__file__).resolve().parents[3] / "PRIVACY.md"
FIELD = re.compile(r"^\| `(\w+)\.(\w+)` \|", re.MULTILINE)


def documented(heading: str) -> set[tuple[str, str]]:
    text = PRIVACY.read_text(encoding="utf-8")
    section = text.split(f"\n## {heading}", 1)[1].split("\n## ", 1)[0]
    return set(FIELD.findall(section))


def test_every_server_column_is_in_privacy_doc():
    assert app.main.create_app
    columns = {(table.name, column.name) for table in Base.metadata.sorted_tables for column in table.columns}
    fields = documented("DB của server")
    assert sorted(columns - fields) == []
    assert sorted(fields - columns) == []

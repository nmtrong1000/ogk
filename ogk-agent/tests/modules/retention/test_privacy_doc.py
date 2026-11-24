import re
import sqlite3
from pathlib import Path

from service.core.local_db import DB_FILE, LocalDb

PRIVACY = Path(__file__).resolve().parents[4] / "PRIVACY.md"
FIELD = re.compile(r"^\| `(\w+)\.(\w+)` \|", re.MULTILINE)


def test_every_agent_column_is_in_privacy_doc(data_dir):
    LocalDb(data_dir).schema_version()
    with sqlite3.connect(data_dir / DB_FILE) as conn:
        tables = [
            name
            for (name,) in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        ]
        columns = {(table, row[1]) for table in tables for row in conn.execute(f"PRAGMA table_info({table})")}
    section = PRIVACY.read_text(encoding="utf-8").split("\n## DB trên máy trẻ", 1)[1].split("\n## ", 1)[0]
    fields = set(FIELD.findall(section))
    assert sorted(columns - fields) == []
    assert sorted(fields - columns) == []

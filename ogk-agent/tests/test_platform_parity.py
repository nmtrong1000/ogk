"""windows.py cannot be imported on the Mac (pywin32), so the parity with fake.py is checked on the source:
every public function of fake.py must be defined or imported at the top level of windows.py.
FAKE_ONLY lists the Mac session simulator hooks; service/main.py reaches them through hasattr.
"""

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FAKE_ONLY = {
    "service/platform": {
        "dispatch_session_event",
        "read_session_events",
        "session_command",
        "tray_command",
        "watch_session_file",
    },
    "tray/platform": set(),
}


def _public_functions(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_")
    }


def _top_level_names(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            names.update(alias.asname or alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.Assign):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
    return names


@pytest.mark.parametrize("package", ["service/platform", "tray/platform"])
def test_windows_platform_has_every_fake_function(package):
    fake = ROOT / package / "fake.py"
    windows = ROOT / package / "windows.py"
    missing = _public_functions(fake) - FAKE_ONLY[package] - _top_level_names(windows)
    assert missing == set()

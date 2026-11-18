"""Claude Code Stop hook: auto-fix lint and format the files changed in the working tree.

Python files in ogk-server and ogk-agent go through ruff check --fix and ruff format, each with its app's ruff.toml.
Dashboard files go through oxlint --fix and prettier --write (configs in ogk-dashboard).
If errors remain that cannot be fixed automatically, the hook blocks the stop once and hands them to Claude;
when stop_hook_active is already true it only reports them to the user, so it can never loop.
Output is capped so a large error list does not flood the context.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
PY_APPS = ("ogk-server/", "ogk-agent/")
DASHBOARD = "ogk-dashboard/"
OXLINT_EXT = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}
PRETTIER_EXT = OXLINT_EXT | {".css", ".json", ".html"}
MAX_REPORT = 4000


def changed_files() -> list[str]:
    out = subprocess.run(
        ["git", "status", "--porcelain", "-z", "--untracked-files=all"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout.decode()
    entries = out.split("\0")
    files, i = [], 0
    while i < len(entries):
        entry = entries[i]
        i += 1
        if len(entry) < 4:
            continue
        status, path = entry[:2], entry[3:]
        if status[0] in "RC":
            i += 1
        if "D" in status or not (ROOT / path).is_file():
            continue
        files.append(path)
    return files


def digest(paths: list[str]) -> dict[str, str]:
    return {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths if (ROOT / p).is_file()}


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def ruff_binary(app: str) -> str | None:
    candidate = ROOT / app / ".venv" / "bin" / "ruff"
    return str(candidate) if candidate.is_file() else shutil.which("ruff")


def python_pass(files: list[str], problems: list[str]) -> None:
    for app in PY_APPS:
        rel = [f[len(app) :] for f in files if f.startswith(app)]
        if not rel:
            continue
        ruff = ruff_binary(app)
        if ruff is None:
            problems.append(f"ruff is not installed: pip install -r {app}requirements-dev.txt")
            continue
        cwd = ROOT / app
        run([ruff, "check", "--fix", "--quiet", *rel], cwd)
        run([ruff, "format", "--quiet", *rel], cwd)
        result = run([ruff, "check", "--output-format", "concise", "--quiet", *rel], cwd)
        if result.returncode != 0:
            problems.append(f"ruff (paths relative to {app}):\n" + (result.stdout + result.stderr).strip())


def dashboard_pass(files: list[str], problems: list[str]) -> None:
    app = ROOT / DASHBOARD
    rel = [f[len(DASHBOARD) :] for f in files]
    lint = [f for f in rel if Path(f).suffix in OXLINT_EXT]
    fmt = [f for f in rel if Path(f).suffix in PRETTIER_EXT and f != "package-lock.json"]
    if not lint and not fmt:
        return
    bin_dir = app / "node_modules" / ".bin"
    if not (bin_dir / "oxlint").is_file() or not (bin_dir / "prettier").is_file():
        problems.append("oxlint or prettier is missing: run npm install in ogk-dashboard")
        return
    if lint:
        run([str(bin_dir / "oxlint"), "--fix", *lint], app)
    if fmt:
        run([str(bin_dir / "prettier"), "--write", "--ignore-unknown", "--log-level", "warn", *fmt], app)
    if lint:
        result = run([str(bin_dir / "oxlint"), "--format", "unix", *lint], app)
        if result.returncode != 0:
            problems.append("oxlint (paths relative to ogk-dashboard):\n" + (result.stdout + result.stderr).strip())


def main() -> None:
    payload = json.loads(sys.stdin.read() or "{}")
    files = changed_files()
    py = [f for f in files if f.endswith(".py") and f.startswith(PY_APPS)]
    dash = [f for f in files if f.startswith(DASHBOARD)]
    if not py and not dash:
        return
    before = digest(py + dash)
    problems: list[str] = []
    python_pass(py, problems)
    dashboard_pass(dash, problems)
    after = digest(py + dash)
    touched = [p for p in before if before[p] != after.get(p)]

    if problems:
        report = "\n\n".join(problems)[:MAX_REPORT]
        if payload.get("stop_hook_active"):
            print(json.dumps({"systemMessage": "Lint errors remain after auto-fix:\n" + report}))
        else:
            reason = "Lint errors remain after auto-fix. Fix them, then stop:\n" + report
            print(json.dumps({"decision": "block", "reason": reason}))
        return
    if touched:
        print(json.dumps({"systemMessage": f"Lint/format auto-fixed {len(touched)} file(s): " + ", ".join(touched)}))


if __name__ == "__main__":
    main()

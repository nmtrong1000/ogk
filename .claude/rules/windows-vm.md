---
paths:
  - "ogk-agent/**"
---

# Windows VM testing and agent pitfalls

## Agent code

- The Stop hook's `ruff check --fix` silently deletes imports that a module only re-exports (F401), such as `service/platform/windows.py` re-exporting `process.py`. List those names in `__all__`; `tests/test_platform_parity.py` catches a function that `fake.py` has and `windows.py` lacks.

## The VM (from P13)

- UTM "OGK Windows 11"; the stopped clone "OGK Windows 11 - clean" is the restore point. Start it with `/Applications/UTM.app/Contents/MacOS/utmctl start "OGK Windows 11"`.
- SSH: `ssh -i ~/.ssh/ogk_vm_ed25519 tom@192.168.64.2`. `tom` is the admin, `An` the standard child account with no password. SSH runs in session 0, so it cannot show or click windows in An's session.
- Agent source in the VM: `C:\ogk-setup\ogk-agent` with its own `.venv`. The server runs on the Mac at `https://192.168.100.238:8443` (LAN IP in the certificate).
- The VM clock is Pacific; schedules use the child PC's local time.
- Never type passwords; the seed password lives in the gitignored root `tmp.txt`.

## Updating the agent in place

Never run `uninstall.ps1` for an update: it wipes the enrollment.

1. Sync from `ogk-agent/`: `COPYFILE_DISABLE=1 tar --exclude __pycache__ -cf - service tray | ssh ... "tar -xf - -C C:/ogk-setup/ogk-agent"`.
2. Build from cmd: `cd /d C:\ogk-setup\ogk-agent && set PATH=C:\ogk-setup\ogk-agent\.venv\Scripts;%PATH% && powershell -NoProfile -ExecutionPolicy Bypass -File installer\build.ps1 > build.log 2>&1`. Redirecting with `*>` inside PowerShell 5.1 turns PyInstaller's stderr INFO lines into a fatal error.
3. `Stop-Service OGKAgent -Force`, stop `ogk-tray`, copy `dist\ogk-service.exe` and `dist\ogk-tray.exe` to `C:\Program Files\OGK`, `Start-Service OGKAgent`.

## Watching a test

- Tail `C:\ProgramData\OGK\logs\service.log` and poll processes over SSH while the user acts in An's session.
- Query the server's `ogk-server/data/ogk.db` read-only (`file:...?mode=ro`) for events and policy versions.

## Test exes on Windows 11

- A renamed System32 app quits silently unless `en-US\<new name>.mui` sits next to it; copy the `.mui` too.
- The `notepad.exe` stub cannot be renamed at all; use `charmap.exe` with its `.mui`.
- Double-clicking a file named `explorer.exe` runs the real Explorer; launch such files from cmd.
- Files an admin creates in `C:\Windows\Temp` are unreadable to An; An must create them.

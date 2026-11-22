$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent

Push-Location $Root
try {
    python -m PyInstaller --noconfirm --onefile --name ogk-service `
        --hidden-import win32timezone `
        --collect-data tldextract `
        --exclude-module service.devtools `
        --add-data "data;data" `
        --distpath dist --workpath build `
        ogk_service.py
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller ogk-service that bai" }

    python -m PyInstaller --noconfirm --onefile --windowed --name ogk-tray `
        --distpath dist --workpath build `
        ogk_tray.py
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller ogk-tray that bai" }
} finally {
    Pop-Location
}

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent

Push-Location $Root
try {
    python -m PyInstaller --noconfirm --onefile --name ogk-service `
        --hidden-import win32timezone `
        --distpath dist --workpath build `
        ogk_service.py
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller that bai" }
} finally {
    Pop-Location
}

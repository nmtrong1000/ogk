#Requires -RunAsAdministrator
param(
    [Parameter(Mandatory = $true)] [string]$ServerUrl,
    [Parameter(Mandatory = $true)] [string]$CaCert,
    [Parameter(Mandatory = $true)] [string]$PolicyPublicKey,
    [string]$Exe = (Join-Path $PSScriptRoot "..\dist\ogk-service.exe"),
    [string]$TrayExe = (Join-Path $PSScriptRoot "..\dist\ogk-tray.exe")
)
$ErrorActionPreference = "Stop"

$ServiceName = "OGKAgent"
$InstallDir = Join-Path $env:ProgramFiles "OGK"
$DataDir = Join-Path $env:ProgramData "OGK"
$ServiceExe = Join-Path $InstallDir "ogk-service.exe"
$TrayTarget = Join-Path $InstallDir "ogk-tray.exe"

if (Get-Service $ServiceName -ErrorAction SilentlyContinue) {
    throw "Service $ServiceName da duoc cai. Chay uninstall.ps1 truoc."
}

New-Item -ItemType Directory -Force -Path $InstallDir, $DataDir | Out-Null
icacls $DataDir /inheritance:r /grant:r "*S-1-5-18:(OI)(CI)F" "*S-1-5-32-544:(OI)(CI)F" | Out-Null

Copy-Item $Exe $ServiceExe -Force
Copy-Item $TrayExe $TrayTarget -Force
Copy-Item $CaCert (Join-Path $DataDir "ca.crt") -Force
Copy-Item $PolicyPublicKey (Join-Path $DataDir "policy_public.pem") -Force
@{ server_url = $ServerUrl; ca_cert = "ca.crt"; policy_public_key = "policy_public.pem"; health_interval = 30 } |
    ConvertTo-Json | Set-Content -Encoding UTF8 (Join-Path $DataDir "config.json")

& $ServiceExe --startup auto install
if (-not (Get-Service $ServiceName -ErrorAction SilentlyContinue)) {
    throw "Cai service $ServiceName that bai."
}
sc.exe failure $ServiceName reset= 86400 actions= restart/5000/restart/5000/restart/5000 | Out-Null
sc.exe failureflag $ServiceName 1 | Out-Null

Start-Service $ServiceName
Get-Service $ServiceName
Write-Host "Next: create a pairing code on the dashboard, then run: & '$ServiceExe' enroll"

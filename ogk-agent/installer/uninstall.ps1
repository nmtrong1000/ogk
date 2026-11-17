#Requires -RunAsAdministrator
$ErrorActionPreference = "Stop"

$ServiceName = "OGKAgent"
$InstallDir = Join-Path $env:ProgramFiles "OGK"
$DataDir = Join-Path $env:ProgramData "OGK"

$service = Get-Service $ServiceName -ErrorAction SilentlyContinue
if ($service) {
    if ($service.Status -ne "Stopped") {
        Stop-Service $ServiceName -Force
    }
    sc.exe delete $ServiceName | Out-Null
}
Wait-Process -Name "ogk-service" -Timeout 15 -ErrorAction SilentlyContinue

Remove-Item $InstallDir, $DataDir -Recurse -Force -ErrorAction SilentlyContinue
Write-Output "Da go $ServiceName"

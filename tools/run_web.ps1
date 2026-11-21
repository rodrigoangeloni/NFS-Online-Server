param(
    [string]$PublicHost = "192.0.2.37",
    [int]$Port = 8081,
    [switch]$InviteRequired
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$downloads = Join-Path (Split-Path -Parent $root) "NFS-Online-Artifacts\downloads"

$env:PYTHONPATH = Join-Path $root "server"
$env:NFS_WEB_CONFIG = Join-Path $root "config\server.toml"
$env:NFS_WEB_DOWNLOADS_DIR = $downloads
$env:NFS_WEB_PUBLIC_HOST = $PublicHost
$env:NFS_WEB_SITE_URL = "http://${PublicHost}:$Port"
$env:NFS_WEB_ALLOW_INSECURE = "1"
$env:NFS_WEB_INVITE_REQUIRED = if ($InviteRequired) { "1" } else { "0" }

Write-Host ""
Write-Host "NFS Online web"
Write-Host "  URL:      http://${PublicHost}:$Port"
Write-Host "  Descargas: $downloads"
Write-Host "  Registro: $(if ($InviteRequired) { 'solo con invitacion' } else { 'abierto' })"
Write-Host ""
Write-Host "Presiona Ctrl+C para detener."
Write-Host ""

python -m uvicorn web.app:app --host 0.0.0.0 --port $Port

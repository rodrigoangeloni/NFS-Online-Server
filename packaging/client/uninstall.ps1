[CmdletBinding()]
param(
    [string]$U2Path = "",
    [string]$MWPath = "",
    [switch]$NoElevate,
    [switch]$NoPause,
    [switch]$Yes
)

$ErrorActionPreference = 'Stop'
$script:Root = Split-Path -Parent $MyInvocation.MyCommand.Path

function Write-Step([string]$Text) { Write-Host $Text -ForegroundColor Green }
function Write-Warn([string]$Text) { Write-Host $Text -ForegroundColor Yellow }

function Test-Admin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-Admin) -and -not $NoElevate) {
    $arguments = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$PSCommandPath`"")
    if ($U2Path) { $arguments += @("-U2Path", "`"$U2Path`"") }
    if ($MWPath) { $arguments += @("-MWPath", "`"$MWPath`"") }
    $process = Start-Process -FilePath "powershell.exe" -Verb RunAs -ArgumentList $arguments -PassThru -Wait
    exit $process.ExitCode
}

$Games = @{
    u2 = @{
        Name = "Need for Speed Underground 2"
        Exe = "SPEED2.EXE"
        Source = "U2"
        Registry = @("Need for Speed Underground 2")
        Folders = @("Need for Speed Underground 2")
        Files = @(
            "net_u2.asi",
            "net_u2.ini",
            "scripts\NFSUnderground2.WidescreenFix.asi",
            "scripts\NFSUnderground2.WidescreenFix.ini",
            "scripts\NFSUnderground2.WidescreenFix.dat"
        )
    }
    mw = @{
        Name = "Need for Speed Most Wanted"
        Exe = "speed.exe"
        Source = "MW"
        Registry = @("Need for Speed Most Wanted", "Need for Speed Most Wanted 2005")
        Folders = @("Need for Speed Most Wanted 2005", "Need for Speed Most Wanted")
        Files = @(
            "net_mw.asi",
            "net_mw.ini",
            "scripts\NFSMostWanted.WidescreenFix.asi",
            "scripts\NFSMostWanted.WidescreenFix.ini",
            "scripts\NFSMostWanted.WidescreenFix.tpk"
        )
    }
}

function Test-GameDir([string]$Directory, [string]$Exe) {
    if (-not $Directory) { return $false }
    return (Test-Path -LiteralPath (Join-Path $Directory $Exe) -PathType Leaf)
}

function Get-RegistryDir([string[]]$Keys) {
    foreach ($root in @("HKLM:\SOFTWARE\WOW6432Node\EA Games", "HKLM:\SOFTWARE\EA Games", "HKCU:\SOFTWARE\EA Games")) {
        foreach ($key in $Keys) {
            $path = "$root\$key"
            if (Test-Path -LiteralPath $path) {
                $item = Get-ItemProperty -LiteralPath $path -ErrorAction SilentlyContinue
                if ($null -ne $item) {
                    foreach ($name in @("Install Dir", "InstallDir", "Path")) {
                        $value = $item.$name
                        if ($value) { return ([string]$value).TrimEnd("\") }
                    }
                }
            }
        }
    }
    return $null
}

function Resolve-GameDir([string]$Game, $Info) {
    $override = ""
    if ($Game -eq "u2") { $override = $U2Path }
    if ($Game -eq "mw") { $override = $MWPath }
    if ($override -and (Test-GameDir $override $Info.Exe)) { return $override.TrimEnd("\") }
    $registry = Get-RegistryDir $Info.Registry
    if ($registry -and (Test-GameDir $registry $Info.Exe)) { return $registry }
    $bases = @()
    if (${env:ProgramFiles(x86)}) { $bases += ${env:ProgramFiles(x86)} }
    if ($env:ProgramFiles) { $bases += $env:ProgramFiles }
    $bases += @("D:\Games", "D:\Juegos", "E:\Games", "E:\Juegos")
    foreach ($base in $bases) {
        foreach ($folder in $Info.Folders) {
            $candidate = Join-Path $base $folder
            if (Test-GameDir $candidate $Info.Exe) { return $candidate.TrimEnd("\") }
        }
    }
    return $null
}

Write-Host ""
Write-Host "============================================"
Write-Host " NFS ONLINE - DESINSTALADOR"
Write-Host "============================================"
Write-Host ""
Write-Host "Esto quita el cliente online y el fix de pantalla."
Write-Host "No borra el ASI Loader ni tus partidas."
Write-Host ""

$targets = @()
foreach ($game in @("u2", "mw")) {
    $info = $Games[$game]
    if (-not (Test-Path -LiteralPath (Join-Path $script:Root $info.Source) -PathType Container)) { continue }
    $dir = Resolve-GameDir $game $info
    if (-not $dir) { continue }
    foreach ($relative in $info.Files) {
        $path = Join-Path $dir $relative
        if (Test-Path -LiteralPath $path -PathType Leaf) {
            $targets += [pscustomobject]@{ Game = $info.Name; Path = $path }
        }
    }
}

if ($targets.Count -eq 0) {
    Write-Warn "No encontre archivos de NFS Online instalados."
    if (-not $NoPause) { Read-Host "Presiona Enter para cerrar" | Out-Null }
    exit 0
}

Write-Host "Se van a quitar:"
foreach ($target in $targets) { Write-Host "  $($target.Path)" }
Write-Host ""
if (-not $Yes) {
    $answer = Read-Host "Escribi SI para continuar"
    if ($answer.Trim().ToUpperInvariant() -ne "SI") {
        Write-Warn "Cancelado."
        if (-not $NoPause) { Read-Host "Presiona Enter para cerrar" | Out-Null }
        exit 0
    }
}

foreach ($target in $targets) {
    try {
        Remove-Item -LiteralPath $target.Path -Force
        Write-Host "  quitado: $($target.Path)"
    }
    catch {
        Write-Warn "  no se pudo quitar: $($target.Path)"
    }
}

foreach ($game in @("u2", "mw")) {
    $info = $Games[$game]
    if (-not (Test-Path -LiteralPath (Join-Path $script:Root $info.Source) -PathType Container)) { continue }
    $dir = Resolve-GameDir $game $info
    if (-not $dir) { continue }
    $scripts = Join-Path $dir "scripts"
    if (Test-Path -LiteralPath $scripts -PathType Container) {
        if (-not (Get-ChildItem -LiteralPath $scripts -Force | Select-Object -First 1)) {
            Remove-Item -LiteralPath $scripts -Force -ErrorAction SilentlyContinue
        }
    }
}

Write-Step "Listo. El cliente y el fix fueron desinstalados."
Write-Host "Los backups siguen en Documentos\NFS-Online\Backup."
if (-not $NoPause) { Read-Host "Presiona Enter para cerrar" | Out-Null }
exit 0

[CmdletBinding()]
param(
    [string]$U2Path = "",
    [string]$MWPath = "",
    [switch]$NoElevate,
    [switch]$NoPause
)

$ErrorActionPreference = 'Stop'
$script:Root = Split-Path -Parent $MyInvocation.MyCommand.Path

function Write-Step([string]$Text) {
    Write-Host $Text -ForegroundColor Green
}

function Write-Warn([string]$Text) {
    Write-Host $Text -ForegroundColor Yellow
}

function Write-Err([string]$Text) {
    Write-Host $Text -ForegroundColor Red
}

function Test-Admin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-Admin) -and -not $NoElevate) {
    Write-Host "Se necesitan permisos de administrador."
    Write-Host "Windows va a mostrar un aviso; acepta para continuar."
    $arguments = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$PSCommandPath`"")
    if ($U2Path) { $arguments += @("-U2Path", "`"$U2Path`"") }
    if ($MWPath) { $arguments += @("-MWPath", "`"$MWPath`"") }
    try {
        $process = Start-Process -FilePath "powershell.exe" -Verb RunAs -ArgumentList $arguments -PassThru -Wait
        exit $process.ExitCode
    }
    catch {
        Write-Err "No se pudo pedir permisos de administrador."
        Write-Host $_.Exception.Message
        if (-not $NoPause) { Read-Host "Presiona Enter para cerrar" | Out-Null }
        exit 1
    }
}

$Games = @{
    u2 = @{
        Name = "Need for Speed Underground 2"
        Exe = "SPEED2.EXE"
        Source = "U2"
        Net = "net_u2.asi"
        Ini = "net_u2.ini"
        Registry = @("Need for Speed Underground 2")
        Folders = @("Need for Speed Underground 2")
    }
    mw = @{
        Name = "Need for Speed Most Wanted"
        Exe = "speed.exe"
        Source = "MW"
        Net = "net_mw.asi"
        Ini = "net_mw.ini"
        Registry = @("Need for Speed Most Wanted", "Need for Speed Most Wanted 2005")
        Folders = @("Need for Speed Most Wanted 2005", "Need for Speed Most Wanted")
    }
}

function Test-GameDir([string]$Directory, [string]$Exe) {
    if (-not $Directory) { return $false }
    return (Test-Path -LiteralPath (Join-Path $Directory $Exe) -PathType Leaf)
}

function Get-RegistryDir([string[]]$Keys) {
    $roots = @(
        "HKLM:\SOFTWARE\WOW6432Node\EA Games",
        "HKLM:\SOFTWARE\EA Games",
        "HKCU:\SOFTWARE\EA Games"
    )
    foreach ($root in $roots) {
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

function Get-CommonDirs($Info) {
    $results = New-Object System.Collections.Generic.List[string]
    $drives = @()
    try {
        $drives = Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" -ErrorAction Stop |
            ForEach-Object { $_.DeviceID + "\" }
    }
    catch {
        $drives = @("C:\")
    }
    if (-not $drives -or $drives.Count -eq 0) { $drives = @("C:\") }
    foreach ($drive in $drives) {
        foreach ($base in @("Program Files (x86)", "Program Files", "Games", "Juegos", "")) {
            foreach ($folder in $Info.Folders) {
                if ($base) {
                    $results.Add((Join-Path (Join-Path $drive $base) $folder))
                }
                else {
                    $results.Add((Join-Path $drive $folder))
                }
            }
        }
    }
    return $results
}

function Select-GameDir($Info) {
    Add-Type -AssemblyName System.Windows.Forms
    $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
    $dialog.Description = "Elegi la carpeta de $($Info.Name) (donde esta $($Info.Exe))"
    $dialog.ShowNewFolderButton = $false
    if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
        return $dialog.SelectedPath
    }
    return $null
}

function Resolve-GameDir([string]$Game, $Info) {
    $override = ""
    if ($Game -eq "u2") { $override = $U2Path }
    if ($Game -eq "mw") { $override = $MWPath }
    if ($override) {
        if (Test-GameDir $override $Info.Exe) { return $override.TrimEnd("\") }
        Write-Warn "La ruta indicada para $($Info.Name) no contiene $($Info.Exe)."
    }

    $registry = Get-RegistryDir $Info.Registry
    if ($registry -and (Test-GameDir $registry $Info.Exe)) { return $registry }

    foreach ($candidate in (Get-CommonDirs $Info)) {
        if (Test-GameDir $candidate $Info.Exe) { return $candidate }
    }

    Write-Warn "No encontre $($Info.Name) automaticamente."
    Write-Host "Se va a abrir una ventana para elegir la carpeta."
    $selected = Select-GameDir $Info
    if ($selected -and (Test-GameDir $selected $Info.Exe)) { return $selected.TrimEnd("\") }
    if ($selected) {
        Write-Err "La carpeta elegida no contiene $($Info.Exe)."
    }
    return $null
}

function Backup-File([string]$Path, [string]$BackupDir, [string]$Relative) {
    if (Test-Path -LiteralPath $Path -PathType Leaf) {
        $destination = Join-Path $BackupDir $Relative
        $parent = Split-Path -Parent $destination
        if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
        Copy-Item -LiteralPath $Path -Destination $destination -Force
        Write-Host "  backup: $Relative"
    }
}

function Install-Game([string]$Game, $Info, [string]$GameDir, [string]$Stamp) {
    $source = Join-Path $script:Root $Info.Source
    if (-not (Test-Path -LiteralPath $source -PathType Container)) { return $false }

    $netSource = Join-Path $source $Info.Net
    $iniSource = Join-Path $source $Info.Ini
    $scriptsSource = Join-Path $source "scripts"
    if (-not (Test-Path -LiteralPath $netSource -PathType Leaf)) {
        throw "Falta $($Info.Net) dentro del paquete."
    }
    if (-not (Test-Path -LiteralPath $iniSource -PathType Leaf)) {
        throw "Falta $($Info.Ini) dentro del paquete."
    }
    if (-not (Test-Path -LiteralPath $scriptsSource -PathType Container)) {
        throw "Falta la carpeta scripts dentro del paquete."
    }

    Write-Step "Instalando $($Info.Name) en:"
    Write-Host "  $GameDir"

    $backupDir = Join-Path ([Environment]::GetFolderPath("MyDocuments")) "NFS-Online\Backup\$Stamp\$Game"
    New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

    Backup-File (Join-Path $GameDir $Info.Net) $backupDir $Info.Net
    Backup-File (Join-Path $GameDir $Info.Ini) $backupDir $Info.Ini

    $scriptsTarget = Join-Path $GameDir "scripts"
    New-Item -ItemType Directory -Force -Path $scriptsTarget | Out-Null
    foreach ($file in Get-ChildItem -LiteralPath $scriptsSource -File) {
        Backup-File (Join-Path $scriptsTarget $file.Name) $backupDir ("scripts\" + $file.Name)
    }

    Copy-Item -LiteralPath $netSource -Destination (Join-Path $GameDir $Info.Net) -Force
    Copy-Item -LiteralPath $iniSource -Destination (Join-Path $GameDir $Info.Ini) -Force
    foreach ($file in Get-ChildItem -LiteralPath $scriptsSource -File) {
        Copy-Item -LiteralPath $file.FullName -Destination (Join-Path $scriptsTarget $file.Name) -Force
    }

    $loaders = @("dinput8.dll", "dsound.dll", "version.dll", "winmm.dll", "d3d8.dll", "d3d9.dll", "dxgi.dll")
    $existingLoaders = @($loaders | Where-Object { Test-Path -LiteralPath (Join-Path $GameDir $_) -PathType Leaf })
    if ($existingLoaders.Count -eq 0) {
        $loader = Join-Path $script:Root "loader\dinput8.dll"
        if (Test-Path -LiteralPath $loader -PathType Leaf) {
            Copy-Item -LiteralPath $loader -Destination (Join-Path $GameDir "dinput8.dll") -Force
            Write-Host "  ASI Loader instalado (dinput8.dll)."
        }
        else {
            Write-Warn "  No hay loader en el paquete; el juego puede no cargar el fix."
        }
    }
    else {
        Write-Host "  Se conserva el loader existente: $($existingLoaders -join ', ')"
    }

    $required = @(
        (Join-Path $GameDir $Info.Net),
        (Join-Path $GameDir $Info.Ini)
    )
    foreach ($file in Get-ChildItem -LiteralPath $scriptsSource -File) {
        $required += (Join-Path $scriptsTarget $file.Name)
    }
    foreach ($file in $required) {
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
            throw "No se pudo verificar $file"
        }
    }

    Write-Step "  OK: $($Info.Name) quedo instalado."
    Write-Host "  Backup: $backupDir"
    return $true
}

Write-Host ""
Write-Host "============================================"
Write-Host " NFS ONLINE - INSTALADOR DE CLIENTE"
Write-Host "============================================"
Write-Host ""
Write-Host "Este instalador copia el cliente online y el fix de pantalla."
Write-Host "No modifica tu instalacion del juego mas que agregar esos archivos."
Write-Host ""

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$installed = @()

foreach ($game in @("u2", "mw")) {
    $info = $Games[$game]
    $source = Join-Path $script:Root $info.Source
    if (-not (Test-Path -LiteralPath $source -PathType Container)) { continue }
    $gameDir = Resolve-GameDir $game $info
    if (-not $gameDir) {
        Write-Warn "No se instalo $($info.Name)."
        continue
    }
    $ok = Install-Game $game $info $gameDir $stamp
    if ($ok) { $installed += $info.Name }
}

Write-Host ""
if ($installed.Count -eq 0) {
    Write-Err "No se encontro ningun juego para instalar."
    Write-Host "Proba de nuevo y elegi la carpeta que contiene SPEED2.EXE o speed.exe."
    if (-not $NoPause) { Read-Host "Presiona Enter para cerrar" | Out-Null }
    exit 1
}

Write-Step "Listo. Se instalo en:"
foreach ($name in $installed) { Write-Host "  - $name" }
Write-Host ""
Write-Host "Podes abrir el juego y entrar con tu cuenta de la web."
Write-Host "La pantalla se va a ver sin bordes y sin la barra de Windows."
Write-Host ""
if (-not $NoPause) { Read-Host "Presiona Enter para cerrar" | Out-Null }
exit 0

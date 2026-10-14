#requires -Version 5.1
<#
Instala EVA-01 Audio para el usuario actual, sin administrador.
-Root redirige TODAS las rutas a un perfil de pruebas. No lanza Spotifast.
-SkipDownload exige un spotifast.exe existente (no comprueba su procedencia).
-DryRun no escribe ni descarga. Los recursos sustituidos quedan en backups.
Cambia apariencia, idioma y nombre del dispositivo Spotify Connect; abre la biblioteca.
#>
[CmdletBinding()]
param(
    [ValidateSet('EVA-01', 'EVA-01 Terminal')][string]$Theme = 'EVA-01',
    [switch]$DryRun,
    [switch]$SkipDownload,
    [string]$Root,
    [ValidateSet('Auto', 'x86_64', 'aarch64')][string]$Architecture = 'Auto'
)
Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'

function Write-EvaJson([string]$Path, $Value) {
    $temporary = $Path + '.' + [guid]::NewGuid().ToString('N') + '.tmp'
    try {
        $json = ConvertTo-Json -InputObject $Value -Depth 100
        [IO.File]::WriteAllText($temporary, $json + [Environment]::NewLine, (New-Object Text.UTF8Encoding($false)))
        Move-Item -LiteralPath $temporary -Destination $Path -Force
    } finally {
        if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Force }
    }
}
function Read-EvaSettings([string]$Path) {
    if (!(Test-Path -LiteralPath $Path)) { return [pscustomobject]@{} }
    $value = Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($null -eq $value -or $value -isnot [pscustomobject]) { throw "settings.json debe ser un objeto JSON: $Path" }
    return $value
}
function Set-EvaProperty($Object, [string]$Name, $Value) {
    $Object | Add-Member -MemberType NoteProperty -Name $Name -Value $Value -Force
}
function Copy-EvaResource([string]$Source, [string]$Destination, [string]$BackupDirectory) {
    if (Test-Path -LiteralPath $Destination) {
        if ((Get-FileHash -LiteralPath $Source -Algorithm SHA256).Hash -eq (Get-FileHash -LiteralPath $Destination -Algorithm SHA256).Hash) { return }
        $backup = Join-Path $BackupDirectory ([guid]::NewGuid().ToString('N'))
        New-Item -ItemType Directory -Path $backup -Force | Out-Null
        Copy-Item -LiteralPath $Destination -Destination (Join-Path $backup 'original')
        Write-EvaJson (Join-Path $backup 'metadata.json') ([ordered]@{ destination = $Destination; saved_utc = [DateTime]::UtcNow.ToString('o') })
    }
    $temporary = $Destination + '.' + [guid]::NewGuid().ToString('N') + '.tmp'
    try {
        Copy-Item -LiteralPath $Source -Destination $temporary
        Move-Item -LiteralPath $temporary -Destination $Destination -Force
    } finally {
        if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Force }
    }
}
function Expand-EvaZip([string]$ArchivePath, [string]$Destination) {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [IO.Compression.ZipFile]::OpenRead($ArchivePath)
    try {
        $base = [IO.Path]::GetFullPath($Destination).TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
        $seen = @{}
        # Validate ALL entries before extracting any. Windows paths are case-insensitive.
        foreach ($entry in $archive.Entries) {
            $relative = $entry.FullName.Replace('\', '/')
            if ($relative.StartsWith('/') -or $relative -match '(^|/)\.\.(/|$)|:') { throw "Ruta ZIP no segura: $relative" }
            $target = [IO.Path]::GetFullPath((Join-Path $Destination $relative))
            if (!$target.StartsWith($base, [StringComparison]::OrdinalIgnoreCase)) { throw "Ruta ZIP fuera de destino: $relative" }
            if ($seen.ContainsKey($target)) { throw "Ruta ZIP duplicada: $relative" }
            $seen[$target] = $true
            # Unix symbolic links and Windows reparse points are never accepted.
            $attributes = [uint32]([int64]$entry.ExternalAttributes -band 0xffffffffL)
            if ((($attributes -shr 16) -band 0xf000) -eq 0xa000 -or ($attributes -band 0x400) -ne 0) { throw "Enlace ZIP no permitido: $relative" }
            if ($entry.Length -gt 1GB) { throw "Entrada ZIP demasiado grande: $relative" }
        }
        New-Item -ItemType Directory -Path $Destination -Force | Out-Null
        foreach ($entry in $archive.Entries) {
            $relative = $entry.FullName.Replace('\', '/')
            $target = Join-Path $Destination $relative
            if ($relative.EndsWith('/')) { New-Item -ItemType Directory -Path $target -Force | Out-Null; continue }
            New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($target)) -Force | Out-Null
            [IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $target, $false)
        }
    } finally { $archive.Dispose() }
}

if ($Root) {
    if (![IO.Path]::IsPathRooted($Root)) { throw '-Root debe ser una ruta absoluta a un perfil de pruebas.' }
    $profileRoot = [IO.Path]::GetFullPath($Root)
    $roaming = Join-Path $profileRoot 'AppData/Roaming'
    $local = Join-Path $profileRoot 'AppData/Local'
} else {
    if ($env:OS -ne 'Windows_NT') { throw 'Este instalador requiere Windows. Para pruebas aisladas utilice -Root.' }
    $roaming = [Environment]::GetFolderPath('ApplicationData')
    $local = [Environment]::GetFolderPath('LocalApplicationData')
    if (!$roaming -or !$local) { throw 'No se pudieron localizar las carpetas del perfil.' }
}
$config = Join-Path $roaming 'paolino/spotifast/config'
$appDirectory = Join-Path $local 'Programs/EVA-01 Audio'
$settingsPath = Join-Path $config 'settings.json'
$binary = Join-Path $appDirectory 'spotifast.exe'
$backups = Join-Path $appDirectory 'backups'
$appearanceBackup = Join-Path $backups 'appearance-before.json'
$shortcutPath = Join-Path $roaming 'Microsoft/Windows/Start Menu/Programs/EVA-01 Audio.lnk'
$icon = Join-Path $appDirectory 'eva-01-audio.ico'
$assets = Join-Path $PSScriptRoot 'assets'

if ($DryRun) {
    Write-Output "DRY RUN: tema $Theme; ajustes $settingsPath; ejecutable $binary; acceso $shortcutPath. Sin escrituras ni red."
    return
}
# A test root never changes the real user's configuration; process checks are unnecessary there.
if (!$Root -and @(Get-Process -Name spotifast -ErrorAction SilentlyContinue).Count -gt 0) {
    throw 'Cierre Spotifast antes de instalar EVA-01 Audio. El script no termina procesos.'
}
$settings = Read-EvaSettings $settingsPath
foreach ($name in @('EVA-01.json', 'EVA-01 Terminal.json', 'EVA-01.wsz', 'eva-01-audio.ico')) {
    if (!(Test-Path -LiteralPath (Join-Path $assets $name) -PathType Leaf)) { throw "Falta el recurso: $name" }
}
if ($SkipDownload -and !(Test-Path -LiteralPath $binary -PathType Leaf)) { throw "-SkipDownload requiere un ejecutable existente: $binary" }
$download = $null
if (!$SkipDownload) {
    $lock = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'release-lock.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($Architecture -eq 'Auto') {
        $cpu = $env:PROCESSOR_ARCHITEW6432
        if (!$cpu) { $cpu = $env:PROCESSOR_ARCHITECTURE }
        if ($cpu -eq 'ARM64') { $Architecture = 'aarch64' }
        elseif ($cpu -eq 'AMD64') { $Architecture = 'x86_64' }
        else { throw "Arquitectura Windows no compatible: $cpu. Se requieren x64 o ARM64." }
    }
    $download = $lock.downloads.PSObject.Properties['windows-' + $Architecture].Value
    if ($null -eq $download -or $download.sha256 -notmatch '^[0-9a-fA-F]{64}$' -or $download.url -notmatch '^https://github\.com/crmne/spotifast/releases/download/v[^/]+/[^/]+\.zip$') { throw 'release-lock.json no contiene un ZIP oficial con SHA256 valido.' }
}
foreach ($directory in @($appDirectory, $backups, (Join-Path $config 'themes'), (Join-Path $config 'skins'), ([IO.Path]::GetDirectoryName($shortcutPath)))) {
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
}
if ($download) {
    $staging = Join-Path $appDirectory ('.download-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $staging | Out-Null
    try {
        $archivePath = Join-Path $staging 'spotifast.zip'
        $previousTls = [Net.ServicePointManager]::SecurityProtocol
        try {
            [Net.ServicePointManager]::SecurityProtocol = $previousTls -bor [Net.SecurityProtocolType]::Tls12
            Invoke-WebRequest -Uri $download.url -OutFile $archivePath -UseBasicParsing
        } finally { [Net.ServicePointManager]::SecurityProtocol = $previousTls }
        if ((Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash -ne $download.sha256) { throw 'SHA256 incorrecto. No se instala el archivo descargado.' }
        $extracted = Join-Path $staging 'extracted'
        Expand-EvaZip $archivePath $extracted
        $candidates = @(Get-ChildItem -LiteralPath $extracted -Filter spotifast.exe -File -Recurse)
        if ($candidates.Count -ne 1) { throw 'El ZIP oficial debe contener exactamente un spotifast.exe.' }
        Copy-EvaResource $candidates[0].FullName $binary $backups
    } finally { if (Test-Path -LiteralPath $staging) { Remove-Item -LiteralPath $staging -Recurse -Force } }
}
foreach ($name in @('EVA-01.json', 'EVA-01 Terminal.json')) {
    Copy-EvaResource (Join-Path $assets $name) (Join-Path $config ('themes/' + $name)) $backups
}
Copy-EvaResource (Join-Path $assets 'EVA-01.wsz') (Join-Path $config 'skins/EVA-01.wsz') $backups
Copy-EvaResource (Join-Path $assets 'eva-01-audio.ico') $icon $backups
$changes = [ordered]@{
    theme = 'dark'; custom_theme = ($Theme + '.json'); custom_theme_cache = $null
    language = 'es'; skin = 'EVA-01.wsz'; skin_scale = 3; random_skin = $false
    accent_from_art = $false; custom_titlebar = $true; player_bar_vis = 'waveform'
    device_name = 'EVA-01 Audio'; winamp_window = $false
}
if (!(Test-Path -LiteralPath $appearanceBackup)) {
    $before = [ordered]@{}
    foreach ($name in $changes.Keys) {
        $property = $settings.PSObject.Properties[$name]
        $before[$name] = [ordered]@{ present = ($null -ne $property); value = $(if ($null -ne $property) { $property.Value } else { $null }) }
    }
    Write-EvaJson $appearanceBackup ([ordered]@{ schema_version = 1; keys = $before })
}
foreach ($name in $changes.Keys) { Set-EvaProperty $settings $name $changes[$name] }
Write-EvaJson $settingsPath $settings
# Preserve a pre-existing homonymous shortcut once before first installation.
$shortcutBackup = Join-Path $backups 'shortcut-before.lnk'
$shortcutMarker = Join-Path $backups 'shortcut-managed.json'
if (!(Test-Path -LiteralPath $shortcutMarker)) {
    if (Test-Path -LiteralPath $shortcutPath) { Copy-Item -LiteralPath $shortcutPath -Destination $shortcutBackup }
    Write-EvaJson $shortcutMarker ([ordered]@{ destination = $shortcutPath; original_present = (Test-Path -LiteralPath $shortcutBackup) })
}
$shell = New-Object -ComObject WScript.Shell
try {
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $binary
    $shortcut.WorkingDirectory = $appDirectory
    $shortcut.IconLocation = $icon + ',0'
    $shortcut.Description = 'EVA-01 Audio - Spotifast'
    $shortcut.Save()
} finally {
    if ([Runtime.InteropServices.Marshal]::IsComObject($shell)) { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($shell) }
}
Write-Output "EVA-01 Audio instalado. Abra el acceso del menu Inicio. Copias: $backups"

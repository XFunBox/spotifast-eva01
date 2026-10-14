#requires -Version 5.1
<#
Restaura solo los campos de apariencia, idioma y dispositivo Connect modificados por install-windows.ps1.
Conserva el ejecutable, temas, skin, icono, acceso y backups de recursos.
-Root usa el mismo perfil aislado de pruebas que el instalador.
#>
[CmdletBinding()]
param([switch]$DryRun, [string]$Root)
Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
if ($Root) {
    if (![IO.Path]::IsPathRooted($Root)) { throw '-Root debe ser una ruta absoluta a un perfil de pruebas.' }
    $profileRoot = [IO.Path]::GetFullPath($Root)
    $roaming = Join-Path $profileRoot 'AppData/Roaming'
    $local = Join-Path $profileRoot 'AppData/Local'
} else {
    if ($env:OS -ne 'Windows_NT') { throw 'Este restaurador requiere Windows. Para pruebas aisladas utilice -Root.' }
    $roaming = [Environment]::GetFolderPath('ApplicationData')
    $local = [Environment]::GetFolderPath('LocalApplicationData')
    if (!$roaming -or !$local) { throw 'No se pudieron localizar las carpetas del perfil.' }
}
$settingsPath = Join-Path $roaming 'paolino/spotifast/config/settings.json'
$backups = Join-Path $local 'Programs/EVA-01 Audio/backups'
$backupPath = Join-Path $backups 'appearance-before.json'
if ($DryRun) { Write-Output "DRY RUN: restaurar apariencia en $settingsPath. Sin escrituras ni red."; return }
if (!$Root -and @(Get-Process -Name spotifast -ErrorAction SilentlyContinue).Count -gt 0) {
    throw 'Cierre Spotifast antes de restaurar. El script no termina procesos.'
}
if (!(Test-Path -LiteralPath $backupPath)) { Write-Output 'No hay una apariencia pendiente de restaurar.'; return }
$backup = Get-Content -LiteralPath $backupPath -Raw -Encoding UTF8 | ConvertFrom-Json
$allowed = @('theme', 'custom_theme', 'custom_theme_cache', 'language', 'skin', 'skin_scale', 'random_skin', 'accent_from_art', 'custom_titlebar', 'player_bar_vis', 'device_name', 'winamp_window')
if ($backup.schema_version -ne 1 -or $backup.keys -isnot [pscustomobject]) { throw 'Formato de backup no compatible.' }
foreach ($property in $backup.keys.PSObject.Properties) {
    if ($allowed -notcontains $property.Name -or $property.Value.present -isnot [bool]) { throw 'El backup contiene un campo no permitido o invalido.' }
}
if (Test-Path -LiteralPath $settingsPath) {
    $settings = Get-Content -LiteralPath $settingsPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($null -eq $settings -or $settings -isnot [pscustomobject]) { throw 'settings.json debe ser un objeto JSON.' }
} else {
    $settings = [pscustomobject]@{}
    New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($settingsPath)) -Force | Out-Null
}
# Save only the current affected fields, never unrelated settings or credentials.
$current = [ordered]@{}
foreach ($property in $backup.keys.PSObject.Properties) {
    $existing = $settings.PSObject.Properties[$property.Name]
    $current[$property.Name] = [ordered]@{ present = ($null -ne $existing); value = $(if ($null -ne $existing) { $existing.Value } else { $null }) }
    if ($property.Value.present) {
        $settings | Add-Member -MemberType NoteProperty -Name $property.Name -Value $property.Value.value -Force
    } else { $settings.PSObject.Properties.Remove($property.Name) }
}
$encoding = New-Object Text.UTF8Encoding($false)
$timestamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfff') + '-' + [guid]::NewGuid().ToString('N')
$currentPath = Join-Path $backups ('appearance-before-restore-' + $timestamp + '.json')
[IO.File]::WriteAllText($currentPath, (ConvertTo-Json -InputObject ([ordered]@{ schema_version = 1; keys = $current }) -Depth 100), $encoding)
$temporary = $settingsPath + '.' + [guid]::NewGuid().ToString('N') + '.tmp'
try {
    [IO.File]::WriteAllText($temporary, (ConvertTo-Json -InputObject $settings -Depth 100) + [Environment]::NewLine, $encoding)
    Move-Item -LiteralPath $temporary -Destination $settingsPath -Force
} finally { if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Force } }
Move-Item -LiteralPath $backupPath -Destination (Join-Path $backups ('appearance-restored-' + $timestamp + '.json'))
Write-Output "Apariencia restaurada. Los recursos y el acceso EVA-01 siguen disponibles. Copias: $backups"

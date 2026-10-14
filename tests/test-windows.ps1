#requires -Version 5.1
# Sin Pester ni red. Perfil temporal; en Windows se prueba el COM real.
[CmdletBinding()]
param()
Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
$package = Split-Path -Parent $PSScriptRoot
$installer = Join-Path $package 'eva/install-windows.ps1'
$restorer = Join-Path $package 'eva/restore-windows.ps1'
$fixture = Join-Path ([IO.Path]::GetTempPath()) ('eva-windows-tests-' + [guid]::NewGuid().ToString('N'))
$checks = 0
function Assert-Eva($Condition, [string]$Message) {
    if (!$Condition) { throw "FALLO: $Message" }
    $script:checks++
}
function Write-TestJson([string]$Path, $Object) {
    New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($Path)) -Force | Out-Null
    [IO.File]::WriteAllText($Path, (ConvertTo-Json -InputObject $Object -Depth 100), (New-Object Text.UTF8Encoding($false)))
}
function Read-TestJson([string]$Path) { Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json }
function Assert-Throws([scriptblock]$Action, [string]$Pattern) {
    $failed = $false
    try { & $Action | Out-Null } catch { $failed = $_.Exception.Message -match $Pattern }
    Assert-Eva $failed "Se esperaba error: $Pattern"
}
# Linux PowerShell permite comprobar la logica, pero no ofrece WScript.Shell.
if ($env:OS -ne 'Windows_NT') {
    function New-Object {
        param([string]$TypeName, [object[]]$ArgumentList, [string]$ComObject)
        if ($ComObject) {
            if ($ComObject -ne 'WScript.Shell') { throw 'COM no previsto en prueba.' }
            $shell = [pscustomobject]@{}
            $shell | Add-Member ScriptMethod CreateShortcut {
                param($Path)
                $link = [pscustomobject]@{ Path = $Path; TargetPath = ''; WorkingDirectory = ''; IconLocation = ''; Description = '' }
                $link | Add-Member ScriptMethod Save { [IO.File]::WriteAllText($this.Path, $this.TargetPath + "`n" + $this.IconLocation) }
                return $link
            }
            return $shell
        }
        Microsoft.PowerShell.Utility\New-Object @PSBoundParameters
    }
}
try {
    $dryProfile = Join-Path $fixture 'dry-profile'
    & $installer -Root $dryProfile -DryRun
    & $restorer -Root $dryProfile -DryRun
    Assert-Eva (!(Test-Path -LiteralPath $fixture)) 'DryRun no debe crear rutas.'
    Assert-Throws { & $installer -Root $dryProfile -SkipDownload } 'ejecutable existente'
    Assert-Eva (!(Test-Path -LiteralPath $fixture)) 'SkipDownload ausente falla antes de escribir.'

    $profile = Join-Path $fixture 'profile with spaces'
    $app = Join-Path $profile 'AppData/Local/Programs/EVA-01 Audio'
    $config = Join-Path $profile 'AppData/Roaming/paolino/spotifast/config'
    $settingsPath = Join-Path $config 'settings.json'
    $binary = Join-Path $app 'spotifast.exe'
    $backup = Join-Path $app 'backups/appearance-before.json'
    New-Item -ItemType Directory -Path $app -Force | Out-Null
    [IO.File]::WriteAllText($binary, 'NOT AN EXECUTABLE: isolated fixture')
    Write-TestJson $settingsPath ([ordered]@{ theme = 'light'; custom_theme = $null; language = 'fr'; skin_scale = 2; volume = 0.42; unrelated = @{ items = @('alpha', 'beta'); flag = $true }; eq_bands_db = @(1, 2, 3) })
    $binaryHash = (Get-FileHash -LiteralPath $binary).Hash
    $oldTheme = Join-Path $config 'themes/EVA-01.json'
    New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($oldTheme)) -Force | Out-Null
    [IO.File]::WriteAllText($oldTheme, 'existing homonymous theme')
    & $installer -Root $profile -SkipDownload
    $installed = Read-TestJson $settingsPath
    Assert-Eva ($installed.theme -eq 'dark' -and $installed.custom_theme -eq 'EVA-01.json' -and $installed.language -eq 'es') 'Tema e idioma seleccionados.'
    Assert-Eva ($installed.skin -eq 'EVA-01.wsz' -and $installed.skin_scale -eq 3 -and !$installed.random_skin) 'Skin seleccionada.'
    Assert-Eva (!$installed.accent_from_art -and $installed.custom_titlebar -and $installed.player_bar_vis -eq 'waveform' -and $installed.device_name -eq 'EVA-01 Audio' -and !$installed.winamp_window) 'Apariencia aplicada.'
    Assert-Eva ($installed.volume -eq 0.42 -and $installed.unrelated.items.Count -eq 2 -and $installed.unrelated.flag -and $installed.eq_bands_db[2] -eq 3) 'Ajustes ajenos conservados.'
    Assert-Eva ((Get-FileHash -LiteralPath $binary).Hash -eq $binaryHash) 'SkipDownload conserva binario.'
    $originalBackup = Read-TestJson $backup
    Assert-Eva ($null -eq $originalBackup.keys.PSObject.Properties['volume'] -and !$originalBackup.keys.skin.present -and $originalBackup.keys.custom_theme.present -and $null -eq $originalBackup.keys.custom_theme.value) 'Backup solo campos modificados, ausencia y null diferenciados.'
    $resourceBackups = @(Get-ChildItem -LiteralPath (Join-Path $app 'backups') -Filter metadata.json -File -Recurse)
    Assert-Eva ($resourceBackups.Count -eq 1) 'Recurso homonimo respaldado.'
    Assert-Eva ((Get-Content -LiteralPath (Join-Path $resourceBackups[0].Directory.FullName 'original') -Raw) -eq 'existing homonymous theme') 'Contenido original conservado.'
    $shortcutPath = Join-Path $profile 'AppData/Roaming/Microsoft/Windows/Start Menu/Programs/EVA-01 Audio.lnk'
    Assert-Eva (Test-Path -LiteralPath $shortcutPath) 'Acceso creado.'
    if ($env:OS -eq 'Windows_NT') {
        $link = (New-Object -ComObject WScript.Shell).CreateShortcut($shortcutPath)
        Assert-Eva ($link.TargetPath -eq $binary -and $link.IconLocation -match 'eva-01-audio.ico') 'Acceso real apunta al binario e icono.'
    }
    $backupHash = (Get-FileHash -LiteralPath $backup).Hash
    $settingsHash = (Get-FileHash -LiteralPath $settingsPath).Hash
    & $installer -Root $profile -SkipDownload
    Assert-Eva ((Get-FileHash -LiteralPath $backup).Hash -eq $backupHash) 'Reinstalacion conserva baseline.'
    Assert-Eva ((Get-FileHash -LiteralPath $settingsPath).Hash -eq $settingsHash) 'Reinstalacion idempotente.'
    Assert-Eva (@(Get-ChildItem -LiteralPath (Join-Path $app 'backups') -Filter metadata.json -File -Recurse).Count -eq 1) 'Reinstalacion no duplica recursos identicos.'
    & $installer -Root $profile -SkipDownload -Theme 'EVA-01 Terminal'
    Assert-Eva ((Read-TestJson $settingsPath).custom_theme -eq 'EVA-01 Terminal.json') 'Variante Terminal seleccionada.'
    Assert-Eva ((Get-FileHash -LiteralPath $backup).Hash -eq $backupHash) 'Cambio de tema conserva baseline.'
    $installed = Read-TestJson $settingsPath
    $installed.volume = 0.7
    Write-TestJson $settingsPath $installed
    & $restorer -Root $profile
    $restored = Read-TestJson $settingsPath
    Assert-Eva ($restored.theme -eq 'light' -and $restored.language -eq 'fr' -and $restored.skin_scale -eq 2 -and $null -eq $restored.custom_theme) 'Valores originales restaurados.'
    Assert-Eva ($null -eq $restored.PSObject.Properties['skin'] -and $null -eq $restored.PSObject.Properties['custom_theme_cache'] -and $null -eq $restored.PSObject.Properties['winamp_window']) 'Campos originalmente ausentes eliminados.'
    Assert-Eva ($restored.volume -eq 0.7 -and $restored.unrelated.flag -and $restored.eq_bands_db[2] -eq 3) 'Restaurar preserva cambios ajenos posteriores.'
    Assert-Eva (!(Test-Path -LiteralPath $backup)) 'Baseline archivado tras restaurar.'
    Assert-Eva ((Test-Path -LiteralPath $binary) -and (Test-Path -LiteralPath $shortcutPath) -and (Test-Path -LiteralPath $oldTheme)) 'Restaurar conserva recursos y acceso.'
    $restoredHash = (Get-FileHash -LiteralPath $settingsPath).Hash
    & $restorer -Root $profile
    Assert-Eva ((Get-FileHash -LiteralPath $settingsPath).Hash -eq $restoredHash) 'Segunda restauracion no escribe settings.'
    & $installer -Root $profile -SkipDownload
    Assert-Eva ((Read-TestJson $backup).keys.theme.value -eq 'light') 'Nueva instalacion crea baseline nuevo.'

    # Un JSON corrupto nunca se sustituye por valores por defecto.
    $corrupt = Join-Path $fixture 'corrupt'
    $corruptSettings = Join-Path $corrupt 'AppData/Roaming/paolino/spotifast/config/settings.json'
    New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($corruptSettings)) -Force | Out-Null
    [IO.File]::WriteAllText($corruptSettings, '{invalid')
    $corruptHash = (Get-FileHash -LiteralPath $corruptSettings).Hash
    Assert-Throws { & $installer -Root $corrupt -SkipDownload } '.'
    Assert-Eva ((Get-FileHash -LiteralPath $corruptSettings).Hash -eq $corruptHash) 'JSON corrupto conservado.'

    # Las funciones quedan en el ambito de prueba al dot-source con DryRun.
    . $installer -Root $profile -DryRun
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $unsafeZip = Join-Path $fixture 'unsafe.zip'
    $zip = [IO.Compression.ZipFile]::Open($unsafeZip, [IO.Compression.ZipArchiveMode]::Create)
    try { [void]$zip.CreateEntry('../escape.exe') } finally { $zip.Dispose() }
    $extraction = Join-Path $fixture 'extraction'
    Assert-Throws { Expand-EvaZip $unsafeZip $extraction } 'no segura'
    Assert-Eva (!(Test-Path -LiteralPath $extraction) -and !(Test-Path -LiteralPath (Join-Path $fixture 'escape.exe'))) 'ZIP traversal rechazado antes de extraer.'
    $safeZip = Join-Path $fixture 'safe.zip'
    $zip = [IO.Compression.ZipFile]::Open($safeZip, [IO.Compression.ZipArchiveMode]::Create)
    try {
        $entry = $zip.CreateEntry('bin/spotifast.exe')
        $writer = [IO.StreamWriter]::new($entry.Open())
        try { $writer.Write('fixture binary') } finally { $writer.Dispose() }
    } finally { $zip.Dispose() }
    Expand-EvaZip $safeZip $extraction
    Assert-Eva ((Get-Content -LiteralPath (Join-Path $extraction 'bin/spotifast.exe') -Raw) -eq 'fixture binary') 'ZIP normal extraido.'
    # Mock de descarga: hash incorrecto no puede sustituir el ejecutable.
    function Invoke-WebRequest { param($Uri, $OutFile, [switch]$UseBasicParsing); [IO.File]::WriteAllText($OutFile, 'wrong hash fixture') }
    Assert-Throws { & $installer -Root $profile -Architecture x86_64 } 'SHA256 incorrecto'
    Assert-Eva ((Get-FileHash -LiteralPath $binary).Hash -eq $binaryHash) 'Hash incorrecto conserva binario.'
    Assert-Eva (@(Get-ChildItem -LiteralPath $app -Directory -Filter '.download-*').Count -eq 0) 'Temporales de descarga limpiados.'
    Write-Output "$checks comprobaciones correctas. Binario simulado; sin red ni reproduccion."
} finally {
    if (Test-Path -LiteralPath $fixture) { Remove-Item -LiteralPath $fixture -Recurse -Force }
}

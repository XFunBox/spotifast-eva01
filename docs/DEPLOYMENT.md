# Despliegue y restauración

## Versiones fijadas

El manifiesto `eva/release-lock.json` fija Spotifast 0.13.0, commit de fuente, URLs y SHA-256 para Linux x86_64/ARM64 y Windows x86_64/ARM64. Para actualizar, revisar una release oficial nueva, compatibilidad de configuración y sprites; cambiar versión, hashes y snapshot `upstream/` juntos y ejecutar la CI. Los instaladores no eligen `latest` automáticamente.

## Linux

`bash install-linux.sh` descarga el AppImage oficial. Una copia con el SHA-256 esperado se reutiliza. Crea:

- `~/.local/opt/eva-01-audio/Spotifast.AppImage`.
- `~/.local/bin/eva-01-audio`.
- `$XDG_CONFIG_HOME/spotifast/themes/` y `skins/`, usando `~/.config` como alternativa.
- Acceso en `$XDG_DATA_HOME/applications/`, usando `~/.local/share` como alternativa.
- Copia visual en `$XDG_DATA_HOME/eva-01-audio/apariencia-anterior.json`.

El AppImage oficial necesita las bibliotecas del sistema indicadas en `upstream/native-packages.yaml`; la lista Ubuntu está en el README. El instalador no ejecuta apt ni cambia paquetes del sistema.

La instalación requiere que Spotifast esté cerrado. Detecta el ejecutable nativo incluso cuando el AppImage muestra el nombre `AppRun`. No mata procesos automáticamente.

Si el runtime AppImage falla por ausencia de FUSE2:

```bash
APPIMAGE_EXTRACT_AND_RUN=1 ~/.local/opt/eva-01-audio/Spotifast.AppImage
```

En Ubuntu 24.04 también puede instalarse `libfuse2t64` con el gestor de paquetes. No instalar el antiguo paquete `fuse` para resolverlo. En distribuciones anteriores a la base glibc 2.39 del binario, usar una distribución compatible o compilar la fuente siguiendo las instrucciones originales.

`--root /ruta/perfil-temporal` crea un perfil de pruebas aislado, ignora XDG y no comprueba procesos del perfil real. `--skip-download` conserva el binario existente sin verificarlo; es una opción de pruebas o para una copia que ya hayas comprobado. No se usa en el despliegue normal.

## Windows

El instalador usa Windows PowerShell 5.1, ZIP oficial y `Get-FileHash -Algorithm SHA256`. Instala el binario en `%LOCALAPPDATA%\Programs\EVA-01 Audio\spotifast.exe`, el icono en su carpeta de datos y un `.lnk` en el menú Inicio del usuario. La configuración de Spotifast está en `%APPDATA%\paolino\spotifast\config`.

El ZIP contiene la distribución oficial portátil. No ejecuta MSI ni instala asociaciones de enlaces Spotify. La cuenta se configura dentro del reproductor después de instalar.

`-Root C:\ruta\perfil-temporal` sirve para pruebas aisladas. `-SkipDownload` exige que el ejecutable ya exista. `-DryRun` muestra el plan sin descargas ni escrituras.

## Restaurar

Cerrar Spotifast y ejecutar `bash install-linux.sh --restore` o `eva\restore-windows.ps1`. Se restauran los campos cambiados a sus valores originales; los demás ajustes posteriores se conservan. La primera copia no se sustituye al reinstalar o cambiar de tema.

La restauración no desinstala el reproductor, los temas, los iconos ni los accesos. Los recursos anteriores quedan conservados en una carpeta de copias junto a los datos de EVA-01 Audio. Restaurar esos archivos manualmente solo si se desea retirar los recursos del paquete.

## Publicación

El código fuente completo está en GitHub y la release distribuye un ZIP con instaladores, temas, licencia y documentación. Los binarios nativos se obtienen del repositorio oficial durante la instalación; no se duplican binarios grandes en Git.

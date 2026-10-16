# EVA-01 Audio · Spotifast

Spotifast 0.13.3 con temas Evangelion, skin NERV e instaladores para Linux y Windows. Incluye el código original en `upstream/`, sin modificaciones al motor de audio, y conserva su licencia MIT y autoría.

![Vista previa de la skin compacta](eva/assets/EVA-01-preview.png)

## Instalar en Linux

Cierra Spotifast antes de instalar. Necesitas Python 3.9 o posterior, conexión a Internet y Linux x86_64 o ARM64 compatible con el AppImage oficial. La base del binario es glibc 2.39 (Ubuntu 24.04 o posterior). No necesita compilar Rust ni instalar como administrador.

En Ubuntu 24.04, si faltan las bibliotecas de escritorio/audio:

```bash
sudo apt install python3 libdbus-1-3 libx11-xcb1 libpulse0 libasound2t64 libfuse2t64 libxkbcommon0 libxkbcommon-x11-0 libwayland-client0 libwayland-cursor0 libwayland-egl1 libgl1 libegl1 libx11-6 libxcursor1 libxi6 libxrandr2
```

```bash
git clone https://github.com/XFunBox/spotifast-eva01.git
cd spotifast-eva01
bash install-linux.sh
```

Abre **EVA-01 Audio** desde el menú. Instala en tu directorio personal, respeta `XDG_CONFIG_HOME` y `XDG_DATA_HOME`, y crea un acceso de escritorio. Si falta `libfuse.so.2`, en Ubuntu 24.04 instala `libfuse2t64`, o inicia el AppImage con el método de extracción descrito en [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

```bash
bash install-linux.sh --dry-run
bash install-linux.sh --theme 'EVA-01 Terminal'
bash install-linux.sh --restore
```

## Instalar en Windows

Windows 10/11 de 64 bits o ARM64. No necesitas Python ni permisos de administrador. Descarga y descomprime el repositorio o clónalo con Git. Cierra Spotifast, abre PowerShell en la carpeta y ejecuta:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\eva\install-windows.ps1
```

El acceso **EVA-01 Audio** aparece en el menú Inicio. La opción de ejecución se aplica a ese proceso; no cambia la política del sistema.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\eva\install-windows.ps1 -DryRun
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\eva\install-windows.ps1 -Theme 'EVA-01 Terminal'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\eva\restore-windows.ps1
```

El repositorio es público. Puedes clonar el código o descargar el ZIP de [EVA-01 Audio v1.1.0](https://github.com/XFunBox/spotifast-eva01/releases/tag/v1.1.0), que incluye Spotifast 0.13.3 y NERV Nightshift. La entrega incluye `SHA256SUMS.txt` para verificar el paquete; los instaladores obtienen el reproductor oficial y comprueban su SHA-256.

## Temas y controles

**NERV Nightshift** es la segunda interfaz opcional para Linux: ventana sencilla,
verde neón, carátula y controles para trabajar. Instalación y atajos en
[docs/nightshift.md](docs/nightshift.md).

- **EVA-01**: negro, morado y verde vivo.
- **EVA-01 Terminal**: negro verdoso y verde vivo.
- **EVA-01.wsz**: skin clásica completa, 15 hojas de sprites, títulos de consola NERV y ecualizador AT FIELD.

**Ctrl + M** alterna biblioteca y minirreproductor. **EQ** abre el ecualizador, **PL** la cola, y el menú contextual del título ajusta el tamaño. Si todavía no has conectado la cuenta, inicia sesión desde la ventana principal. La reproducción local depende de Spotify Premium y de las capacidades de Spotifast.

Los instaladores fusionan las preferencias de aspecto y cambian el nombre visible en Spotify Connect a «EVA-01 Audio». No incluyen cuentas, credenciales, listas privadas ni el contenido del equipo que creó este repositorio. Guardan los ajustes visuales anteriores y una copia de cualquier recurso homónimo que sustituyan. La restauración recupera las preferencias y conserva los recursos instalados para poder reutilizarlos.

La skin y paleta principal se pueden regenerar con `python3 eva/build_theme.py` (necesita Pillow). Los instaladores solo necesitan los recursos ya incluidos.

## Código, versión y validación

El código de `upstream/` corresponde a `crmne/spotifast`, tag **v0.13.3**, commit `a4c1b3ef6c9667507f198312453766f6ba953710`. Para compilarlo, sigue [upstream/README.md](upstream/README.md) y [upstream/CONTRIBUTING.md](upstream/CONTRIBUTING.md), desde esa carpeta. Los instaladores usan los binarios oficiales; no recompilan el programa.

[Documentación de despliegue](docs/DEPLOYMENT.md) · [Validación](docs/VERIFICATION.md) · [Licencia](LICENSE) · [Procedencia](NOTICE.md).

La integración continua comprueba Linux y Windows, preservación/restauración de ajustes y descarga/arranque del binario fijado. Las pruebas de instalación no inician sesión ni reproducen música. La imagen superior es una composición de la skin en reposo.

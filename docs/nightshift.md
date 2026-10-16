# NERV Nightshift (Linux)

Ventana nativa opcional para trabajar: carátula, canción y controles en una sola vista,
con fondo carbón y verde neón `#9DFF00`. Usa el cliente Spotifast 0.13.3 instalado,
sin otra cuenta, motor de audio ni acceso a credenciales.

Requiere Python 3 y PyQt6 con QtSvg y QtNetwork. En Ubuntu, si faltan:
`sudo apt install python3-pyqt6 python3-pyqt6.qtsvg`.

Desde este repositorio, después de instalar EVA-01 Audio:

```sh
python3 eva/install_nightshift.py
```

Después de actualizar EVA-01 Audio, ejecutar de nuevo ese comando con Nightshift
y Spotifast cerrados para renovar también su copia del motor.

Abrir **NERV Nightshift** desde el menú KDE o `nerv-nightshift`.
Si Spotifast está cerrado, **Abrir biblioteca** inicia el cliente.
Cerrar Nightshift deja Spotifast y la música funcionando.

- Reproducción, anterior/siguiente, aleatorio, repetición, favorito, posición y volumen
  usan la interfaz local del cliente. El estado se consulta cada 1,5 segundos.
- Buscar y pulsar Intro abre resultados en la ventana de Spotifast, sin reproducir
  automáticamente. **Abrir biblioteca** muestra esa ventana, donde están biblioteca,
  favoritos y cola. Esas listas no se duplican: la API local no las expone.
- Las carátulas se descargan por HTTPS únicamente de subdominios `scdn.co` de Spotify,
  sin credenciales; no se guardan. La interfaz no descarga audio.
- El instalador extrae una copia del AppImage existente una sola vez en
  `~/.local/opt/nerv-nightshift/runtime`. Esto evita depender de FUSE y extraerlo
  en cada consulta. No cambia la instalación ni las preferencias de EVA-01 Audio.

Atajos dentro de la ventana (teclado 60 %): **Ctrl+P** reproducir/pausar,
**Alt+J / Alt+L** anterior/siguiente, **Ctrl+G** favorito, **Ctrl+K** buscar,
**Ctrl+B** biblioteca y **Ctrl+Q** cerrar. Los sliders admiten teclado.

Vista sin cuenta ni reproducción: `python3 eva/nightshift.py --demo`.
Captura: `QT_QPA_PLATFORM=offscreen python3 eva/nightshift.py --screenshot /ruta/preview.png`.

Para retirar solo esta interfaz, eliminar `~/.local/opt/nerv-nightshift`,
`~/.local/bin/nerv-nightshift` y `~/.local/share/applications/nerv-nightshift.desktop`.
Linux probado; no se ofrece instalador Nightshift para Windows.

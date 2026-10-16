#!/usr/bin/env python3
"""Install the optional Nightshift window using the existing Spotifast AppImage."""
import argparse
import importlib.util
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent


def install(home, appimage):
    if importlib.util.find_spec('PyQt6.QtWidgets') is None:
        raise SystemExit('Falta PyQt6. En Ubuntu: sudo apt install python3-pyqt6 python3-pyqt6.qtsvg')
    if not appimage.is_file():
        raise SystemExit('No se encontró Spotifast. Instala primero EVA-01 Audio o usa --appimage RUTA.')
    target = home / '.local/opt/nerv-nightshift'
    target.mkdir(parents=True, exist_ok=True)
    runtime = target / 'runtime'
    # Extract once: no FUSE required and no AppImage extraction on every status poll.
    with tempfile.TemporaryDirectory(prefix='extract-', dir=target) as staging:
        subprocess.run([str(appimage.resolve()), '--appimage-extract'], cwd=staging,
                       stdout=subprocess.DEVNULL, check=True)
        extracted = Path(staging) / 'squashfs-root'
        subprocess.run([str(extracted / 'AppRun'), '--version'], check=True,
                       stdout=subprocess.DEVNULL)
        if runtime.exists():
            shutil.rmtree(runtime)
        extracted.rename(runtime)
    shutil.copy2(HERE / 'nightshift.py', target / 'nightshift.py')
    icon = target / 'nightshift.svg'
    icon.write_text('''<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">
<rect width="128" height="128" rx="26" fill="#16171c"/>
<path d="M32 96V32h12l40 44V32h12v64H84L44 52v44z" fill="#9dff00"/>
<path d="M32 110h64" stroke="#9966cc" stroke-width="4"/></svg>''')
    launcher = home / '.local/bin/nerv-nightshift'
    launcher.parent.mkdir(parents=True, exist_ok=True)
    launcher.write_text('#!/bin/sh\nexec /usr/bin/python3 ' + shlex.quote(str(target / 'nightshift.py'))
                        + ' --spotifast ' + shlex.quote(str(runtime / 'AppRun')) + ' "$@"\n')
    launcher.chmod(0o755)
    applications = Path(os.environ.get('XDG_DATA_HOME', str(home / '.local/share'))) / 'applications'
    applications.mkdir(parents=True, exist_ok=True)
    desktop = applications / 'nerv-nightshift.desktop'
    # Desktop Exec quoting is distinct from shell quoting.
    command = str(launcher).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%')
    desktop.write_text('[Desktop Entry]\nType=Application\nName=NERV Nightshift\n'
                       'Comment=Interfaz de trabajo para Spotifast\n'
                       f'Exec="{command}"\nIcon={icon}\nTerminal=false\nCategories=AudioVideo;Audio;Player;\n'
                       'StartupWMClass=nightshift.py\n')
    print(f'Instalado: {launcher}\nAcceso KDE: {desktop}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--appimage', type=Path,
                        default=Path.home() / '.local/opt/eva-01-audio/Spotifast.AppImage')
    args = parser.parse_args()
    install(Path.home(), args.appimage)

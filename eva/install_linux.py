#!/usr/bin/env python3
"""Install the pinned official Spotifast and the EVA-01 theme pack, per user."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import tempfile
import urllib.request

HERE = Path(__file__).resolve().parent
ASSETS = HERE / 'assets'
THEMES = ('EVA-01', 'EVA-01 Terminal')


def read_json(path):
    value = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    if not isinstance(value, dict):
        raise ValueError(f'Expected JSON object in {path.name}')
    return value


def atomic_write(path, content, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_json(path, value):
    atomic_write(path, (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode())


def layout(root=None):
    home = Path(root).resolve() if root else Path.home()
    def xdg(name, default):
        value = os.environ.get(name) if root is None else None
        return Path(value) if value and Path(value).is_absolute() else home / default
    return {
        'home': home,
        'config': xdg('XDG_CONFIG_HOME', '.config') / 'spotifast',
        'data': xdg('XDG_DATA_HOME', '.local/share') / 'eva-01-audio',
        'applications': xdg('XDG_DATA_HOME', '.local/share') / 'applications',
        'binary': home / '.local/opt/eva-01-audio/Spotifast.AppImage',
        'launcher': home / '.local/bin/eva-01-audio',
    }


def running():
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        try:
            if (proc / 'exe').resolve().name == 'spotifast':
                return True
        except (OSError, RuntimeError):
            pass
    return False


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def preserve(path, data):
    if path.exists():
        backup = data / 'recursos-anteriores' / (path.name + '.' + digest(path)[:12] + '.bak')
        if not backup.exists():
            atomic_write(backup, path.read_bytes())


def copy_asset(source, target, data):
    content = source.read_bytes()
    if target.exists() and target.read_bytes() == content:
        return
    preserve(target, data)
    atomic_write(target, content, 0o644)


def download(entry, target):
    request = urllib.request.Request(entry['url'], headers={'User-Agent': 'EVA-01-Audio/1.0'})
    h = hashlib.sha256()
    with urllib.request.urlopen(request, timeout=90) as response, target.open('wb') as stream:
        while True:
            block = response.read(1024 * 1024)
            if not block:
                break
            h.update(block)
            stream.write(block)
    if h.hexdigest() != entry['sha256']:
        raise ValueError('SHA-256 del binario incorrecto; no se ha instalado.')


def install(root=None, theme='EVA-01', skip_download=False, dry_run=False):
    if platform.system() != 'Linux':
        raise ValueError('Usa install-windows.ps1 en Windows.')
    if theme not in THEMES:
        raise ValueError('Tema desconocido.')
    paths = layout(root)
    config, data, binary = (paths[k] for k in ('config', 'data', 'binary'))
    if root is None and running():
        raise ValueError('Cierra Spotifast antes de instalar; no se cierra automáticamente.')
    machine = platform.machine().lower()
    arch = {'x86_64': 'x86_64', 'amd64': 'x86_64', 'aarch64': 'aarch64', 'arm64': 'aarch64'}.get(machine)
    if not arch:
        raise ValueError(f'Arquitectura no soportada: {machine}')
    entry = read_json(HERE / 'release-lock.json')['downloads']['linux-' + arch]
    updates = {'theme': 'dark', 'custom_theme': theme + '.json', 'accent_from_art': False,
               'custom_titlebar': True, 'language': 'es', 'skin': 'EVA-01.wsz',
               'random_skin': False, 'skin_scale': 3, 'winamp_window': False,
               'player_bar_vis': 'waveform', 'device_name': 'EVA-01 Audio'}
    settings = config / 'settings.json'
    current = read_json(settings)
    # Validate all input before any download or change to the profile.
    for filename in (*[t + '.json' for t in THEMES], 'EVA-01.wsz', 'eva-01-audio.svg'):
        if not (ASSETS / filename).is_file():
            raise ValueError(f'Falta recurso: {filename}')
    if dry_run:
        print(f'Simulación: Spotifast 0.13.0, {arch}, tema {theme}, perfil {paths["home"]}')
        return
    if skip_download and not binary.is_file():
        raise ValueError('--skip-download necesita un AppImage ya instalado en la ruta de destino.')
    with tempfile.TemporaryDirectory(prefix='eva-download-') as temporary:
        candidate = Path(temporary) / 'Spotifast.AppImage'
        replace_binary = not skip_download and (not binary.exists() or digest(binary) != entry['sha256'])
        if replace_binary:
            download(entry, candidate)
        backup = data / 'apariencia-anterior.json'
        if not backup.exists():
            write_json(backup, {k: {'present': k in current, 'value': current.get(k)}
                               for k in (*updates, 'custom_theme_cache')})
        if replace_binary:
            preserve(binary, data)
            atomic_write(binary, candidate.read_bytes(), 0o755)
        binary.chmod(0o755)
        for filename in (t + '.json' for t in THEMES):
            copy_asset(ASSETS / filename, config / 'themes' / filename, data)
        copy_asset(ASSETS / 'EVA-01.wsz', config / 'skins/EVA-01.wsz', data)
        copy_asset(ASSETS / 'eva-01-audio.svg', data / 'eva-01-audio.svg', data)
        copy_asset(HERE.parent / 'LICENSE', data / 'LICENSE-Spotifast', data)
        launcher = paths['launcher']
        preserve(launcher, data)
        # The official AppImage can run without FUSE via its runtime fallback.
        content = '#!/bin/sh\nexec ' + shlex.quote(str(binary)) + ' "$@"\n'
        atomic_write(launcher, content.encode(), 0o755)
        desktop = paths['applications'] / 'eva-01-audio.desktop'
        preserve(desktop, data)
        escaped = str(launcher).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%')
        text = ('[Desktop Entry]\nType=Application\nName=EVA-01 Audio\n'
                'Comment=Spotifast con tema EVA-01\nExec="' + escaped + '" %U\n'
                'Icon=' + str(data / 'eva-01-audio.svg') + '\nTerminal=false\n'
                'Categories=AudioVideo;Audio;Player;\nStartupWMClass=spotifast\n'
                'Keywords=Spotify;Spotifast;Evangelion;NERV;EVA;\n')
        atomic_write(desktop, text.encode(), 0o644)
        current.update(updates)
        current.pop('custom_theme_cache', None)
        write_json(settings, current)
    if root is None and shutil.which('update-desktop-database'):
        subprocess.run(['update-desktop-database', str(paths['applications'])], check=False)
    print('EVA-01 Audio instalado. Ábrelo desde el menú de aplicaciones. Ctrl+M: modo compacto.')


def restore(root=None):
    paths = layout(root)
    if root is None and running():
        raise ValueError('Cierra Spotifast antes de restaurar.')
    backup = paths['data'] / 'apariencia-anterior.json'
    if not backup.is_file():
        raise ValueError('No hay copia de preferencias anterior.')
    original = read_json(backup)
    settings = paths['config'] / 'settings.json'
    current = read_json(settings)
    for key, item in original.items():
        if item['present']:
            current[key] = item['value']
        else:
            current.pop(key, None)
    write_json(settings, current)
    print('Preferencias anteriores restauradas. Recursos instalados conservados.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, help='Perfil aislado de pruebas; ignora XDG y procesos del usuario.')
    parser.add_argument('--theme', choices=THEMES, default=THEMES[0])
    parser.add_argument('--skip-download', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--restore', action='store_true')
    args = parser.parse_args()
    try:
        if args.restore:
            if args.dry_run:
                print('Simulación: se restaurarían únicamente las preferencias visuales.')
            else:
                restore(args.root)
        else:
            install(args.root, args.theme, args.skip_download, args.dry_run)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f'Error: {error}\n')


if __name__ == '__main__':
    main()

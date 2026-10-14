import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('eva_linux', ROOT / 'eva/install_linux.py')
eva = importlib.util.module_from_spec(spec)
spec.loader.exec_module(eva)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='eva tests ')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'profile with spaces'
        self.paths = eva.layout(self.root)
        self.settings = self.paths['config'] / 'settings.json'
        self.before = {'theme': 'light', 'custom_theme': 'other.json',
                       'volume': 9876, 'home': {'extra': True}, 'unknown_future': [1, 2]}

    def prepare(self):
        eva.write_json(self.settings, self.before)
        eva.atomic_write(self.paths['binary'], b'fake test executable', 0o755)

    def test_preserves_unrelated_settings_and_restores_later_changes(self):
        self.prepare()
        eva.install(self.root, skip_download=True)
        value = eva.read_json(self.settings)
        self.assertEqual(value['custom_theme'], 'EVA-01.json')
        for field in ('volume', 'home', 'unknown_future'):
            self.assertEqual(value[field], self.before[field])
        value['volume'] = 5432
        eva.write_json(self.settings, value)
        eva.restore(self.root)
        value = eva.read_json(self.settings)
        self.assertEqual(value['theme'], 'light')
        self.assertEqual(value['custom_theme'], 'other.json')
        self.assertNotIn('skin', value)
        self.assertEqual(value['volume'], 5432)

    def test_reinstall_keeps_first_backup_and_switches_theme(self):
        self.prepare()
        eva.install(self.root, skip_download=True)
        backup = self.paths['data'] / 'apariencia-anterior.json'
        original = backup.read_bytes()
        eva.install(self.root, theme='EVA-01 Terminal', skip_download=True)
        self.assertEqual(original, backup.read_bytes())
        self.assertEqual(eva.read_json(self.settings)['custom_theme'], 'EVA-01 Terminal.json')
        self.assertIn('profile with spaces', self.paths['launcher'].read_text())
        self.assertIn('Exec="', (self.paths['applications'] / 'eva-01-audio.desktop').read_text())

    def test_dry_run_does_not_create_profile(self):
        eva.install(self.root, dry_run=True)
        self.assertFalse(self.root.exists())

    def test_invalid_settings_fail_without_modifications(self):
        self.prepare()
        self.settings.write_text('[]')
        with self.assertRaises(ValueError):
            eva.install(self.root, skip_download=True)
        self.assertFalse(self.paths['data'].exists())
        self.assertEqual(self.settings.read_text(), '[]')

    def test_bad_download_hash_does_not_change_profile(self):
        self.prepare()
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, size):
                if hasattr(self, 'done'): return b''
                self.done = True
                return b'wrong download'
        with patch.object(eva.urllib.request, 'urlopen', return_value=Response()):
            with self.assertRaisesRegex(ValueError, 'SHA-256'):
                eva.install(self.root)
        self.assertEqual(eva.read_json(self.settings), self.before)
        self.assertFalse(self.paths['data'].exists())
        self.assertEqual(self.paths['binary'].read_bytes(), b'fake test executable')

    def test_preserves_existing_homonymous_asset(self):
        self.prepare()
        target = self.paths['config'] / 'themes/EVA-01.json'
        eva.atomic_write(target, b'previous custom artwork')
        eva.install(self.root, skip_download=True)
        backups = list((self.paths['data'] / 'recursos-anteriores').glob('EVA-01.json.*.bak'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), b'previous custom artwork')

    def test_xdg_directories_and_relative_xdg_ignored(self):
        with patch.dict(eva.os.environ, {'XDG_CONFIG_HOME': str(self.root / 'custom config'),
                                       'XDG_DATA_HOME': 'relative-path'}), patch.object(eva.Path, 'home', return_value=self.root):
            paths = eva.layout()
        self.assertEqual(paths['config'], self.root / 'custom config/spotifast')
        self.assertEqual(paths['data'], self.root / '.local/share/eva-01-audio')

    def test_skin_matches_original_sprite_dimensions(self):
        with zipfile.ZipFile(ROOT / 'eva/assets/EVA-01.wsz') as custom, zipfile.ZipFile(ROOT / 'upstream/assets/skins/spotifast.wsz') as original:
            self.assertIsNone(custom.testzip())
            count = 0
            for name in original.namelist():
                if not name.endswith('.bmp'): continue
                count += 1
                a, b = original.read(name), custom.read(name)
                self.assertEqual(b[:2], b'BM')
                self.assertEqual(struct.unpack_from('<ii', a, 18), struct.unpack_from('<ii', b, 18))
            self.assertEqual(count, 15)


if __name__ == '__main__':
    unittest.main()

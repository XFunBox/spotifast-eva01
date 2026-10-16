"""Protocol and native UI regression checks without a Spotify account or audio."""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

SOURCE = Path(__file__).resolve().parents[1] / 'eva/nightshift.py'
spec = importlib.util.spec_from_file_location('nightshift', SOURCE)
nightshift = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = nightshift
spec.loader.exec_module(nightshift)
APP = QApplication.instance() or QApplication([])


class ProtocolTests(unittest.TestCase):
    def test_real_protocol_flags_and_unicode(self):
        track = nightshift.Track.parse('playing\tSeñal\tÁrtista\tÁlbum\t83000\t214000\t65\ton\ttrack\thttps://i.scdn.co/image/a\tyes\tEVA-01\n')
        self.assertEqual(track.artist, 'Ártista')
        self.assertTrue(track.shuffle)
        self.assertTrue(track.saved)
        self.assertEqual(track.repeat, 'track')
        self.assertEqual(nightshift.stamp(track.position), '1:23')

    def test_stopped_unknown_and_malformed(self):
        self.assertEqual(nightshift.Track.parse('stopped\n').duration, 0)
        track = nightshift.Track.parse('paused\tt\ta\tb\t0\t4\t100\toff\toff\t\tunknown\t')
        self.assertFalse(track.saved)
        self.assertFalse(track.shuffle)
        for bad in ('', 'playing\tt', 'paused\tt\ta\tb\tx\t4\t100\toff\toff\t\tyes\td'):
            with self.assertRaises(ValueError):
                nightshift.Track.parse(bad)

    def test_cli_async_order_status_and_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            binary = Path(folder) / 'fake-spotifast'
            log = Path(folder) / 'commands'
            binary.write_text('#!/usr/bin/python3\nimport sys\nfrom pathlib import Path\n'
                              f'log = Path({str(log)!r})\n'
                              'with log.open("a") as f: f.write(repr(sys.argv[1:]) + "\\n")\n'
                              'if sys.argv[1] == "now-playing": print("stopped")\n'
                              'if sys.argv[1] == "fail": sys.exit(1)\n')
            binary.chmod(0o755)
            control = nightshift.Control(binary)
            updates, errors = [], []
            control.updated.connect(updates.append)
            control.error.connect(errors.append)
            control.command('volume', '42')
            control.command('spotify:search:AC%2FDC%20%24%28x%29')
            control.command('fail')
            for _ in range(100):
                QTest.qWait(20)
                if errors and updates and control.command_process is None:
                    break
            control.shutdown()
            lines = log.read_text().splitlines()
            self.assertTrue(updates)
            self.assertEqual(len(errors), 1)
            commands = [line for line in lines if 'now-playing' not in line]
            self.assertEqual(commands, ["['volume', '42']", "['spotify:search:AC%2FDC%20%24%28x%29']", "['fail']"])

    def test_missing_binary_recovers_without_spawning_forever(self):
        control = nightshift.Control('/no/such/spotifast')
        states = []
        control.online.connect(states.append)
        QTest.qWait(100)
        self.assertIn(False, states)
        self.assertIsNone(control.poll_process)
        control.shutdown()


class WindowTests(unittest.TestCase):
    def test_sliders_send_wheel_or_keyboard_changes_without_focus_but_not_poll_updates(self):
        window = nightshift.Nightshift(Path('/unused'), demo=True)
        commands = []
        window.send = lambda *args: commands.append(args)
        window.search.setFocus()
        window.volume.setValue(72)
        window.progress.setValue(90000)
        self.assertEqual(commands, [('volume', '72'), ('seek-to', '90')])
        commands.clear()
        window.update_track(nightshift.Track(position=30000, duration=180000, volume=33))
        self.assertEqual(commands, [])
        window.close()

    def test_metadata_is_plain_text_and_controls_reflect_real_flags(self):
        window = nightshift.Nightshift(Path('/unused'), demo=True)
        window.update_track(nightshift.Track.parse('paused\t<b>literal</b>\ta\tb\t1000\t5000\t20\ton\tcontext\t\tyes\td'))
        self.assertEqual(window.title.text(), '<b>literal</b>')
        self.assertEqual(window.title.textFormat(), nightshift.Qt.TextFormat.PlainText)
        self.assertEqual(window.volume.value(), 20)
        self.assertEqual(window.progress.value(), 1000)
        self.assertEqual(window.like.toolTip(), 'Quitar de favoritos')
        window.connection(False)
        self.assertFalse(window.play.isEnabled())
        window.close()


class InstallTests(unittest.TestCase):
    def test_installer_uses_existing_image_and_preserves_other_files(self):
        spec = importlib.util.spec_from_file_location('install_nightshift', SOURCE.with_name('install_nightshift.py'))
        installer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(installer)
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder) / 'home with spaces'
            home.mkdir()
            appimage = home / 'Original.AppImage'
            appimage.write_text('#!/usr/bin/python3\nfrom pathlib import Path\n'
                               'p=Path("squashfs-root"); p.mkdir()\n'
                               'b=p/"AppRun"; b.write_text("#!/bin/sh\\nexit 0\\n"); b.chmod(0o755)\n')
            appimage.chmod(0o755)
            original = appimage.read_bytes()
            unrelated = home / 'user-file'
            unrelated.write_text('keep')
            with patch.dict(os.environ, {'XDG_DATA_HOME': str(home / 'data')}):
                installer.install(home, appimage)
            self.assertTrue((home / '.local/opt/nerv-nightshift/runtime/AppRun').is_file())
            self.assertTrue((home / 'data/applications/nerv-nightshift.desktop').is_file())
            launcher = home / '.local/bin/nerv-nightshift'
            self.assertIn("'", launcher.read_text())
            self.assertEqual(appimage.read_bytes(), original)
            self.assertEqual(unrelated.read_text(), 'keep')


if __name__ == '__main__':
    unittest.main()

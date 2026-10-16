#!/usr/bin/env python3
"""A small, native working-day interface for Spotifast's local control CLI."""
import argparse
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, urlparse

from PyQt6.QtCore import Qt, QProcess, QTimer, QUrl, QSize, pyqtSignal, QObject
from PyQt6.QtGui import QColor, QFont, QIcon, QKeySequence, QPainter, QPixmap, QShortcut, QLinearGradient
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
                            QPushButton, QSlider, QVBoxLayout, QWidget)

NEON = '#9dff00'
ICONS = {
    'play': '<path d="M9 5l11 7-11 7z" fill="currentColor" stroke="none"/>',
    'pause': '<path d="M9 5v14M16 5v14" stroke-width="4"/>',
    'previous': '<path d="M6 5v14M19 5L8 12l11 7z"/>',
    'next': '<path d="M18 5v14M5 5l11 7L5 19z"/>',
    'shuffle': '<path d="M3 6h3c5 0 7 12 12 12h3m-4-4 4 4-4 3M3 18h3c2 0 4-3 6-6s4-6 6-6h3m-4-3 4 3-4 4"/>',
    'repeat': '<path d="M5 9V7h14l-3-3m3 3-3 3M19 15v2H5l3 3m-3-3 3-3"/>',
    'heart': '<path d="M12 20L4 12C-2 5 7 0 12 7c5-7 14-2 8 5z"/>',
    'volume': '<path d="M4 9h4l5-4v14l-5-4H4zM17 8q6 4 0 8"/>',
    'search': '<circle cx="10" cy="10" r="6"/><path d="m15 15 5 5"/>',
    'library': '<path d="M4 5v14M9 5v14M14 5v14m4-14 4 14"/>',
}


def icon(name, color='#b9bbc7'):
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" '
           f'viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.7" '
           'stroke-linecap="round" stroke-linejoin="round">'
           + ICONS[name].replace('currentColor', color) + '</svg>')
    pix = QPixmap(32, 32)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    QSvgRenderer(svg.encode()).render(painter)
    painter.end()
    return QIcon(pix)


@dataclass
class Track:
    state: str = 'stopped'
    title: str = 'Tu espacio para escuchar'
    artist: str = 'Elige música en tu biblioteca de Spotifast'
    album: str = ''
    position: int = 0
    duration: int = 0
    volume: int = 50
    shuffle: bool = False
    repeat: str = 'off'
    art: str = ''
    saved: bool = False
    device: str = ''

    @classmethod
    def parse(cls, raw):
        if raw.strip() == 'stopped':
            return cls()
        fields = raw.rstrip('\r\n').split('\t')
        if len(fields) != 12 or fields[0] not in ('playing', 'paused', 'stopped'):
            raise ValueError('Invalid playback snapshot')
        state, title, artist, album, pos, dur, volume, shuffle, repeat, art, saved, device = fields
        return cls(state, title, artist, album, max(0, int(pos)), max(0, int(dur)),
                   min(100, max(0, int(volume))), shuffle == 'on', repeat, art,
                   saved == 'yes', device)


class Control(QObject):
    updated = pyqtSignal(object)
    error = pyqtSignal(str)
    online = pyqtSignal(bool)

    def __init__(self, binary, parent=None):
        super().__init__(parent)
        self.binary = str(binary)
        self.pending = deque()
        self.poll_process = None
        self.command_process = None
        self.closing = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(1500)
        QTimer.singleShot(0, self.poll)

    def run(self, args, callback):
        proc = QProcess(self)
        done = False
        timeout = QTimer(proc)
        timeout.setSingleShot(True)

        def finish(ok):
            nonlocal done
            if done:
                return
            done = True
            timeout.stop()
            output = bytes(proc.readAllStandardOutput()).decode('utf-8', errors='replace')
            callback(ok, output)
            proc.deleteLater()

        def expired():
            proc.kill()
            finish(False)

        proc.finished.connect(lambda code, status: finish(code == 0 and status == QProcess.ExitStatus.NormalExit))
        proc.errorOccurred.connect(lambda _: finish(False))
        timeout.timeout.connect(expired)
        proc.start(self.binary, args)
        timeout.start(5000)
        return proc

    def poll(self):
        if self.closing or self.poll_process is not None:
            return

        def received(ok, output):
            self.poll_process = None
            self.online.emit(ok)
            if ok:
                try:
                    self.updated.emit(Track.parse(output))
                except ValueError:
                    self.online.emit(False)

        self.poll_process = self.run(['now-playing', '--raw'], received)

    def command(self, *args):
        if len(self.pending) < 32:
            self.pending.append(list(args))
        self.drain()

    def drain(self):
        if self.closing or self.command_process is not None or not self.pending:
            return

        def completed(ok, _):
            self.command_process = None
            if not ok:
                self.error.emit('Abre Spotifast para conectar el reproductor.')
            self.poll()
            self.drain()

        self.command_process = self.run(self.pending.popleft(), completed)

    def shutdown(self):
        self.closing = True
        self.pending.clear()
        self.timer.stop()
        for proc in (self.poll_process, self.command_process):
            if proc is not None:
                proc.kill()
                proc.waitForFinished(1000)


def stamp(milliseconds):
    seconds = max(0, milliseconds // 1000)
    return f'{seconds // 60}:{seconds % 60:02}'


class Nightshift(QMainWindow):
    def __init__(self, binary, demo=False):
        super().__init__()
        self.setWindowTitle('NERV Nightshift')
        self.resize(840, 450)
        self.setMinimumSize(660, 420)
        self.track = Track()
        self.demo = demo
        self.connected = False
        self.art_url = ''
        self.cover_request = None
        self.network = QNetworkAccessManager(self)
        self.control = None if demo else Control(binary, self)
        if self.control:
            self.control.updated.connect(self.update_track)
            self.control.online.connect(self.connection)
            self.control.error.connect(self.message)

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(30, 25, 30, 22)
        layout.setSpacing(24)
        header = QHBoxLayout()
        brand = QLabel('<span style="color:#9dff00">NERV</span> <span style="color:#93909f"> / NIGHTSHIFT</span>')
        brand.setObjectName('brand')
        header.addWidget(brand)
        header.addStretch()
        self.search = QLineEdit()
        self.search.setPlaceholderText('Buscar en Spotifast…')
        self.search.setAccessibleName('Buscar música en Spotifast')
        self.search.setClearButtonEnabled(True)
        self.search.addAction(icon('search'), QLineEdit.ActionPosition.LeadingPosition)
        self.search.setFixedWidth(265)
        self.search.returnPressed.connect(self.search_music)
        header.addWidget(self.search)
        layout.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(32)
        self.cover = QLabel()
        self.cover.setFixedSize(218, 218)
        self.cover.setAccessibleName('Carátula del álbum')
        body.addWidget(self.cover)
        details = QVBoxLayout()
        details.setSpacing(9)
        details.addStretch()
        eyebrow = QLabel('AHORA SUENA')
        eyebrow.setObjectName('eyebrow')
        details.addWidget(eyebrow)
        songrow = QHBoxLayout()
        self.title = QLabel()
        self.title.setObjectName('title')
        self.title.setWordWrap(True)
        songrow.addWidget(self.title, 1)
        self.like = self.button('heart', 'Guardar canción · Ctrl+G', lambda: self.send('like'))
        songrow.addWidget(self.like)
        details.addLayout(songrow)
        self.artist = QLabel()
        self.artist.setWordWrap(True)
        self.artist.setObjectName('artist')
        details.addWidget(self.artist)
        self.album = QLabel()
        self.album.setObjectName('muted')
        details.addWidget(self.album)
        details.addSpacing(12)
        controls = QHBoxLayout()
        controls.setSpacing(15)
        self.shuffle = self.button('shuffle', 'Aleatorio', lambda: self.send('shuffle'))
        self.previous = self.button('previous', 'Anterior · Alt+J', lambda: self.send('previous'))
        self.play = self.button('play', 'Reproducir / pausar · Ctrl+P', lambda: self.send('play-pause'))
        self.play.setObjectName('play')
        self.play.setFixedSize(54, 54)
        self.next = self.button('next', 'Siguiente · Alt+L', lambda: self.send('next'))
        self.repeat = self.button('repeat', 'Repetir', lambda: self.send('repeat'))
        for button in (self.shuffle, self.previous, self.play, self.next, self.repeat):
            controls.addWidget(button)
        controls.addStretch()
        details.addLayout(controls)
        details.addStretch()
        body.addLayout(details, 1)
        layout.addLayout(body, 1)

        timeline = QHBoxLayout()
        self.elapsed = QLabel('0:00')
        self.total = QLabel('0:00')
        self.progress = QSlider(Qt.Orientation.Horizontal)
        self.progress.setSingleStep(5000)
        self.progress.setPageStep(15000)
        self.progress.setAccessibleName('Posición de reproducción')
        self.progress.sliderReleased.connect(lambda: self.send('seek-to', str(self.progress.value() // 1000)))
        self.progress.valueChanged.connect(self.seek_changed)
        for widget in (self.elapsed, self.progress, self.total):
            timeline.addWidget(widget)
        layout.addLayout(timeline)
        footer = QHBoxLayout()
        library = QPushButton('  Abrir biblioteca ↗')
        library.setIcon(icon('library'))
        library.setToolTip('Abre Spotifast: biblioteca, favoritos y cola · Ctrl+B')
        library.clicked.connect(self.show_library)
        footer.addWidget(library)
        self.status = QLabel('Conectando…')
        self.status.setObjectName('muted')
        footer.addWidget(self.status, 1, Qt.AlignmentFlag.AlignCenter)
        volume_icon = QLabel()
        volume_icon.setPixmap(icon('volume').pixmap(20, 20))
        footer.addWidget(volume_icon)
        self.volume = QSlider(Qt.Orientation.Horizontal)
        self.volume.setRange(0, 100)
        self.volume.setFixedWidth(100)
        self.volume.setAccessibleName('Volumen')
        self.volume.sliderReleased.connect(lambda: self.send('volume', str(self.volume.value())))
        self.volume.valueChanged.connect(self.volume_changed)
        footer.addWidget(self.volume)
        layout.addLayout(footer)

        self.setStyleSheet('''
            QWidget { background: #16171c; color: #ebecf1; font-family: "Noto Sans"; font-size: 13px; }
            QLabel { background: transparent; }
            #brand { font-size: 12px; font-weight: 700; letter-spacing: 2px; }
            #eyebrow { color: #9dff00; font-size: 10px; font-weight: 600; letter-spacing: 2px; }
            #title { font-size: 25px; font-weight: 650; }
            #artist { color: #b9bbc7; font-size: 15px; }
            #muted { color: #868995; font-size: 12px; }
            QLineEdit { background: #202127; border: 1px solid #303139; border-radius: 8px; padding: 8px; }
            QLineEdit:focus { border-color: #9dff00; }
            QPushButton { border: 1px solid transparent; border-radius: 7px; padding: 7px; color: #b9bbc7; }
            QPushButton:hover { background: #292a33; color: #9dff00; }
            QPushButton:focus { border-color: #9dff00; }
            QPushButton:disabled { color: #575963; }
            #play { background: #9dff00; border-radius: 27px; }
            #play:hover { background: #b7ff40; }
            #play:disabled { background: #353d29; }
            QSlider::groove:horizontal { height: 4px; background: #30323b; border-radius: 2px; }
            QSlider::sub-page:horizontal { background: #9dff00; border-radius: 2px; }
            QSlider::handle:horizontal { background: #9dff00; width: 10px; margin: -4px 0; border-radius: 5px; }
            QSlider:disabled::sub-page:horizontal { background: #4a4c54; }
            QToolTip { color: #ebecf1; background: #292a33; border: 1px solid #51535e; }
        ''')
        for keys, action in [('Ctrl+P', lambda: self.send('play-pause')),
                             ('Alt+J', lambda: self.send('previous')),
                             ('Alt+L', lambda: self.send('next')),
                             ('Ctrl+G', lambda: self.send('like')),
                             ('Ctrl+B', self.show_library), ('Ctrl+K', self.search.setFocus),
                             ('Ctrl+Q', self.close)]:
            QShortcut(QKeySequence(keys), self, activated=action)
        self.update_track(self.track)
        self.connection(False)
        if demo:
            self.connection(True)
            self.update_track(Track('playing', 'Midnight Signal', 'Nightshift', 'Tokyo-3 · Demo',
                                    83000, 214000, 65, False, 'off', '', True, 'Vista de demostración'))

    def button(self, name, label, action):
        button = QPushButton()
        button.setIcon(icon(name))
        button.setIconSize(QSize(23, 23))
        button.setFixedSize(36, 36)
        button.setToolTip(label)
        button.setAccessibleName(label.split(' · ')[0])
        button.clicked.connect(action)
        return button

    def send(self, *args):
        if self.control and self.connected:
            self.control.command(*args)

    def show_library(self):
        if self.demo:
            return
        if self.connected:
            self.control.command('show')
        else:
            QProcess.startDetached(self.control.binary, [])
            self.message('Abriendo Spotifast…')

    def search_music(self):
        query = self.search.text().strip()
        if query and self.control:
            if self.connected:
                self.control.command('spotify:search:' + quote(query, safe=''))
            else:
                self.message('Abre la biblioteca para conectar Spotifast.')

    def message(self, text):
        self.status.setText(text)
        self.status.setToolTip(text)

    def connection(self, online):
        self.connected = online
        for widget in (self.play, self.previous, self.next, self.shuffle, self.repeat,
                       self.like, self.progress, self.volume):
            widget.setEnabled(online)
        if not online:
            self.message('Spotifast desconectado')
        else:
            self.message('Conectado' if not self.demo else 'Demostración')

    def volume_changed(self, value):
        self.volume.setToolTip(f'Volumen: {value} %')
        # Keyboard/wheel changes do not emit sliderReleased.
        if not self.volume.isSliderDown():
            self.send('volume', str(value))

    def seek_changed(self, value):
        if not self.progress.isSliderDown():
            self.send('seek-to', str(value // 1000))

    def update_track(self, track):
        self.track = track
        for label, text in ((self.title, track.title), (self.artist, track.artist), (self.album, track.album)):
            label.setTextFormat(Qt.TextFormat.PlainText)
            label.setText(text)
            label.setToolTip(text)
        self.play.setIcon(icon('pause' if track.state == 'playing' else 'play', '#16171c'))
        for button, name, selected in ((self.shuffle, 'shuffle', track.shuffle),
                                       (self.repeat, 'repeat', track.repeat != 'off'),
                                       (self.like, 'heart', track.saved)):
            button.setIcon(icon(name, NEON if selected else '#a0a3b2'))
        self.repeat.setToolTip({'track': 'Repetir: canción', 'context': 'Repetir: lista'}.get(track.repeat, 'Repetir: desactivado'))
        self.like.setToolTip('Quitar de favoritos' if track.saved else 'Guardar en favoritos')
        if not self.progress.isSliderDown():
            self.progress.blockSignals(True)
            self.progress.setRange(0, max(1, track.duration))
            self.progress.setValue(min(track.position, track.duration))
            self.progress.blockSignals(False)
        self.elapsed.setText(stamp(track.position))
        self.total.setText(stamp(track.duration))
        if not self.volume.isSliderDown():
            self.volume.blockSignals(True)
            self.volume.setValue(track.volume)
            self.volume.blockSignals(False)
            self.volume.setToolTip(f'Volumen: {track.volume} %')
        if track.art != self.art_url or self.cover.pixmap() is None or self.cover.pixmap().isNull():
            self.load_cover(track.art)

    def load_cover(self, url):
        self.art_url = url
        if self.cover_request is not None:
            self.cover_request.abort()
            self.cover_request = None
        pix = QPixmap(218, 218)
        painter = QPainter(pix)
        gradient = QLinearGradient(0, 0, 218, 218)
        gradient.setColorAt(0, QColor('#362946'))
        gradient.setColorAt(1, QColor('#151b22'))
        painter.fillRect(pix.rect(), gradient)
        painter.setPen(QColor('#a2ff30'))
        painter.setFont(QFont('Noto Sans', 48, QFont.Weight.Light))
        painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, '♪')
        painter.end()
        self.cover.setPixmap(pix)
        parsed = urlparse(url)
        if parsed.scheme != 'https' or not (parsed.hostname or '').endswith('.scdn.co'):
            return
        request = QNetworkRequest(QUrl(url))
        request.setTransferTimeout(8000)
        request.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute,
                             QNetworkRequest.RedirectPolicy.ManualRedirectPolicy)
        reply = self.network.get(request)
        self.cover_request = reply

        def ready():
            if reply.bytesAvailable() > 5 * 1024 * 1024:
                reply.abort()

        def finished():
            if self.cover_request is reply:
                self.cover_request = None
                data = bytes(reply.readAll())
                image = QPixmap()
                if reply.error() == reply.NetworkError.NoError and len(data) <= 5 * 1024 * 1024 and image.loadFromData(data):
                    self.cover.setPixmap(image.scaled(218, 218, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                                      Qt.TransformationMode.SmoothTransformation))
            reply.deleteLater()

        reply.readyRead.connect(ready)
        reply.finished.connect(finished)

    def closeEvent(self, event):
        if self.control:
            self.control.shutdown()
        event.accept()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spotifast', type=Path,
                        default=Path.home() / '.local/opt/nerv-nightshift/runtime/AppRun')
    parser.add_argument('--demo', action='store_true', help='Preview without playback or account access')
    parser.add_argument('--screenshot', type=Path, help='Save a demo preview and quit')
    args = parser.parse_args()
    app = QApplication([])
    window = Nightshift(args.spotifast, demo=args.demo or bool(args.screenshot))
    window.show()
    if args.screenshot:
        def capture():
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            window.grab().save(str(args.screenshot))
            app.quit()
        QTimer.singleShot(150, capture)
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())

import dataclasses
import signal
import sys
from importlib.resources import files
from pathlib import Path

from PySide6.QtCore import QDir, QFileSystemWatcher, QLockFile, QTimer, QUrl, Qt
from PySide6.QtGui import QAction, QActionGroup, QDesktopServices, QIcon
from PySide6.QtMultimedia import QAudioOutput, QMediaDevices, QMediaPlayer
from PySide6.QtWidgets import (
    QApplication, QDialog, QFileDialog, QMenu, QMessageBox, QSystemTrayIcon,
)

from . import APP_ID, APP_NAME, SHORT_NAME, autostart, keys
from . import config as config_mod
from . import keyboard as keyboard_mod
from . import model
from .first_run import FirstRunDialog
from .listener import Listener

try:
    from PySide6.QtCore import QMicrophonePermission
except ImportError:
    QMicrophonePermission = None

FLASH_MS = 1000


def icon(name: str) -> QIcon:
    return QIcon(str(files("voice_to_hotkey") / "icons" / f"{name}.svg"))


def quoted(phrases: list[str]) -> str:
    return " or ".join(f"“{p}”" for p in phrases)


class Tray(QSystemTrayIcon):
    def __init__(self, config_path: Path, keyboard, first_run: bool):
        super().__init__(icon("paused"))
        self.config_path = config_path
        self.keyboard = keyboard
        self.first_run = first_run
        self.cfg = None
        self.config_error = None
        self.listening = False
        self.downloader = None
        self.download_percent = 0
        self.flashing = False
        self.warned_words = set()
        self.ready = False
        self.pending_press = False

        self.player = QMediaPlayer()
        self.player.setAudioOutput(QAudioOutput(self.player))
        self.player.mediaStatusChanged.connect(self.on_media_status)
        self.player.errorOccurred.connect(self.on_sound_error)

        self.listener = Listener()
        self.listener.detected.connect(self.on_detected)
        self.listener.failed.connect(self.on_failed)
        self.listener.unknown_words.connect(self.on_unknown_words)

        self.build_menu()
        self.activated.connect(self.on_activated)

        # Editors often save by replacing the file, which drops the watch,
        # so reload() adds it back. The timer collapses bursts of events.
        self.watcher = QFileSystemWatcher([str(config_path)])
        self.reload_timer = QTimer(singleShot=True, interval=300)
        self.reload_timer.timeout.connect(self.reload)
        self.watcher.fileChanged.connect(self.reload_timer.start)

        self.show()
        self.reload()
        self.listening = bool(self.cfg and self.cfg.start_listening)
        self.ready = True
        self.apply()

    # Menu

    def build_menu(self):
        menu = QMenu()
        self.status_action = menu.addAction("")
        self.status_action.setEnabled(False)
        self.toggle_action = menu.addAction("")
        self.toggle_action.triggered.connect(lambda: self.set_listening(not self.listening))
        menu.addSeparator()

        self.mic_menu = menu.addMenu("Microphone")
        self.mic_menu.aboutToShow.connect(self.fill_mic_menu)

        self.sound_menu = menu.addMenu("Sound")
        self.sound_menu.aboutToShow.connect(self.fill_sound_menu)

        launch_menu = menu.addMenu("When VTH opens")
        group = QActionGroup(launch_menu)
        self.launch_listen = QAction("Start listening", group, checkable=True)
        self.launch_paused = QAction("Stay paused", group, checkable=True)
        launch_menu.addActions([self.launch_listen, self.launch_paused])
        self.launch_listen.triggered.connect(lambda: self.save("start_listening", True))
        self.launch_paused.triggered.connect(lambda: self.save("start_listening", False))

        self.autostart_action = menu.addAction("Open on login")
        self.autostart_action.setCheckable(True)
        self.autostart_action.setChecked(autostart.is_enabled())
        self.autostart_action.toggled.connect(self.set_autostart)

        menu.addAction("Open config file").triggered.connect(self.open_config)
        menu.addSeparator()
        menu.addAction(f"Quit {SHORT_NAME}").triggered.connect(QApplication.quit)
        self.menu = menu
        self.setContextMenu(menu)

    def fill_mic_menu(self):
        self.mic_menu.clear()
        group = QActionGroup(self.mic_menu)
        current = self.cfg.microphone if self.cfg else ""
        names = [""] + [d.description() for d in QMediaDevices.audioInputs()]
        for name in names:
            action = QAction(name or "System default", group, checkable=True)
            action.setChecked(name == current)
            action.triggered.connect(lambda _=False, n=name: self.save("microphone", n))
            self.mic_menu.addAction(action)

    def fill_sound_menu(self):
        self.sound_menu.clear()
        sound = self.cfg.sound if self.cfg else ""
        none = self.sound_menu.addAction("No sound")
        none.setCheckable(True)
        none.setChecked(not sound)
        none.triggered.connect(lambda: self.save("sound", ""))
        if sound:
            current = self.sound_menu.addAction(Path(sound).name)
            current.setCheckable(True)
            current.setChecked(True)
            current.setEnabled(False)
        self.sound_menu.addAction("Choose sound…").triggered.connect(self.choose_sound)

    def choose_sound(self):
        src, _ = QFileDialog.getOpenFileName(
            None, "Choose a sound to play before the hotkey", "",
            "Sounds (*.wav *.mp3 *.ogg *.flac)")
        if not src:
            return
        try:
            name = config_mod.install_sound(Path(src), self.config_path.parent)
        except OSError as e:
            self.notify("Couldn't use that sound", str(e), error=True)
            return
        self.save("sound", name)

    def update_ui(self):
        if self.config_error and not self.cfg:
            status, name = "Fix the config file to continue", "paused"
        elif self.downloader:
            status, name = f"Downloading speech model, {self.download_percent}%", "paused"
        elif self.listening and self.cfg:
            status = f"Listening for {quoted(self.cfg.phrases)}"
            name = "triggered" if self.flashing else "active"
        else:
            status, name = "Paused", "paused"
        if self.config_error and self.cfg:
            status += " (config file has an error, using the last working settings)"
        self.status_action.setText(status)
        self.setToolTip(f"{SHORT_NAME}: {status}")
        self.setIcon(icon(name))

        self.toggle_action.setText("Pause listening" if self.listening else "Start listening")
        self.toggle_action.setEnabled(self.cfg is not None)
        self.mic_menu.setEnabled(self.cfg is not None)
        self.sound_menu.setEnabled(self.cfg is not None)
        if self.cfg:
            self.launch_listen.setChecked(self.cfg.start_listening)
            self.launch_paused.setChecked(not self.cfg.start_listening)

    # Config

    def reload(self):
        if self.config_path.exists() and str(self.config_path) not in self.watcher.files():
            self.watcher.addPath(str(self.config_path))
        try:
            new = config_mod.load(self.config_path)
        except (config_mod.ConfigError, OSError) as e:
            if str(e) != self.config_error:
                self.notify("Config file problem", str(e), error=True)
            self.config_error = str(e)
            self.update_ui()
            return

        old, self.cfg = self.cfg, new
        recovered = self.config_error is not None
        self.config_error = None
        # start_listening and sound don't need the listener restarted.
        changed = old is None or dataclasses.replace(
            new, start_listening=old.start_listening, sound=old.sound) != old
        if self.ready and (recovered or changed):
            self.apply()
        self.update_ui()

    def save(self, key: str, value):
        try:
            config_mod.set_value(self.config_path, key, value)
        except Exception as e:
            self.notify("Couldn't save the setting", str(e), error=True)
        # The file watcher picks up the change and reloads.

    def open_config(self):
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.config_path))):
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.config_path.parent)))

    def set_autostart(self, on: bool):
        try:
            autostart.set_enabled(on)
        except OSError as e:
            self.notify("Couldn't change Open on login", str(e), error=True)

    # Listening

    def on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger and self.cfg:
            self.set_listening(not self.listening)

    def set_listening(self, on: bool):
        self.listening = on
        self.apply()

    def apply(self):
        """Bring the listener in line with the config and the pause state."""
        self.listener.stop()
        if self.cfg and not model.is_installed(self.cfg.model):
            self.download(self.cfg.model)
        elif self.cfg and self.listening and self.has_mic_permission():
            self.listener.start(self.cfg, model.path(self.cfg.model))
        self.update_ui()

    def has_mic_permission(self) -> bool:
        if QMicrophonePermission is None:
            return True
        app = QApplication.instance()
        status = app.checkPermission(QMicrophonePermission())
        if status == Qt.PermissionStatus.Granted:
            return True
        if status == Qt.PermissionStatus.Undetermined:
            app.requestPermission(QMicrophonePermission(), self, lambda _: self.apply())
            return False
        self.listening = False
        self.notify("VTH can't use the microphone",
                    "Allow it in your system's privacy settings, then start listening again.",
                    error=True)
        return False

    def download(self, name: str):
        if self.downloader and self.downloader.name == name:
            return
        self.download_percent = 0
        self.downloader = model.Downloader(name)
        self.downloader.progress.connect(self.on_download_progress)
        self.downloader.done.connect(self.on_download_done)
        self.downloader.failed.connect(self.on_download_failed)
        self.downloader.finished.connect(self.downloader.deleteLater)
        self.downloader.start()

    def on_download_progress(self, percent: int):
        if percent != self.download_percent:
            self.download_percent = percent
            self.update_ui()

    def on_download_done(self):
        self.downloader = None
        if self.first_run and self.cfg:
            self.first_run = False
            self.notify(
                f"{SHORT_NAME} is ready",
                f"Say {quoted(self.cfg.phrases)} to press {keys.label(self.cfg.hotkey)}."
                if self.listening else
                "Click the tray icon when you want VTH to start listening.",
            )
        self.apply()

    def on_download_failed(self, error: str):
        self.downloader = None
        self.listening = False
        self.notify("Download failed", error + "\nStart listening to try again.", error=True)
        self.update_ui()

    def on_detected(self):
        if self.pending_press:
            return
        if not self.cfg.sound:
            self.press_hotkey()
            return
        # The hotkey is pressed once the sound has played to the end.
        self.pending_press = True
        self.player.setSource(QUrl())
        self.player.setSource(QUrl.fromLocalFile(self.cfg.sound))
        self.player.play()

    def on_media_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia and self.pending_press:
            self.press_hotkey()
        elif status == QMediaPlayer.MediaStatus.InvalidMedia:
            self.on_sound_error(None, "The file isn't a sound VTH can play.")

    def on_sound_error(self, _error, message: str):
        # Whichever of the two error signals arrives first presses the key.
        if self.pending_press:
            self.notify("Couldn't play the sound", message, error=True)
            self.press_hotkey()

    def press_hotkey(self):
        self.pending_press = False
        try:
            self.keyboard.press(self.cfg.hotkey)
        except Exception as e:
            self.notify("Couldn't press the hotkey", str(e), error=True)
            return
        self.flashing = True
        self.update_ui()
        QTimer.singleShot(FLASH_MS, self.end_flash)

    def end_flash(self):
        self.flashing = False
        self.update_ui()

    def on_failed(self, error: str):
        self.listening = False
        self.listener.stop()
        self.notify("VTH stopped listening", error, error=True)
        self.update_ui()

    def on_unknown_words(self, words: list[str]):
        key = (self.cfg.model, tuple(self.cfg.phrases), tuple(words))
        if key in self.warned_words:
            return
        self.warned_words.add(key)
        listed = ", ".join(f"“{w}”" for w in words)
        self.notify(
            "Some words aren't recognized",
            f"The speech model doesn't know {listed}, so phrases with them will "
            "never match. Try another spelling in the config file.",
            error=True,
        )

    def notify(self, title: str, message: str, error: bool = False):
        kind = QSystemTrayIcon.MessageIcon.Warning if error else QSystemTrayIcon.MessageIcon.Information
        self.showMessage(title, message, kind, 8000 if error else 4000)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_ID)
    app.setDesktopFileName(APP_ID)
    app.setWindowIcon(icon("app"))
    app.setQuitOnLastWindowClosed(False)
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    lock = QLockFile(QDir.temp().filePath(f"{APP_ID}.lock"))
    if not lock.tryLock(100):
        QMessageBox.information(None, APP_NAME,
                                "VTH is already running. Look for its icon in the system tray.")
        return

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, APP_NAME,
                             "VTH lives in the system tray, but your desktop doesn't have "
                             "one. On GNOME, install the AppIndicator extension and try again.")
        sys.exit(1)

    config_path = config_mod.path()
    first_run = not config_path.exists()
    if first_run:
        dialog = FirstRunDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        config_mod.create(config_path, **dialog.values())
        if dialog.start_on_login.isChecked():
            autostart.set_enabled(True)

    try:
        keyboard = keyboard_mod.create()
    except keyboard_mod.KeyboardError as e:
        QMessageBox.critical(None, APP_NAME, str(e))
        sys.exit(1)
    problem = keyboard.permission_problem()
    if problem:
        QMessageBox.warning(None, APP_NAME, problem)

    tray = Tray(config_path, keyboard, first_run)
    app.aboutToQuit.connect(tray.listener.stop)
    app.aboutToQuit.connect(keyboard.close)
    sys.exit(app.exec())

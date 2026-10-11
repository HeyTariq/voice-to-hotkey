import signal
import sys
from importlib.resources import files
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QAction, QDesktopServices, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

from . import config as config_mod
from . import model
from .keyboard import Keyboard
from .listener import Listener

AUTOSTART_PATH = Path.home() / ".config" / "autostart" / "ok-garmin.desktop"
AUTOSTART_ENTRY = f"""\
[Desktop Entry]
Type=Application
Name=ok-garmin
Comment=Presses a key when it hears the wake phrase
Exec={sys.executable} -m ok_garmin.app
X-GNOME-Autostart-enabled=true
"""


def icon(name: str) -> QIcon:
    return QIcon(str(files("ok_garmin") / "icons" / f"{name}.svg"))


class Tray(QSystemTrayIcon):
    def __init__(self, cfg: config_mod.Config, keyboard: Keyboard):
        super().__init__(icon("active"))
        self.cfg = cfg
        self.keyboard = keyboard

        if not (model.MODELS_DIR / cfg.model).is_dir():
            self.show()
            self.showMessage("ok-garmin", f"Downloading speech model {cfg.model}")
        self.listener = Listener(cfg, model.ensure(cfg.model))
        self.listener.detected.connect(self.on_detected)
        self.listener.failed.connect(self.on_failed)

        menu = QMenu()
        self.listening = QAction("Listening", menu, checkable=True, checked=True)
        self.listening.toggled.connect(self.set_listening)
        autostart = QAction("Start on login", menu, checkable=True,
                            checked=AUTOSTART_PATH.exists())
        autostart.toggled.connect(self.set_autostart)
        open_config = QAction("Open config", menu)
        open_config.triggered.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(config_mod.CONFIG_PATH))))
        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(QApplication.quit)
        menu.addActions([self.listening, autostart, open_config])
        menu.addSeparator()
        menu.addAction(quit_action)
        self.menu = menu
        self.setContextMenu(menu)

        self.set_listening(True)
        self.show()

    def set_listening(self, on: bool):
        if on:
            self.listener.start()
        else:
            self.listener.stop()
        self.setIcon(icon("active" if on else "paused"))
        self.setToolTip(f"ok-garmin: {'listening' if on else 'paused'}")

    def set_autostart(self, on: bool):
        if on:
            AUTOSTART_PATH.parent.mkdir(parents=True, exist_ok=True)
            AUTOSTART_PATH.write_text(AUTOSTART_ENTRY)
        else:
            AUTOSTART_PATH.unlink(missing_ok=True)

    def on_detected(self):
        self.keyboard.press()
        self.showMessage("ok-garmin", f"Wake phrase heard, pressed {self.cfg.key}",
                         QSystemTrayIcon.MessageIcon.Information, 2000)

    def on_failed(self, error: str):
        self.listening.setChecked(False)
        self.showMessage("ok-garmin stopped listening", error,
                         QSystemTrayIcon.MessageIcon.Critical)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    cfg = config_mod.load()
    try:
        keyboard = Keyboard(cfg.key)
    except Exception as e:
        QMessageBox.critical(None, "ok-garmin", f"Can't create the virtual keyboard: {e}")
        sys.exit(1)

    tray = Tray(cfg, keyboard)
    app.aboutToQuit.connect(tray.listener.stop)
    app.aboutToQuit.connect(keyboard.close)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

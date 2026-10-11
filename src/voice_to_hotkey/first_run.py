import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QPalette
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QKeySequenceEdit,
    QLabel, QLineEdit, QVBoxLayout, QWidget,
)

from . import APP_NAME, keys
from .model import LANGUAGES

QT_KEYS = {
    Qt.Key.Key_Space: "space", Qt.Key.Key_Return: "enter", Qt.Key.Key_Enter: "enter",
    Qt.Key.Key_Tab: "tab", Qt.Key.Key_Escape: "esc", Qt.Key.Key_Backspace: "backspace",
    Qt.Key.Key_Delete: "delete", Qt.Key.Key_Insert: "insert", Qt.Key.Key_Home: "home",
    Qt.Key.Key_End: "end", Qt.Key.Key_PageUp: "pageup", Qt.Key.Key_PageDown: "pagedown",
    Qt.Key.Key_Up: "up", Qt.Key.Key_Down: "down", Qt.Key.Key_Left: "left",
    Qt.Key.Key_Right: "right", Qt.Key.Key_Print: "printscreen", Qt.Key.Key_Pause: "pause",
    Qt.Key.Key_ScrollLock: "scrolllock", Qt.Key.Key_CapsLock: "capslock",
    Qt.Key.Key_Minus: "minus", Qt.Key.Key_Equal: "equal", Qt.Key.Key_Comma: "comma",
    Qt.Key.Key_Period: "period", Qt.Key.Key_Slash: "slash", Qt.Key.Key_Semicolon: "semicolon",
    Qt.Key.Key_Apostrophe: "apostrophe", Qt.Key.Key_QuoteLeft: "grave",
    Qt.Key.Key_BracketLeft: "leftbracket", Qt.Key.Key_BracketRight: "rightbracket",
    Qt.Key.Key_Backslash: "backslash",
}

# On macOS, Qt reports the Command key as Control and Control as Meta.
if sys.platform == "darwin":
    QT_MODIFIERS = {Qt.KeyboardModifier.MetaModifier: "ctrl",
                    Qt.KeyboardModifier.ControlModifier: "meta"}
else:
    QT_MODIFIERS = {Qt.KeyboardModifier.ControlModifier: "ctrl",
                    Qt.KeyboardModifier.MetaModifier: "meta"}
QT_MODIFIERS |= {Qt.KeyboardModifier.ShiftModifier: "shift",
                 Qt.KeyboardModifier.AltModifier: "alt"}


def combo_from_sequence(seq: QKeySequence) -> list[str] | None:
    """Portable combo for the first chord of a recorded key sequence."""
    if seq.isEmpty():
        return None
    chord = seq[0]
    key = chord.key()
    code = key.value
    if Qt.Key.Key_A.value <= code <= Qt.Key.Key_Z.value or Qt.Key.Key_0.value <= code <= Qt.Key.Key_9.value:
        name = chr(code).lower()
    elif Qt.Key.Key_F1.value <= code <= Qt.Key.Key_F24.value:
        name = f"f{code - Qt.Key.Key_F1.value + 1}"
    else:
        name = QT_KEYS.get(key)
    if name is None:
        return None
    mods = chord.keyboardModifiers()
    names = [n for flag, n in QT_MODIFIERS.items() if mods & flag]
    return keys.parse("+".join(names + [name]))


class FirstRunDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Set up {APP_NAME}")
        self.setMinimumWidth(460)

        intro = QLabel(
            "Say a phrase and VTH presses a hotkey for you, like saving a clip "
            "in your recording app. Recognition runs on this computer and "
            "nothing you say leaves it."
        )
        intro.setWordWrap(True)

        self.language = QComboBox()
        self.language.addItems(LANGUAGES)

        self.phrase = QLineEdit("clip that")
        self.phrase.setPlaceholderText("clip that")
        self.phrase.textChanged.connect(self.validate)

        self.hotkey = QKeySequenceEdit(QKeySequence("F8"))
        self.hotkey.setMaximumSequenceLength(1)
        self.hotkey.setClearButtonEnabled(True)
        self.hotkey.keySequenceChanged.connect(self.validate)

        self.hotkey_hint = hint("")

        self.start_listening = QCheckBox("Start listening as soon as VTH opens")
        self.start_listening.setChecked(True)
        self.start_on_login = QCheckBox("Open VTH when I log in")

        form = QFormLayout()
        form.setVerticalSpacing(12)
        form.addRow("Language", self.language)
        form.addRow("Phrase", stacked(self.phrase, hint("Short phrases made of common words work best.")))
        form.addRow("Hotkey", stacked(self.hotkey, self.hotkey_hint))

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Start")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        outro = hint("You can change all of this later. Open the config file from "
                     "VTH's tray menu.")

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(intro)
        layout.addLayout(form)
        layout.addWidget(self.start_listening)
        layout.addWidget(self.start_on_login)
        layout.addWidget(outro)
        layout.addWidget(self.buttons)

        self.validate()

    def combo(self) -> list[str] | None:
        try:
            return combo_from_sequence(self.hotkey.keySequence())
        except keys.HotkeyError:
            return None

    def validate(self):
        combo = self.combo()
        if self.hotkey.keySequence().isEmpty():
            self.hotkey_hint.setText("Click the box, then press the key or combo your app uses.")
        elif combo is None:
            self.hotkey_hint.setText("That key isn't supported. Try a letter, number or F key, "
                                     "with or without Ctrl, Shift or Alt.")
        else:
            self.hotkey_hint.setText(f"VTH will press {keys.label(combo)}. To change it, "
                                     "click the box and press the key your app uses.")
        ok = combo is not None and bool(self.phrase.text().strip())
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(ok)

    def values(self) -> dict:
        return {
            "phrases": [self.phrase.text().strip().lower()],
            "hotkey": "+".join(self.combo()),
            "start_listening": self.start_listening.isChecked(),
            "model": LANGUAGES[self.language.currentText()],
        }


def hint(text: str) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setForegroundRole(QPalette.ColorRole.PlaceholderText)
    return label


def stacked(field: QWidget, below: QLabel) -> QWidget:
    """A form field with its hint text tucked right underneath."""
    box = QWidget()
    layout = QVBoxLayout(box)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)
    layout.addWidget(field)
    layout.addWidget(below)
    return box

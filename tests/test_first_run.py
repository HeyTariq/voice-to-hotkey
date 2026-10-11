import sys

import pytest
from PySide6.QtGui import QKeySequence

from voice_to_hotkey.first_run import combo_from_sequence


@pytest.mark.parametrize("seq, expected", [
    ("F8", ["f8"]),
    ("Alt+F10", ["alt", "f10"]),
    ("Shift+S", ["shift", "s"]),
    ("Print", ["printscreen"]),
])
def test_combo_from_sequence(seq, expected):
    assert combo_from_sequence(QKeySequence(seq)) == expected


@pytest.mark.skipif(sys.platform == "darwin", reason="Qt swaps Ctrl and Meta on macOS")
def test_ctrl_maps_to_ctrl():
    assert combo_from_sequence(QKeySequence("Ctrl+Shift+S")) == ["ctrl", "shift", "s"]


def test_unsupported_key():
    assert combo_from_sequence(QKeySequence("Ctrl+F35")) is None
    assert combo_from_sequence(QKeySequence()) is None

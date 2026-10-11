import pytest

from voice_to_hotkey import keys


@pytest.mark.parametrize("combo, expected", [
    ("f8", ["f8"]),
    ("Alt+F10", ["alt", "f10"]),
    ("shift + ctrl + s", ["ctrl", "shift", "s"]),
    ("cmd+shift+4", ["shift", "meta", "4"]),
    ("ctrl+-", ["ctrl", "minus"]),
    ("Escape", ["esc"]),
])
def test_parse(combo, expected):
    assert keys.parse(combo) == expected


@pytest.mark.parametrize("combo", ["", "ctrl+", "alt", "f8+alt", "ctrl+banana", "hyper+a"])
def test_parse_rejects(combo):
    with pytest.raises(keys.HotkeyError):
        keys.parse(combo)


def test_label():
    assert keys.label(["ctrl", "shift", "s"]) == "Ctrl+Shift+S"
    assert keys.label(["alt", "f10"]) == "Alt+F10"


def test_every_key_maps_to_evdev():
    ecodes = pytest.importorskip("evdev").ecodes
    for name in keys.MODIFIERS + keys.KEYS:
        assert keys.to_evdev(name) in ecodes.ecodes, name

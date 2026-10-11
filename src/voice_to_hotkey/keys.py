"""Portable key names and hotkey combos like "alt+f10".

Each OS backend maps these names to its own key codes, so the config file
reads the same everywhere.
"""

import string

MODIFIERS = ["ctrl", "shift", "alt", "meta"]

NAMED_KEYS = [
    "space", "enter", "tab", "esc", "backspace", "delete", "insert",
    "home", "end", "pageup", "pagedown", "up", "down", "left", "right",
    "printscreen", "pause", "scrolllock", "capslock",
]

# Punctuation keys by name, with the character they type on a US layout.
SYMBOL_KEYS = {
    "minus": "-", "equal": "=", "comma": ",", "period": ".", "slash": "/",
    "semicolon": ";", "apostrophe": "'", "grave": "`",
    "leftbracket": "[", "rightbracket": "]", "backslash": "\\",
}

FUNCTION_KEYS = [f"f{n}" for n in range(1, 25)]

KEYS = (
    list(string.ascii_lowercase)
    + list(string.digits)
    + FUNCTION_KEYS
    + NAMED_KEYS
    + list(SYMBOL_KEYS)
)

ALIASES = {
    "control": "ctrl", "option": "alt", "cmd": "meta", "command": "meta",
    "win": "meta", "super": "meta", "return": "enter", "escape": "esc",
    "del": "delete", "ins": "insert", "pgup": "pageup", "pgdn": "pagedown",
    "prtsc": "printscreen", "print": "printscreen",
}
ALIASES |= {char: name for name, char in SYMBOL_KEYS.items()}


class HotkeyError(ValueError):
    pass


def parse(combo: str) -> list[str]:
    """Split "Ctrl+Shift+S" into ["ctrl", "shift", "s"].

    Modifiers come first in a fixed order and exactly one non-modifier key
    ends the combo.
    """
    names = [ALIASES.get(p, p) for p in combo.replace(" ", "").lower().split("+")]
    if "" in names:
        raise HotkeyError(f"'{combo}' isn't a hotkey. Use something like f8 or alt+f10.")

    *mods, key = names
    for name in mods:
        if name not in MODIFIERS:
            raise HotkeyError(f"'{name}' in '{combo}' isn't a modifier. Use ctrl, shift, alt or meta.")
    if key in MODIFIERS:
        raise HotkeyError(f"'{combo}' needs a key after the modifiers, like alt+f10.")
    if key not in KEYS:
        raise HotkeyError(f"'{key}' isn't a supported key.")
    return [m for m in MODIFIERS if m in mods] + [key]


def label(names: list[str]) -> str:
    """Human form of a parsed combo, like "Alt+F10"."""
    return "+".join(
        n.upper() if len(n) == 1 or n in FUNCTION_KEYS else n.capitalize()
        for n in names
    )


def to_evdev(name: str) -> str:
    """Linux input event name for a key, like KEY_F10."""
    special = {
        "ctrl": "LEFTCTRL", "shift": "LEFTSHIFT", "alt": "LEFTALT",
        "meta": "LEFTMETA", "printscreen": "SYSRQ", "period": "DOT",
        "leftbracket": "LEFTBRACE", "rightbracket": "RIGHTBRACE",
    }
    return "KEY_" + special.get(name, name).upper()

import tomllib
from dataclasses import dataclass
from pathlib import Path

import tomlkit
from PySide6.QtCore import QStandardPaths

from . import keys

TEMPLATE = """\
# Voice to Hotkey settings. VTH reloads this file as soon as you save it.

# Phrases to listen for. Saying any one of them presses the hotkey.
# Every word must be in the speech model's vocabulary. If a phrase never
# triggers, VTH shows which words the model doesn't know; try other
# spellings of those words.
phrases = ["clip that"]

# Hotkey to press, like "f8", "alt+f10" or "ctrl+shift+s".
# Modifiers: ctrl, shift, alt, meta (the Windows or Command key).
hotkey = "f8"

# Whether VTH starts listening right away when it launches.
start_listening = true

# Speech model, from https://alphacephei.com/vosk/models
# VTH downloads it the first time it's needed.
model = "vosk-model-small-en-us-0.15"

# Microphone to listen to. Empty means the system default.
# Pick one from the tray menu, or type part of its name.
microphone = ""

# Seconds to ignore the phrase after it triggers.
cooldown_seconds = 3

# Lowest per-word recognition confidence (0 to 1) that still counts.
min_confidence = 0.7
"""


class ConfigError(Exception):
    pass


@dataclass
class Config:
    phrases: list[str]
    hotkey: list[str]
    start_listening: bool
    model: str
    microphone: str
    cooldown_seconds: float
    min_confidence: float


def path() -> Path:
    base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppConfigLocation)
    return Path(base) / "config.toml"


def load(file: Path) -> Config:
    defaults = tomllib.loads(TEMPLATE)
    try:
        data = defaults | tomllib.loads(file.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"The config file has a syntax error: {e}") from None

    try:
        phrases = data["phrases"]
        if isinstance(phrases, str):
            phrases = [phrases]
        phrases = [" ".join(p.lower().split()) for p in phrases if p.strip()]
        hotkey = keys.parse(data["hotkey"])
        cfg = Config(
            phrases=phrases,
            hotkey=hotkey,
            start_listening=bool(data["start_listening"]),
            model=str(data["model"]),
            microphone=str(data["microphone"]),
            cooldown_seconds=float(data["cooldown_seconds"]),
            min_confidence=float(data["min_confidence"]),
        )
    except keys.HotkeyError as e:
        raise ConfigError(str(e)) from None
    except (TypeError, ValueError, AttributeError) as e:
        raise ConfigError(f"The config file has a setting with the wrong type: {e}") from None
    if not cfg.phrases:
        raise ConfigError("Add at least one phrase to the config file.")
    return cfg


def create(file: Path, **values):
    """Write a new config from the commented template with these values set."""
    doc = tomlkit.parse(TEMPLATE)
    for key, value in values.items():
        doc[key] = value
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(tomlkit.dumps(doc), encoding="utf-8")


def set_value(file: Path, key: str, value):
    """Change one setting in place, keeping the user's comments and layout."""
    doc = tomlkit.parse(file.read_text(encoding="utf-8"))
    doc[key] = value
    file.write_text(tomlkit.dumps(doc), encoding="utf-8")

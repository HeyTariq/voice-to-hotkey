import tomllib
from dataclasses import dataclass
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "ok-garmin"
CONFIG_PATH = CONFIG_DIR / "config.toml"

DEFAULT_CONFIG = """\
# Spellings of the wake phrase. Any one of them triggers the key press.
# Every word must exist in the Vosk model's vocabulary. The small German
# model doesn't know "garmin", so sound-alike words stand in for it.
phrases = [
    "ok karmin video speichern",
    "okay karmin video speichern",
    "ok carmen video speichern",
    "okay carmen video speichern",
    "ok gar min video speichern",
    "okay gar min video speichern",
]

# Key to press, as a Linux input event name (KEY_F8, KEY_SPACE, KEY_A, ...).
key = "KEY_F8"

# Vosk model name from https://alphacephei.com/vosk/models
model = "vosk-model-small-de-0.15"

# PipeWire source to listen to. Empty means the default mic.
# List sources with: pw-cli list-objects Node | grep node.name
device = ""

# Seconds to ignore the phrase after a trigger.
cooldown_seconds = 3

# Lowest per-word recognizer confidence (0 to 1) that still counts as a match.
min_confidence = 0.7
"""


@dataclass
class Config:
    phrases: list[str]
    key: str
    model: str
    device: str
    cooldown_seconds: float
    min_confidence: float


def load() -> Config:
    if not CONFIG_PATH.exists():
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(DEFAULT_CONFIG)
    defaults = tomllib.loads(DEFAULT_CONFIG)
    data = defaults | tomllib.loads(CONFIG_PATH.read_text())
    return Config(
        phrases=[p.lower() for p in data["phrases"]],
        key=data["key"],
        model=data["model"],
        device=data["device"],
        cooldown_seconds=float(data["cooldown_seconds"]),
        min_confidence=float(data["min_confidence"]),
    )

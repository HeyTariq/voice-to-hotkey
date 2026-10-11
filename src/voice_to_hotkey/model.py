import json
import os
import re
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from PySide6.QtCore import QStandardPaths, QThread, Signal

BASE_URL = "https://alphacephei.com/vosk/models/"

# Small Vosk models, roughly 40 to 90 MB each.
LANGUAGES = {
    "English": "vosk-model-small-en-us-0.15",
    "Català": "vosk-model-small-ca-0.4",
    "Čeština": "vosk-model-small-cs-0.4-rhasspy",
    "Deutsch": "vosk-model-small-de-0.15",
    "Español": "vosk-model-small-es-0.42",
    "Français": "vosk-model-small-fr-0.22",
    "Italiano": "vosk-model-small-it-0.22",
    "Nederlands": "vosk-model-small-nl-0.22",
    "Polski": "vosk-model-small-pl-0.22",
    "Português": "vosk-model-small-pt-0.3",
    "Svenska": "vosk-model-small-sv-rhasspy-0.15",
    "Tiếng Việt": "vosk-model-small-vn-0.4",
    "Türkçe": "vosk-model-small-tr-0.3",
    "Русский": "vosk-model-small-ru-0.22",
    "Українська": "vosk-model-small-uk-v3-small",
    "فارسی": "vosk-model-small-fa-0.42",
    "हिन्दी": "vosk-model-small-hi-0.22",
    "中文": "vosk-model-small-cn-0.22",
    "日本語": "vosk-model-small-ja-0.22",
    "한국어": "vosk-model-small-ko-0.22",
}


def models_dir() -> Path:
    base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    return Path(base) / "models"


def path(name: str) -> Path:
    return models_dir() / name


def is_installed(name: str) -> bool:
    return path(name).is_dir()


class Downloader(QThread):
    """Downloads and unpacks a model, reporting percent done."""

    progress = Signal(int)
    done = Signal()
    failed = Signal(str)

    def __init__(self, name: str):
        super().__init__()
        self.name = name

    def run(self):
        try:
            self.download()
        except Exception as e:
            self.failed.emit(f"Couldn't download the speech model {self.name}: {e}")
        else:
            self.done.emit()

    def download(self):
        root = models_dir()
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile() as tmp:
            with urllib.request.urlopen(BASE_URL + self.name + ".zip") as resp:
                total = int(resp.headers.get("Content-Length") or 0)
                read = 0
                while chunk := resp.read(256 * 1024):
                    tmp.write(chunk)
                    read += len(chunk)
                    if total:
                        self.progress.emit(read * 100 // total)
            # Unpack next to the final folder and rename, so a failed
            # download never leaves a half-written model behind.
            with tempfile.TemporaryDirectory(dir=root) as staging:
                with zipfile.ZipFile(tmp) as zf:
                    zf.extractall(staging)
                (top,) = os.listdir(staging)
                shutil.move(os.path.join(staging, top), path(self.name))


def missing_words(model, phrases: list[str]) -> list[str]:
    """Words in the phrases that the model doesn't know.

    Vosk only reports unknown grammar words as log warnings on stderr, so
    this captures stderr while building a throwaway recognizer. Returns an
    empty list if the warnings can't be captured.
    """
    import vosk

    vosk.SetLogLevel(0)
    try:
        with tempfile.TemporaryFile() as log:
            saved = os.dup(2)
            os.dup2(log.fileno(), 2)
            try:
                vosk.KaldiRecognizer(model, 16000, json.dumps(phrases + ["[unk]"]))
            finally:
                os.dup2(saved, 2)
                os.close(saved)
            log.seek(0)
            text = log.read().decode(errors="replace")
    except OSError:
        return []
    finally:
        vosk.SetLogLevel(-1)
    return re.findall(r"Ignoring word missing in vocabulary: '([^']+)'", text)

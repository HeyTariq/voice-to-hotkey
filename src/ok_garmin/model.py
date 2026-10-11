import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

MODELS_DIR = Path.home() / ".local" / "share" / "ok-garmin" / "models"
BASE_URL = "https://alphacephei.com/vosk/models/"


def ensure(name: str) -> Path:
    """Return the model directory, downloading and unpacking it on first use."""
    path = MODELS_DIR / name
    if path.is_dir():
        return path
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryFile() as tmp:
        with urllib.request.urlopen(BASE_URL + name + ".zip") as resp:
            shutil.copyfileobj(resp, tmp)
        with zipfile.ZipFile(tmp) as zf:
            zf.extractall(MODELS_DIR)
    return path

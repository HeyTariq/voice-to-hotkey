import json
import subprocess
import time
from pathlib import Path

import vosk
from PySide6.QtCore import QThread, Signal

from .config import Config

SAMPLE_RATE = 16000
CHUNK_BYTES = 4000


def matches(words: list[dict], phrases: list[str], min_confidence: float) -> bool:
    """True if any phrase appears as a contiguous run of confident words.

    A restricted Vosk grammar can still emit the phrase words in any order,
    so the whole phrase has to show up in sequence.
    """
    for phrase in phrases:
        target = phrase.split()
        for i in range(len(words) - len(target) + 1):
            window = words[i : i + len(target)]
            if [w["word"] for w in window] == target and all(
                w["conf"] >= min_confidence for w in window
            ):
                return True
    return False


class Listener(QThread):
    detected = Signal()
    failed = Signal(str)

    def __init__(self, config: Config, model_path: Path):
        super().__init__()
        self.config = config
        self.model_path = model_path
        self.model = None
        self.proc = None

    def run(self):
        try:
            if self.model is None:
                vosk.SetLogLevel(-1)
                self.model = vosk.Model(str(self.model_path))
            grammar = json.dumps(self.config.phrases + ["[unk]"])
            rec = vosk.KaldiRecognizer(self.model, SAMPLE_RATE, grammar)
            rec.SetWords(True)

            cmd = ["pw-record", "--raw", "--rate", str(SAMPLE_RATE),
                   "--channels", "1", "--format", "s16"]
            if self.config.device:
                cmd += ["--target", self.config.device]
            self.proc = subprocess.Popen(cmd + ["-"], stdout=subprocess.PIPE)
        except Exception as e:
            self.failed.emit(str(e))
            return

        last = 0.0
        while not self.isInterruptionRequested():
            data = self.proc.stdout.read(CHUNK_BYTES)
            if not data:
                break
            if not rec.AcceptWaveform(data):
                continue
            words = json.loads(rec.Result()).get("result", [])
            now = time.monotonic()
            if (
                matches(words, self.config.phrases, self.config.min_confidence)
                and now - last >= self.config.cooldown_seconds
            ):
                last = now
                self.detected.emit()

        code = self.proc.wait()
        if not self.isInterruptionRequested():
            self.failed.emit(f"pw-record stopped (exit code {code})")

    def stop(self):
        self.requestInterruption()
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
        self.wait()

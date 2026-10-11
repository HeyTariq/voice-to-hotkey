import json
import time
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Qt, QMetaObject, Signal, Slot
from PySide6.QtMultimedia import QAudio, QAudioFormat, QAudioSource, QMediaDevices

from . import model as model_mod
from .config import Config

SAMPLE_RATE = 16000


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


def find_microphone(name: str):
    """The input device whose name contains `name`, or the default one."""
    if not name:
        return QMediaDevices.defaultAudioInput()
    for device in QMediaDevices.audioInputs():
        if name.lower() in device.description().lower():
            return device
    return None


class Worker(QObject):
    """Runs on the listener thread: reads the mic and feeds Vosk."""

    detected = Signal()
    failed = Signal(str)
    unknown_words = Signal(list)

    # Loading a model takes a second or two, so keep it between restarts.
    models = {}

    def __init__(self, config: Config, model_path: Path):
        super().__init__()
        self.config = config
        self.model_path = model_path
        self.source = None
        self.last = 0.0

    @Slot()
    def start(self):
        try:
            import vosk

            vosk.SetLogLevel(-1)
            key = str(self.model_path)
            if key not in self.models:
                self.models[key] = vosk.Model(key)
            model = self.models[key]

            missing = model_mod.missing_words(model, self.config.phrases)
            if missing:
                self.unknown_words.emit(missing)

            device = find_microphone(self.config.microphone)
            if device is None or device.isNull():
                name = self.config.microphone or "default"
                raise RuntimeError(f"Can't find the {name} microphone.")

            fmt = QAudioFormat()
            fmt.setSampleRate(SAMPLE_RATE)
            fmt.setChannelCount(1)
            fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
            if not device.isFormatSupported(fmt):
                # Vosk takes any sample rate, so fall back to the device's own.
                fmt.setSampleRate(device.preferredFormat().sampleRate())
            if not device.isFormatSupported(fmt):
                raise RuntimeError(f"{device.description()} can't record mono 16-bit audio.")

            grammar = json.dumps(self.config.phrases + ["[unk]"])
            self.rec = vosk.KaldiRecognizer(model, fmt.sampleRate(), grammar)
            self.rec.SetWords(True)

            self.source = QAudioSource(device, fmt, self)
            self.source.stateChanged.connect(self.on_state)
            self.io = self.source.start()
            self.io.readyRead.connect(self.on_audio)
        except Exception as e:
            self.failed.emit(str(e))

    @Slot()
    def on_audio(self):
        data = self.io.readAll().data()
        if not data or not self.rec.AcceptWaveform(data):
            return
        words = json.loads(self.rec.Result()).get("result", [])
        now = time.monotonic()
        if (
            matches(words, self.config.phrases, self.config.min_confidence)
            and now - self.last >= self.config.cooldown_seconds
        ):
            self.last = now
            self.detected.emit()

    @Slot(QAudio.State)
    def on_state(self, state):
        if state == QAudio.State.StoppedState and self.source.error() != QAudio.Error.NoError:
            self.failed.emit(f"The microphone stopped working ({self.source.error().name}).")

    @Slot()
    def shutdown(self):
        if self.source:
            self.source.stateChanged.disconnect(self.on_state)
            self.source.stop()


class Listener(QObject):
    """Owns the listener thread. start() and stop() are safe to repeat."""

    detected = Signal()
    failed = Signal(str)
    unknown_words = Signal(list)

    def __init__(self):
        super().__init__()
        self.worker_thread = None
        self.worker = None

    def start(self, config: Config, model_path: Path):
        self.stop()
        self.worker_thread = QThread()
        self.worker = Worker(config, model_path)
        self.worker.moveToThread(self.worker_thread)
        self.worker.detected.connect(self.detected)
        self.worker.failed.connect(self.failed)
        self.worker.unknown_words.connect(self.unknown_words)
        self.worker_thread.started.connect(self.worker.start)
        self.worker_thread.finished.connect(self.worker.deleteLater)
        self.worker_thread.start()

    def stop(self):
        if not self.worker_thread:
            return
        QMetaObject.invokeMethod(self.worker, "shutdown", Qt.ConnectionType.BlockingQueuedConnection)
        self.worker_thread.quit()
        self.worker_thread.wait()
        self.worker_thread = None
        self.worker = None

    @property
    def running(self) -> bool:
        return self.worker_thread is not None

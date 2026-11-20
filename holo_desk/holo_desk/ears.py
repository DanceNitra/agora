"""Yuki's ears: the microphone stays open, Silero VAD cuts it into utterances, Whisper
large-v3-turbo on the GPU writes them down (dictate's engine and models), and the same
stream feeds a music detector.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import sounddevice as sd

log = logging.getLogger(__name__)
RATE = 16000
BLOCK_S = 0.032   # one microphone callback, also one step of the music envelope


@dataclass
class Hearing:
    is_music: bool
    bpm: float
    level_db: float
    beat: float


class Ears:
    def __init__(self, on_utterance: Callable[[str, float, float], None],
                 on_level: Callable[[float], None],
                 on_hearing: Callable[[Hearing], None]) -> None:
        import sherpa_onnx
        from dictate.asr.models import vad_model_path
        from dictate.asr.whisper import WhisperEngine
        from dictate.config import load_config

        cfg = load_config()
        self._whisper = WhisperEngine(model_name=cfg.whisper_model, device=cfg.whisper_device,
                                      compute_type=cfg.whisper_compute_type, language="sk")
        self._whisper.load()
        vad_cfg = sherpa_onnx.VadModelConfig(
            silero_vad=sherpa_onnx.SileroVadModelConfig(
                # 0.6 s of silence ended an utterance; 0.4 s answers sooner and still keeps
                # a normal pause inside a sentence.
                model=str(vad_model_path()), threshold=0.5, min_silence_duration=0.4,
                min_speech_duration=0.25, max_speech_duration=20),
            sample_rate=RATE, num_threads=1, provider="cpu")
        self._vad = sherpa_onnx.VoiceActivityDetector(vad_cfg, buffer_size_in_seconds=60)
        self._device = self._pick_device(cfg.microphone)
        self._on_utterance = on_utterance
        self._on_level = on_level
        self._on_hearing = on_hearing
        self.muted = False          # True while Yuki speaks, so she does not hear herself
        self._energies: deque[float] = deque(maxlen=int(4 / BLOCK_S))
        self._pending = np.zeros(0, dtype=np.float32)
        self._jobs: deque[tuple[np.ndarray, float]] = deque()
        self._wake = threading.Event()
        threading.Thread(target=self._transcribe_loop, daemon=True, name="whisper").start()
        threading.Thread(target=self._music_loop, daemon=True, name="music").start()

    @staticmethod
    def _pick_device(configured):
        """Use dictate's microphone only when it is stored by name; otherwise the Windows default.

        dictate's config held the index 3, which on 2026-11-13 pointed at the Oculus virtual
        headset microphone instead of the HyperX Quadcast: indexes move when devices come and
        go, so Yuki heard nothing.
        """
        # The owner's microphone, 2026-11-13: the HyperX Quadcast.
        for i, d in enumerate(sd.query_devices()):
            if d["max_input_channels"] > 0 and "hyperx" in d["name"].lower():
                return i
        if configured is None or isinstance(configured, int):
            return None
        for i, d in enumerate(sd.query_devices()):
            if d["max_input_channels"] > 0 and str(configured).lower() in d["name"].lower():
                return i
        return None

    def start(self) -> None:
        info = sd.query_devices(self._device, "input")
        native = int(info["default_samplerate"])
        self._native = native
        self._stream = sd.InputStream(device=self._device, channels=1, samplerate=native,
                                      blocksize=int(native * BLOCK_S), dtype="float32",
                                      callback=self._callback)
        self._stream.start()
        log.info("Listening on %s at %d Hz", info["name"], native)

    def _callback(self, indata, frames, time_info, status) -> None:
        from dictate.audio.resample import resample

        mono = indata[:, 0].copy()
        audio = mono if self._native == RATE else resample(mono, self._native, RATE)
        rms = float(np.sqrt(np.mean(audio ** 2))) if audio.size else 0.0
        self._energies.append(rms)
        level = min(1.0, max(0.0, (20 * np.log10(max(rms, 1e-6)) + 50) / 40))
        self._on_level(level)
        if self.muted:
            return
        self._pending = np.concatenate([self._pending, audio])
        while self._pending.size >= 512:
            self._vad.accept_waveform(self._pending[:512])
            self._pending = self._pending[512:]
        while not self._vad.empty():
            seg = np.array(self._vad.front.samples, dtype=np.float32)
            self._vad.pop()
            self._jobs.append((seg, time.perf_counter()))
            self._wake.set()

    def _transcribe_loop(self) -> None:
        while True:
            self._wake.wait()
            self._wake.clear()
            while self._jobs:
                seg, t_end = self._jobs.popleft()
                try:
                    text = self._whisper.transcribe(seg, RATE).text.strip()
                except Exception:
                    log.exception("Whisper failed")
                    continue
                if text:
                    self._on_utterance(text, t_end, time.perf_counter() - t_end)

    def _music_loop(self) -> None:
        """Every 0.5 s: loudness and the onset autocorrelation over the last 4 s.

        The thresholds (-42 dB, beat 0.25) are the same first guesses as on the phone; the
        window shows the measured values so they can be tuned.
        """
        rate = 1 / BLOCK_S   # envelope frames per second
        stop = threading.Event()
        while not stop.wait(0.5):
            e = np.array(self._energies, dtype=np.float64)
            if e.size < int(rate * 3):
                continue
            db = 20 * np.log10(max(e.mean(), 1e-7))
            onset = np.maximum(0, np.diff(e))
            onset -= onset.mean()
            zero = float(np.dot(onset, onset))
            if zero <= 0:
                continue
            lo, hi = int(rate * 60 / 180), int(rate * 60 / 60)
            best, best_lag = 0.0, 0
            for lag in range(lo, min(hi, onset.size - 1) + 1):
                r = float(np.dot(onset[lag:], onset[:-lag])) / zero
                if r > best:
                    best, best_lag = r, lag
            bpm = 60 * rate / best_lag if best_lag else 0.0
            self._on_hearing(Hearing(db > -42 and best > 0.25, bpm, db, best))

"""Yuki's voice: Piper with the Slovak voice Lili, local on the CPU, one sentence at a time.

Measured 2026-11-13 on this PC: 57 characters synthesize in 0.14 s for 3.9 s of audio,
so a sentence is ready long before the previous one finishes playing.
"""

from __future__ import annotations

import os
import queue
import threading
from collections.abc import Callable
from pathlib import Path

import numpy as np
import sounddevice as sd

VOICE = Path(os.path.expandvars(r"%LOCALAPPDATA%\HoloDesk\voices\sk_SK-lili-medium.onnx"))


class Voice:
    def __init__(self, on_start: Callable[[], None], on_idle: Callable[[], None]) -> None:
        from piper import PiperVoice
        from piper.config import SynthesisConfig

        self._voice = PiperVoice.load(VOICE)
        # A touch faster and livelier than the defaults (noise 0.5 / 0.333, scale 1.0).
        self._config = SynthesisConfig(length_scale=0.92, noise_scale=0.6, noise_w_scale=0.5)
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._on_start = on_start
        self._on_idle = on_idle
        self._generation = 0
        self._busy = False
        # One stream kept open: sd.play() opened a new device stream for every sentence.
        self._stream = sd.OutputStream(samplerate=self._voice.config.sample_rate, channels=1,
                                       dtype="float32", latency="low")
        self._stream.start()
        threading.Thread(target=self._run, daemon=True, name="voice").start()

    @property
    def busy(self) -> bool:
        return self._busy or not self._queue.empty()

    def say(self, sentence: str) -> None:
        sentence = sentence.strip()
        if sentence:
            self._queue.put(sentence)

    def stop(self) -> None:
        self._generation += 1
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

    def _run(self) -> None:
        block = int(self._voice.config.sample_rate * 0.05)
        while True:
            text = self._queue.get()
            if text is None:
                return
            gen = self._generation
            for chunk in self._voice.synthesize(text, syn_config=self._config):
                audio = chunk.audio_float_array.astype(np.float32)
                if not self._busy:
                    self._busy = True
                    self._on_start()
                # Written in 50 ms blocks, so stop() cuts the voice within one block.
                for i in range(0, audio.size, block):
                    if gen != self._generation:
                        break
                    self._stream.write(audio[i:i + block].reshape(-1, 1))
                if gen != self._generation:
                    break
            if self._queue.empty():
                self._busy = False
                self._on_idle()

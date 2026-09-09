"""Microphone recording with sounddevice.

Captures audio at 16 kHz mono float32. Supports device selection by
index or by substring of the device name.
"""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "float32"


@dataclass
class AudioChunk:
    """A chunk of audio with its sample rate."""

    samples: np.ndarray
    sample_rate: int


class Recorder:
    """Record microphone audio into a ring buffer.

    The recorder runs a background sounddevice stream. Callers read
    accumulated audio with :meth:`drain`.
    """

    def __init__(
        self,
        sample_rate: int = SAMPLE_RATE,
        channels: int = CHANNELS,
        device: str | int | None = None,
        blocksize: int = 1024,
    ) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self.device = device
        self.blocksize = blocksize
        self._queue: queue.Queue[np.ndarray] = queue.Queue()
        self._stream: sd.InputStream | None = None
        self._lock = threading.Lock()

    def _callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: object,
        status: sd.CallbackFlags,
    ) -> None:
        del frames, time_info
        if status:
            # Logging is not available here; surface the status via the queue.
            pass
        # indata is (frames, channels). Copy so the buffer is not reused.
        self._queue.put(indata[:, 0].copy())

    def start(self) -> None:
        """Open the input stream and start recording."""
        with self._lock:
            if self._stream is not None:
                return
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=DTYPE,
                device=self.device,
                blocksize=self.blocksize,
                callback=self._callback,
            )
            self._stream.start()

    def stop(self) -> None:
        """Stop and close the input stream."""
        with self._lock:
            if self._stream is None:
                return
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def drain(self) -> np.ndarray:
        """Return all queued audio as a single 1-D float32 array."""
        chunks: list[np.ndarray] = []
        while True:
            try:
                chunks.append(self._queue.get_nowait())
            except queue.Empty:
                break
        if not chunks:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(chunks)

    def record(self, seconds: float) -> np.ndarray:
        """Record for ``seconds`` and return the audio.

        Convenience method for CLI use. Starts the stream, waits, stops,
        and returns the captured audio.
        """
        self.start()
        try:
            time.sleep(seconds)
            return self.drain()
        finally:
            self.stop()


def resolve_device(device: str | int | None) -> str | int | None:
    """Resolve a device specifier to a sounddevice device id.

    ``None`` returns the default input device. An integer is returned
    unchanged. A string is matched case-insensitively as a substring of
    the device name; the first match wins.
    """
    if device is None or isinstance(device, int):
        return device
    devices = sd.query_devices()
    needle = device.lower()
    for index, dev in enumerate(devices):
        if dev["max_input_channels"] > 0 and needle in dev["name"].lower():
            return index
    raise ValueError(f"No input device matches {device!r}")

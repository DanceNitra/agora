"""Microphone recording with sounddevice.

Records at the device's native sample rate; sherpa-onnx resamples
internally, so no manual resampling is needed.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from dataclasses import dataclass

import numpy as np
import sounddevice as sd

logger = logging.getLogger(__name__)

CHANNELS = 1
DTYPE = "float32"


@dataclass
class AudioChunk:
    """A chunk of audio with its sample rate."""

    samples: np.ndarray
    sample_rate: int


class Recorder:
    """Record microphone audio into a queue.

    The recorder runs a background sounddevice stream at the device's
    native sample rate. Callers read accumulated audio with
    :meth:`drain`.
    """

    def __init__(
        self,
        sample_rate: int | None = None,
        channels: int = CHANNELS,
        device: str | int | None = None,
        blocksize: int = 0,
    ) -> None:
        self.requested_rate = sample_rate
        self.channels = channels
        self.device = device
        self.blocksize = blocksize
        self._queue: queue.Queue[np.ndarray] = queue.Queue()
        self._stream: sd.InputStream | None = None
        self._lock = threading.Lock()
        self._native_rate = self._query_native_rate()

    def _query_native_rate(self) -> int:
        """Return the device's default input sample rate."""
        if self.device is None:
            info = sd.query_devices(kind="input")
        else:
            info = sd.query_devices(self.device)
        rate = int(info["default_samplerate"])
        logger.info("Device %s native sample rate: %d Hz", info["name"], rate)
        return rate

    @property
    def sample_rate(self) -> int:
        """The sample rate of recorded audio."""
        return self._native_rate

    def _callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: object,
        status: sd.CallbackFlags,
    ) -> None:
        del frames, time_info
        if status:
            logger.warning("Audio callback status: %s", status)
        self._queue.put(indata[:, 0].copy())

    def start(self) -> None:
        """Open the input stream and start recording."""
        with self._lock:
            if self._stream is not None:
                return
            self._stream = sd.InputStream(
                samplerate=self._native_rate,
                channels=self.channels,
                dtype=DTYPE,
                device=self.device,
                blocksize=self.blocksize,
                callback=self._callback,
            )
            self._stream.start()
            logger.info("Recording started: device=%s rate=%d", self.device, self._native_rate)

    def stop(self) -> None:
        """Stop and close the input stream."""
        with self._lock:
            if self._stream is None:
                return
            self._stream.stop()
            self._stream.close()
            self._stream = None
            logger.info("Recording stopped")

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
        """Record for ``seconds`` and return the audio."""
        self.start()
        try:
            time.sleep(seconds)
            return self.drain()
        finally:
            self.stop()

    def record_with_meter(self, seconds: float, width: int = 48) -> np.ndarray:
        """Record for ``seconds`` while printing a live level bar.

        Returns the full recording. The bar shows the peak level of the
        last 100 ms so the speaker can see the microphone is listening.
        """
        self.start()
        chunks: list[np.ndarray] = []
        start = time.perf_counter()
        try:
            while time.perf_counter() - start < seconds:
                time.sleep(0.1)
                got = self.drain()
                if got.size:
                    chunks.append(got)
                    peak = float(np.max(np.abs(got)))
                    filled = int(width * min(1.0, peak * 5.0))
                    bar = "#" * filled + "." * (width - filled)
                    print(f"\r  [{bar}] {peak:.3f}", end="", flush=True)
            got = self.drain()
            if got.size:
                chunks.append(got)
        finally:
            self.stop()
        print()
        if not chunks:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(chunks)


def resolve_device(device: str | int | None) -> str | int | None:
    """Resolve a device specifier to a sounddevice device id.

    ``None`` returns the default input device. An integer is returned
    unchanged. A string is matched case-insensitively as a substring of
    the device name; the first match wins. A string that matches nothing
    logs a warning and returns ``None``, so a missing microphone degrades
    to the system default instead of stopping the app.
    """
    if device is None or isinstance(device, int):
        return device
    devices = sd.query_devices()
    needle = device.lower()
    for index, dev in enumerate(devices):
        if dev["max_input_channels"] > 0 and needle in dev["name"].lower():
            return index
    # The configured microphone is not plugged in, or Windows renamed it. Fall
    # back to the system default so dictation still works, and say so: a wrong
    # microphone records silence, which is indistinguishable from a quiet room.
    logger.warning(
        "Configured microphone %r is not present; falling back to the system default. "
        "Run the setup wizard to pick it again.",
        device,
    )
    return None

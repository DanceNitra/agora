"""Application orchestration: hotkey/button -> recorder -> VAD -> engine -> cursor.

State machine: IDLE -> RECORDING (hotkey down) -> TRANSCRIBING (hotkey
up) -> INJECTING -> IDLE. Recording shorter than 300 ms is discarded;
silence-only takes are discarded via the VAD. State listeners receive
every transition (tray icon, desktop overlay).
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable

import numpy as np

from .asr.factory import build_engine
from .audio.recorder import Recorder
from .audio.vad import SileroVAD
from .config import DictateConfig, load_config
from .feedback import beep_error, beep_start, beep_stop
from .hotkey import HotkeyListener
from .inject import focus
from .inject.base import TextInjector
from .inject.clipboard import ClipboardInjector

logger = logging.getLogger(__name__)

IDLE = "IDLE"
RECORDING = "RECORDING"
TRANSCRIBING = "TRANSCRIBING"
INJECTING = "INJECTING"


def _envelope(chunk: np.ndarray, points: int = 8) -> list[float]:
    """Downsample a chunk to per-slice peak values for the oscilloscope."""
    if chunk.size == 0:
        return [0.0] * points
    size = chunk.size // points
    if size == 0:
        size = 1
    trimmed = chunk[: size * points]
    return [
        float(np.max(np.abs(part))) for part in np.split(trimmed, points)
    ]


class _LiveCapture:
    """Drain the recorder on a timer, keep the buffer, report levels."""

    def __init__(
        self,
        recorder: Recorder,
        on_level: Callable[[float], None],
        on_wave: Callable[[list[float]], None] | None = None,
        envelope_points: int = 8,
        poll_s: float = 0.05,
    ) -> None:
        self.recorder = recorder
        self.on_level = on_level
        self.on_wave = on_wave
        self.envelope_points = envelope_points
        self.poll_s = poll_s
        self._chunks: list[np.ndarray] = []
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self.last_external = 0
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def _loop(self) -> None:
        while not self._stop.is_set():
            got = self.recorder.drain()
            if got.size:
                with self._lock:
                    self._chunks.append(got)
                peak = float(np.max(np.abs(got)))
                try:
                    self.on_level(peak)
                except Exception:
                    logger.debug("level callback failed", exc_info=True)
                if self.on_wave is not None:
                    try:
                        self.on_wave(_envelope(got, self.envelope_points))
                    except Exception:
                        logger.debug("wave callback failed", exc_info=True)
            hwnd = focus.get_foreground_window()
            if focus.is_external_window(hwnd):
                self.last_external = hwnd
            self._stop.wait(self.poll_s)

    def collect(self) -> np.ndarray:
        """Stop capturing and return everything recorded so far."""
        self._stop.set()
        self._thread.join(timeout=1.5)
        got = self.recorder.drain()
        if got.size:
            with self._lock:
                self._chunks.append(got)
        with self._lock:
            chunks = list(self._chunks)
            self._chunks.clear()
        if not chunks:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(chunks)


class DictationApp:
    """Run the dictation state machine driven by a global hotkey."""

    def __init__(self, config: DictateConfig) -> None:
        self.config = config
        self.state = IDLE
        self._lock = threading.RLock()  # reentrant: handlers nest calls
        self._recorder: Recorder | None = None
        self._capture: _LiveCapture | None = None
        self._record_started = 0.0
        self._target_hwnd = 0
        self._target_process = ""
        self._engine = None
        self._vad: SileroVAD | None = None
        self._pipeline_running = False
        self._hotkey: HotkeyListener | None = None
        self._listeners: list[Callable[[str], None]] = []
        self._level_listeners: list[Callable[[float], None]] = []
        self._wave_listeners: list[Callable[[list[float]], None]] = []
        self._transcript_listeners: list[Callable[[str], None]] = []
        self._target_provider: Callable[[], int] | None = None
        self.on_text = self._inject_text

    # -- listeners ---------------------------------------------------------

    def add_state_listener(self, listener: Callable[[str], None]) -> None:
        """Register a callback for state transitions."""
        self._listeners.append(listener)

    def add_level_listener(self, listener: Callable[[float], None]) -> None:
        """Register a callback for live microphone levels."""
        self._level_listeners.append(listener)

    def add_wave_listener(self, listener: Callable[[list[float]], None]) -> None:
        """Register a callback for waveform envelope batches."""
        self._wave_listeners.append(listener)

    def add_transcript_listener(self, listener: Callable[[str], None]) -> None:
        """Register a callback that receives every final transcript."""
        self._transcript_listeners.append(listener)

    def set_target_provider(self, provider: Callable[[], int]) -> None:
        """Provide the paste-target hwnd, resolved when recording starts."""
        self._target_provider = provider

    def _set_state(self, state: str) -> None:
        with self._lock:
            self.state = state
        logger.info("State -> %s", state)
        for listener in list(self._listeners):
            try:
                listener(state)
            except Exception:
                logger.warning("State listener failed", exc_info=True)

    # -- public API --------------------------------------------------------

    def start_hotkey(self) -> None:
        """Start the global hotkey listener."""
        self._hotkey = HotkeyListener(
            combo=self.config.hotkey,
            mode=self.config.hotkey_mode,
            on_activate=self._start_recording,
            on_deactivate=self._stop_recording,
        )
        self._hotkey.start()

    def toggle_recording(self) -> None:
        """Start or stop recording (tray button / toggle mode)."""
        with self._lock:
            state = self.state
        if state == RECORDING:
            self._stop_recording()
        else:
            self._start_recording()

    def reload_config(self) -> None:
        """Reload settings from disk and restart the hotkey listener."""
        self.config = load_config()
        if self._hotkey is not None:
            self._hotkey.stop()
            self.start_hotkey()
        logger.info("Config reloaded")

    def run_forever(self, stop_event: threading.Event) -> None:
        """Load the engine, start the hotkey, and block until ``stop_event``."""
        self._load_engine()
        self.start_hotkey()
        while not stop_event.wait(0.5):
            pass
        self.stop()

    def stop(self) -> None:
        """Stop the hotkey listener."""
        if self._hotkey is not None:
            self._hotkey.stop()
            self._hotkey = None

    # -- recording ---------------------------------------------------------

    def _start_recording(self) -> None:
        with self._lock:
            if self.state != IDLE or self._pipeline_running:
                logger.info("Start ignored: state=%s", self.state)
                return
            self._set_state(RECORDING)
            self._record_started = time.perf_counter()
            if self._target_provider is not None:
                self._target_hwnd = self._target_provider()
            else:
                self._target_hwnd = focus.get_foreground_window()
            self._target_process = focus.process_name(self._target_hwnd)
            logger.info("Paste target: hwnd=%s process=%s", self._target_hwnd, self._target_process)
            self._recorder = Recorder(device=self.config.microphone)
            try:
                self._recorder.start()
            except Exception:
                logger.exception("Could not open the microphone")
                self._recorder = None
                self._set_state(IDLE)
                self._beep("error")
                return
            self._capture = _LiveCapture(
                self._recorder, self._notify_level, self._notify_wave
            )
            self._capture.start()
            self._beep("start")

    def _stop_recording(self) -> None:
        with self._lock:
            if self.state != RECORDING or self._recorder is None:
                logger.info("Stop ignored: state=%s", self.state)
                return
            elapsed_ms = (time.perf_counter() - self._record_started) * 1000
            sample_rate = self._recorder.sample_rate
            recorder = self._recorder
            capture = self._capture
            self._capture = None
            self._recorder = None
            self._set_state(TRANSCRIBING)
            self._beep("stop")

        if elapsed_ms < 300 or audio_size(capture) == 0:
            recorder.stop()
            self._set_state(IDLE)
            self._beep("error")
            return

        audio = capture.collect()
        recorder.stop()
        if capture.last_external:
            self._target_hwnd = capture.last_external
            self._target_process = focus.process_name(self._target_hwnd)
        if audio.size == 0:
            self._set_state(IDLE)
            self._beep("error")
            return

        thread = threading.Thread(
            target=self._run_pipeline,
            args=(audio, sample_rate),
            daemon=True,
        )
        thread.start()

    def _run_pipeline(self, audio: np.ndarray, sample_rate: int) -> None:
        self._pipeline_running = True
        try:
            if self.config.vad_enabled:
                vad = self._vad_engine()
                trimmed = vad.trim(audio, sample_rate, preroll_ms=self.config.preroll_ms)
                logger.info(
                    "VAD kept %.2f s of %.2f s",
                    trimmed.size / 16000,
                    audio.size / sample_rate,
                )
            else:
                from .audio.resample import resample

                trimmed = resample(audio, sample_rate, 16000)
            if trimmed.size == 0:
                self._beep("error")
                return

            self._set_state(INJECTING)
            engine = self._load_engine()
            result = engine.transcribe(trimmed, 16000, language=self.config.language)
            logger.info("Transcript: %r", result.text)
            if not result.text:
                self._beep("error")
            else:
                self.on_text(result.text)
                for callback in list(self._transcript_listeners):
                    try:
                        callback(result.text)
                    except Exception:
                        logger.debug("transcript listener failed", exc_info=True)
        except Exception:
            logger.exception("Pipeline failed")
            self._beep("error")
        finally:
            self._pipeline_running = False
            self._set_state(IDLE)

    # -- helpers -----------------------------------------------------------

    def _notify_level(self, peak: float) -> None:
        for callback in list(self._level_listeners):
            try:
                callback(peak)
            except Exception:
                logger.debug("level listener failed", exc_info=True)

    def _notify_wave(self, envelope: list[float]) -> None:
        for callback in list(self._wave_listeners):
            try:
                callback(envelope)
            except Exception:
                logger.debug("wave listener failed", exc_info=True)

    def _beep(self, kind: str) -> None:
        enabled = self.config.feedback_sound
        if kind == "start":
            beep_start(enabled)
        elif kind == "stop":
            beep_stop(enabled)
        else:
            beep_error(enabled)

    def _inject_text(self, text: str) -> None:
        try:
            logger.info(
                "Injecting %r to hwnd=%s process=%s",
                text,
                self._target_hwnd,
                self._target_process,
            )
            injector = self._injector_for(self._target_process)
            injector.insert(text, self._target_hwnd)
            logger.info("Injection done")
        except Exception:
            logger.exception("Injection failed")

    def _injector_for(self, process: str) -> TextInjector:
        """Build the injector honouring per-app overrides."""
        override = self.config.app_overrides.get(process, {})
        mode = override.get("insert_mode", self.config.insert_mode)
        if mode == "sendinput":
            from .inject.sendinput import SendInputInjector

            return SendInputInjector(
                delay_ms=self.config.typing_delay_ms,
                prefix_space=self.config.prefix_space,
            )
        return ClipboardInjector(
            paste_shortcut=override.get("paste_shortcut", self.config.paste_shortcut),
            restore_delay_ms=self.config.clipboard_restore_delay_ms,
            refocus_original_window=self.config.refocus_original_window,
            prefix_space=self.config.prefix_space,
        )

    def _vad_engine(self) -> SileroVAD:
        if self._vad is None:
            self._vad = SileroVAD()
        return self._vad

    def _load_engine(self):
        if self._engine is None:
            self._engine = build_engine(self.config)
            self._engine.load()
        return self._engine


def audio_size(capture: _LiveCapture | None) -> int:
    """Best-effort byte count of captured audio for the discard check."""
    if capture is None:
        return 0
    with capture._lock:
        return sum(chunk.size for chunk in capture._chunks)



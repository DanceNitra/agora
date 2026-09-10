"""CLI helpers: test-mic, transcribe, download-model, and interactive listen."""

from __future__ import annotations

import logging
import time
import wave
from pathlib import Path

import numpy as np

from .asr.models import download_model as _download_model
from .asr.factory import build_engine
from .audio.recorder import Recorder, resolve_device
from .audio.wav import write_wav
from .config import DictateConfig, load_config, save_config

logger = logging.getLogger(__name__)


def _load(config_path: Path | None) -> DictateConfig:
    return load_config(config_path)


def _beep(frequency: int = 1100, duration_ms: int = 120) -> None:
    import winsound

    winsound.Beep(frequency, duration_ms)


def _read_wav(path: Path) -> tuple[np.ndarray, int]:
    """Read a mono 16-bit wav file and return (float32 samples, sample_rate)."""
    with wave.open(str(path), "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_rate = wav_file.getframerate()
        raw = wav_file.readframes(wav_file.getnframes())
    pcm = np.frombuffer(raw, dtype=np.int16)
    if channels > 1:
        pcm = pcm.reshape(-1, channels)[:, 0]
    return pcm.astype(np.float32) / 32767.0, sample_rate


def _unmute_all_capture_endpoints() -> None:
    """Best-effort: unmute every capture endpoint and raise its level to 100%."""
    try:
        from comtypes import CLSCTX_ALL
        from pycaw.constants import DEVICE_STATE, EDataFlow
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

        enum = AudioUtilities.GetDeviceEnumerator()
        collection = enum.EnumAudioEndpoints(EDataFlow.eCapture.value, DEVICE_STATE.ACTIVE.value)
        for i in range(collection.GetCount()):
            dev = collection.Item(i)
            iface = dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            vol = iface.QueryInterface(IAudioEndpointVolume)
            if vol.GetMute():
                vol.SetMute(0, None)
                print(f"  unmuted capture endpoint {i}")
            if vol.GetMasterVolumeLevelScalar() < 0.99:
                vol.SetMasterVolumeLevelScalar(1.0, None)
    except Exception as exc:  # pragma: no cover - optional dependency
        logger.warning("Could not adjust capture endpoints: %s", exc)


def _probe_devices(speak_seconds: float = 2.0) -> int | None:
    """Sample candidate microphones while the user speaks; return the best index.

    Candidates are the system default input plus every device whose name
    contains HyperX or Quadcast. Each candidate is recorded for
    ``speak_seconds``; the device with the highest peak wins.
    """
    import sounddevice as sd

    candidates: dict[tuple[str, str], int] = {}
    default_index = sd.default.device[0]
    if default_index >= 0:
        info = sd.query_devices(default_index)
        host = sd.query_hostapis(info["hostapi"])["name"]
        candidates[(info["name"], host)] = default_index
    for index, dev in enumerate(sd.query_devices()):
        if dev["max_input_channels"] <= 0:
            continue
        name = dev["name"].lower()
        if "hyperx" in name or "quadcast" in name:
            host = sd.query_hostapis(dev["hostapi"])["name"]
            candidates.setdefault((dev["name"], host), index)

    best_index: int | None = None
    best_peak = 0.0
    for (name, host), index in sorted(candidates.items(), key=lambda item: item[1]):
        print(f"\n  >>> device {index} [{host}] {name} -- TALK <<<")
        _beep(880, 100)
        time.sleep(0.05)
        _beep(880, 100)
        try:
            recorder = Recorder(device=index)
            audio = recorder.record_with_meter(speak_seconds)
        except Exception as exc:
            print(f"    open failed: {exc}")
            continue
        peak = float(np.max(np.abs(audio))) if audio.size else 0.0
        print(f"    peak {peak:.4f}")
        if peak > best_peak:
            best_peak = peak
            best_index = index
    print(f"\n  Best device: {best_index} (peak {best_peak:.4f})")
    return best_index


def test_mic(seconds: int, config_path: Path | None = None) -> int:
    """Record ``seconds`` with beeps and a live meter, then transcribe."""
    config = _load(config_path)
    device = resolve_device(config.microphone)
    recorder = Recorder(device=device)
    print(f"REC device={device} rate={recorder.sample_rate} seconds={seconds}")
    _beep(1100, 120)
    time.sleep(0.05)
    _beep(1100, 120)
    time.sleep(0.05)
    _beep(1100, 120)
    audio = recorder.record_with_meter(float(seconds))
    _beep(1500, 400)

    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    print(f"  peak={peak:.4f} samples={len(audio)} rate={recorder.sample_rate}")
    if peak < 0.005:
        print("  WARNING: near-silent recording.")
        return 1

    out_path = Path("test_mic.wav")
    write_wav(out_path, audio, recorder.sample_rate)
    engine = build_engine(config)
    result = engine.transcribe(audio, recorder.sample_rate, language=config.language)
    print(f"  load={result.load_seconds:.2f}s rtf={result.rtf:.3f}")
    print(f"  TEXT: {result.text}")
    return 0


def listen(
    takes: int,
    seconds: int = 6,
    probe: bool | None = None,
    config_path: Path | None = None,
) -> int:
    """Interactive session: probe microphones, then record and transcribe takes.

    The user hears beeps that mark each phase: two beeps start a device
    scan, three beeps start a recording take, and a long beep stops it.
    """
    config = _load(config_path)
    engine = build_engine(config)
    engine.load()

    do_probe = probe if probe is not None else config.microphone is None
    best = config.microphone if isinstance(config.microphone, int) else None
    if do_probe:
        print("\n=== PROBE: keep talking until the final long beep ===")
        _unmute_all_capture_endpoints()
        _beep(880, 150)
        time.sleep(3.0)  # time to focus this window
        best = _probe_devices(2.0)
        if best is None:
            print("No microphone produced a signal.")
            return 1
        config.microphone = best
        save_config(config, config_path)

    transcripts: list[str] = []
    recorder = Recorder(device=best)
    for take in range(1, takes + 1):
        print(f"\n=== TAKE {take}/{takes} — speak for {seconds} s ===")
        for _ in range(3):
            _beep(1100, 120)
            time.sleep(0.08)
        audio = recorder.record_with_meter(float(seconds))
        _beep(1500, 400)

        peak = float(np.max(np.abs(audio))) if audio.size else 0.0
        if peak < 0.01:
            print("  (silent take, skipped)")
            continue
        wav_path = Path(f"take{take}.wav")
        write_wav(wav_path, audio, recorder.sample_rate)
        result = engine.transcribe(audio, recorder.sample_rate, language=config.language)
        line = f"take{take} peak={peak:.3f} rtf={result.rtf:.3f} TEXT: {result.text}"
        print(f"  {line}")
        transcripts.append(line)

    Path("transcript.txt").write_text("\n".join(transcripts) + "\n", encoding="utf-8")
    print("\nSaved transcript.txt")
    return 0


def transcribe_file(path: Path, config_path: Path | None = None) -> int:
    """Transcribe a wav file and print timing and text."""
    config = _load(config_path)
    audio, sample_rate = _read_wav(path)
    engine = build_engine(config)
    result = engine.transcribe(audio, sample_rate, language=config.language)
    print(
        f"Audio: {result.duration_seconds:.2f} s | Load: {result.load_seconds:.2f} s"
        f" | RTF: {result.rtf:.3f}"
    )
    return 0


def download_model(config_path: Path | None = None) -> int:
    """Download the default ASR model."""
    _load(config_path)

    def _progress(count: int, block_size: int, total_size: int) -> None:
        if total_size <= 0:
            return
        percent = min(100, count * block_size * 100 // total_size)
        print(f"\rDownloading... {percent}%", end="", flush=True)

    directory = _download_model(progress_callback=_progress)
    print(f"\nModel installed at {directory}")
    return 0




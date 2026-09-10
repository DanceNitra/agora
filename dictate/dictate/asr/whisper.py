"""faster-whisper ASR engine (CUDA, int8_float16 by default).

Whisper forces the language explicitly, which is why it is the only engine here. The
Parakeet engine this replaced auto-detected Slovak as Polish and wrote Polish
orthography, and no amount of post-processing recovers that.
"""

from __future__ import annotations

import logging
import time

import numpy as np

from .base import ASREngine, TranscriptionResult

logger = logging.getLogger(__name__)


class WhisperEngine(ASREngine):
    """Offline faster-whisper engine with CUDA support and language forcing."""

    def __init__(
        self,
        model_name: str = "large-v3-turbo",
        device: str = "cuda",
        compute_type: str = "auto",
        language: str | None = "sk",
        num_threads: int = 0,
    ) -> None:
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self.num_threads = num_threads
        self._model = None
        self._load_seconds = 0.0

    def _model_source(self) -> str:
        """Return the installed model directory, or the alias when nothing is installed.

        The installer downloads the weights into the app's own models directory, so a
        machine that never ran faster-whisper before still starts offline. Falling back
        to the alias keeps a development checkout working against the Hugging Face cache.
        """
        from .models import is_model_installed, model_dir

        if is_model_installed():
            return str(model_dir())
        logger.info("No installed weights; falling back to the alias %s", self.model_name)
        return self.model_name

    # Best first. int8_float16 is the fastest on a card with real fp16 throughput; a
    # Pascal card such as the GTX 1080 has fp16 at a sixty-fourth of fp32, so CTranslate2
    # refuses it outright and int8_float32 is the right choice there.
    COMPUTE_PREFERENCE = ("int8_float16", "int8_bfloat16", "int8_float32", "int8",
                          "float16", "float32")

    def _resolve_compute_type(self) -> str:
        """Return a compute type this device actually supports.

        MEASURED on a GTX 1080: a hardcoded int8_float16 raised "Requested int8_float16
        compute type, but the target device or backend do not support efficient
        int8_float16 computation" and the setup stopped after the whole model had
        downloaded. Asking CTranslate2 what the card supports costs one call.
        """
        if self.compute_type and self.compute_type != "auto":
            return self.compute_type
        try:
            import ctranslate2

            supported = set(ctranslate2.get_supported_compute_types(self.device))
        except Exception:
            logger.debug("Could not read the supported compute types", exc_info=True)
            return "int8"
        for candidate in self.COMPUTE_PREFERENCE:
            if candidate in supported:
                logger.info("Compute type %s, chosen from %s",
                            candidate, sorted(supported))
                return candidate
        return "int8"

    def load(self) -> None:
        """Load the model (downloads on first run)."""
        from faster_whisper import WhisperModel

        compute_type = self._resolve_compute_type()
        start = time.perf_counter()
        self._model = WhisperModel(
            self._model_source(),
            device=self.device,
            compute_type=compute_type,
        )
        self.compute_type = compute_type
        self._load_seconds = time.perf_counter() - start
        self._refuse_a_silent_cpu_fallback()
        logger.info(
            "Loaded whisper %s device=%s in %.2f s",
            self.model_name,
            self.device,
            self._load_seconds,
        )

    def _refuse_a_silent_cpu_fallback(self) -> None:
        """Fail loudly when CUDA was asked for and CPU was given.

        CTranslate2 does not raise when it cannot reach the GPU: it loads on the CPU and
        keeps going. A transcript that arrives normally but came from the wrong device is
        the worst failure this app has, because the user only finds out by reading it.
        """
        if self.device != "cuda":
            return
        actual = getattr(getattr(self._model, "model", None), "device", None)
        if actual is not None and str(actual).lower().startswith("cpu"):
            self._model = None
            raise RuntimeError(
                "Whisper fell back to the CPU, so the GPU is not reachable. Check that "
                "the NVIDIA driver is installed and that nvidia-smi lists the card.")

    def transcribe(
        self,
        audio: np.ndarray,
        sample_rate: int,
        language: str | None = None,
    ) -> TranscriptionResult:
        """Transcribe 16 kHz float32 audio; language is forced when set."""
        if self._model is None:
            self.load()

        if audio.ndim != 1:
            raise ValueError(f"Expected 1-D audio, got shape {audio.shape}")
        duration = len(audio) / sample_rate
        if audio.size == 0 or duration < 0.1:
            return TranscriptionResult(
                text="",
                duration_seconds=duration,
                load_seconds=self._load_seconds,
                transcribe_seconds=0.0,
            )


        audio_16k = audio if sample_rate == 16000 else _resample(audio, sample_rate)

        start = time.perf_counter()
        segments, info = self._model.transcribe(
            audio_16k,
            language=language or self.language,
            beam_size=1,
            # The app trims silence with Silero through sherpa-onnx before the audio ever
            # reaches this call, so faster-whisper's own VAD would run the same model a
            # second time and pull a second onnxruntime into the build.
            vad_filter=False,
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()
        transcribe_seconds = time.perf_counter() - start

        logger.info(
            "Whisper: %.2fs audio in %.2fs (%.3f RTF), lang=%s prob=%.2f",
            duration,
            transcribe_seconds,
            transcribe_seconds / max(duration, 1e-9),
            info.language,
            info.language_probability,
        )
        return TranscriptionResult(
            text=text,
            duration_seconds=duration,
            load_seconds=self._load_seconds,
            transcribe_seconds=transcribe_seconds,
        )


def _resample(audio: np.ndarray, sample_rate: int) -> np.ndarray:
    from ..audio.resample import resample

    return resample(audio, sample_rate, 16000)

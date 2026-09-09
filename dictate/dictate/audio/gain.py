"""Peak normalization for microphone audio."""

from __future__ import annotations

import numpy as np


def normalize(samples: np.ndarray, target_peak: float = 0.9) -> np.ndarray:
    """Scale ``samples`` so the loudest sample reaches ``target_peak``.

    Quiet microphone input improves ASR accuracy after normalization.
    Near-silent audio is left untouched to avoid amplifying pure noise.
    """
    if samples.size == 0:
        return samples
    peak = float(np.max(np.abs(samples)))
    if peak < 0.01 or peak >= target_peak:
        return samples
    return (samples * (target_peak / peak)).astype(np.float32)

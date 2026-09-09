"""Sample-rate conversion with linear interpolation.

Good enough for VAD windows; sherpa-onnx resamples internally for ASR.
"""

from __future__ import annotations

import numpy as np


def resample(samples: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
    """Resample 1-D audio from ``src_rate`` to ``dst_rate`` (linear interp)."""
    if src_rate == dst_rate:
        return samples.astype(np.float32)
    if samples.size == 0:
        return np.zeros(0, dtype=np.float32)
    target_n = int(round(samples.size / src_rate * dst_rate))
    if target_n <= 0:
        return np.zeros(0, dtype=np.float32)
    x_src = np.arange(samples.size, dtype=np.float64) / src_rate
    x_dst = np.arange(target_n, dtype=np.float64) / dst_rate
    return np.interp(x_dst, x_src, samples).astype(np.float32)

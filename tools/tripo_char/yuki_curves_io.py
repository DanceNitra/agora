"""Read the curve dumps of ue_yuki_curves_dump.py as dense arrays: one value per frame at FPS (linear between keys)."""
import json

import numpy as np

FPS = 30.0


def load(stem):
    meta = json.load(open(str(stem) + ".json"))
    raw = np.fromfile(str(stem) + ".f32", dtype=np.float32)
    n = int(round(meta["length"] * FPS)) + 1
    t = np.arange(n) / FPS
    out, p = np.zeros((len(meta["names"]), n), dtype=np.float32), 0
    for i, c in enumerate(meta["counts"]):
        if c:
            out[i] = np.interp(t, raw[p:p + c], raw[p + c:p + 2 * c])
        p += 2 * c
    assert p == len(raw), ("dump length", p, len(raw))
    return meta["names"], out

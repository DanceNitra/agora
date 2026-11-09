import json, sys, numpy as np
sys.path.insert(0, r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit")
from fit_lib import *
ref = json.load(open(F + r"\ref_landmarks.json"))
c0 = np.array(json.load(open(F + r"\coeffs_base.json")))
set_coeffs(c0)
lm0 = track(capture("c_base"), "c_base")
lm0b = track(capture("c_base2"), "c_base2")
keys = sorted(lm0)
print("repeat noise px", round(float(np.abs(flat(lm0b, keys) - flat(lm0, keys)).mean()), 3))
for idx in [12, 20, 30, 100, 300, 700, 1200]:
    for delta in [0.5]:
        c = c0.copy(); c[idx] += delta
        set_coeffs(c)
        lm = track(capture(f"c_{idx}"), f"c_{idx}")
        ok = keys == sorted(lm) and all(len(lm[k]) == len(lm0[k]) for k in keys)
        move = float(np.abs(flat(lm, keys) - flat(lm0, keys)).mean()) if ok else -1
        print("idx", idx, "base", round(float(c0[idx]), 3), "delta", delta, "move px", round(move, 3), "err", round(aligned_error(lm, ref)[0], 3) if ok else None)
set_coeffs(c0)

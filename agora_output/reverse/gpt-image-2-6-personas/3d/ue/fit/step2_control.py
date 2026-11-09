import json, sys, numpy as np
sys.path.insert(0, r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit")
from fit_lib import *
ref = json.load(open(F + r"\ref_landmarks.json"))
c0 = np.array(get_coeffs())
json.dump(c0.tolist(), open(F + r"\coeffs_base.json", "w"))
a = np.abs(c0)
print("abs quantiles", np.round(np.quantile(a, [0, .5, .9, .99, 1]), 3), "n>2:", int((a > 2).sum()), "first 12", np.round(c0[:12], 3))
print("big idx", np.where(a > 5)[0][:20])
lm0 = track(capture("ctl0"), "ctl0")
for idx, delta in [(0, 1.0), (5, 1.0), (40, 1.0)]:
    c = c0.copy(); c[idx] += delta
    set_coeffs(c)
    lm = track(capture(f"ctl_{idx}"), f"ctl_{idx}")
    keys = sorted(set(lm0) & set(lm))
    move = np.abs(flat(lm, keys) - flat(lm0, keys)).mean() if keys and all(len(lm[k]) == len(lm0[k]) for k in keys) else -1
    print("idx", idx, "delta", delta, "mean landmark move px", round(float(move), 3), "err", round(aligned_error(lm, ref)[0], 3))
set_coeffs(c0)

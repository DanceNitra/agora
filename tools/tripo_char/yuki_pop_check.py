"""Find pops in a rendered sequence: frames whose change from the previous frame stands far above the local level.

    python yuki_pop_check.py <frames_dir> [factor]

Each frame is read at 1/8 size in grey; the mean absolute difference to the previous frame is compared with the median
of the 30 frames around it. A ratio above FACTOR (default 4) is listed: a pose jump, a hair burst or a cut reads as one
tall spike, steady motion does not. Prints the worst ten and writes <frames_dir>_pops.json."""
import json
import os
import sys

import numpy as np
from PIL import Image

d = sys.argv[1]
F = float(sys.argv[2]) if len(sys.argv) > 2 else 4.0
fs = sorted(f for f in os.listdir(d) if f.endswith(".png"))
prev, diff = None, []
for i, f in enumerate(fs):
    a = np.asarray(Image.open(os.path.join(d, f)).convert("L").reduce(8), dtype=np.float32)
    diff.append(0.0 if prev is None else float(np.abs(a - prev).mean()))
    prev = a
    if i % 1000 == 0:
        print("frame", i, "of", len(fs), flush=True)
diff = np.array(diff)
med = np.array([np.median(diff[max(1, i - 15):i + 16]) for i in range(len(diff))])
ratio = diff / np.maximum(med, 0.05)
worst = np.argsort(-ratio)[:10]
pops = [int(i) for i in np.nonzero(ratio > F)[0] if i > 0]
json.dump({"diff": diff.round(3).tolist(), "pops": pops}, open(d.rstrip("/\\") + "_pops.json", "w"))
print("POPS over", F, ":", len(pops), "| median change", round(float(np.median(diff)), 3), "| worst (frame, ratio, change):", [(int(i), round(float(ratio[i]), 1), round(float(diff[i]), 2)) for i in worst])

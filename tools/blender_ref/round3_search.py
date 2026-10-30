"""Round 3: try leg parameter sets, render alpha silhouettes, score them against the reference.

python round3_search.py   (prints one line per candidate as it finishes)
The first candidate is the round-2 model rebuilt through build_leg_v3.py; it must reproduce the
round-2 scores, or the search is measuring the builder, not the parameters.
"""
import itertools
import json
import os
import re
import subprocess
import time

BL = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
VENV = r"C:\ComfyUI\venv\Scripts\python.exe"
HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = r"C:\Users\Danculus\agora\agora_output\reverse\blender_spider_xCkjVUtVDEw\build"
BASE = os.path.join(BUILD, "06_blend", "robot_v10_legs_round2b.blend")
OUT = os.path.join(BUILD, "07_iterate", "round3c")

control = dict(H=1.0, S=0.0, ARM_R=0.042, KN_S=1.0, BOW=0.04, GAP=0.006)
grid = [dict(H=h, S=s, B=b, ARM_R=0.055, KN_S=1.25, BOW=0.06, GAP=0.003)
        for h, s, b in itertools.product((0.94,), (0.14,), (1.38, 1.44))]
control = dict(control, B=1.196)


def iou(view, d):
    r = subprocess.run([VENV, "-I", os.path.join(HERE, "silhouette_overlay.py"), os.path.join(BUILD, "03_sheet", f"{view}.png"),
                        os.path.join(d, f"{view}_view.png"), os.path.join(d, f"overlay_{view}.png")], capture_output=True, text=True)
    m = re.search(r"IoU ([\d.]+)\s+ref aspect ([\d.]+)\s+render aspect ([\d.]+)", r.stdout)
    return tuple(float(x) for x in m.groups()) if m else (0.0, 0.0, 0.0)


os.makedirs(OUT, exist_ok=True)
rows = []
t0 = time.time()
for k, p in enumerate([control] + grid):
    d = os.path.join(OUT, f"cand_{k:02d}")
    os.makedirs(d, exist_ok=True)
    blend = os.path.join(d, "cand.blend")
    subprocess.run([BL, "-b", BASE, "-P", os.path.join(HERE, "round3_candidate.py"), "--", json.dumps(p), blend], capture_output=True)
    subprocess.run([BL, "-b", blend, "-P", os.path.join(HERE, "render_stills.py"), "--", d, "32", "front_view,side_view", "mask"], capture_output=True)
    f, s = iou("front", d), iou("side", d)
    row = dict(k=k, params=p, front_iou=f[0], front_aspect=f[2], side_iou=s[0], side_aspect=s[2], mean_iou=round((f[0] + s[0]) / 2, 3))
    rows.append(row)
    print(f"[search] {k + 1}/{len(grid) + 1} {time.time() - t0:.0f}s H={p['H']} S={p['S']} front {f[0]:.3f} (asp {f[2]:.3f}) side {s[0]:.3f} (asp {s[2]:.3f})", flush=True)
with open(os.path.join(OUT, "search.json"), "w") as fh:
    json.dump(rows, fh, indent=1)
best = max(rows[1:], key=lambda r: r["mean_iou"])
print("[search] best", json.dumps(best), flush=True)

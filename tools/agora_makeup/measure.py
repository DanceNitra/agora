"""Measure what a look changes, zone by zone, as Lab deltas (look minus before).

  python measure.py view <look_id> [base_BC.png]                     offline: frontal view of the painted texture
  python measure.py render <before.png> <after.png> <landmarks.json>
                                                          on Unreal renders; landmarks from mp_landmarks.py

The same zone points are used in both modes, so the ratio render/offline per zone is the render transfer,
and a target for the render becomes a target for the offline paint before any render runs.
Points follow the zone definitions in zones.py; every patch is a disc of 0.08 eye widths.
"""
import json
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from agora_makeup import zones as Z  # noqa: E402

# Render targets from the independent audit of round 7 (2026-11-09, section 5), divided by the render transfer
# measured on that round with these same points (render delta / offline delta): blush a* 0.66, under-eye L 0.48,
# cheek hollow L 0.50, forehead and chin L about 0.85, nose bridge b* 1.0. So these are OFFLINE targets.
TARGETS = {
    "blush_high_A": {"da": (6, 10), "db": (-0.5, 3)},        # render a* +4..+7, warm (b* 0..+2)
    "under_eye_A": {"dL": (4, 10), "da": (-1.5, 2)},         # render L +2..+5, no red rim
    "lash_inner_A": {"da": (-4, 2)},                         # no red rim; the white inner corner may cool it
    "cheek_hollow_A": {"dL": (-12, -6)},                     # render L -3..-6
    "forehead": {"dL": (3, 6)},                              # render L +2.5..+5, same on chin and neck
    "chin": {"dL": (3, 6)},
    "neck": {"dL": (3, 6)},
    "nose_bridge": {"db": (-2, 2)},
}


def points(lm):
    P = lambda i: np.asarray(lm[i][:2], np.float64)
    E = Z.EYE["A"]
    up = np.array([P(i) for i in E["upper"]])
    lo = np.array([P(i) for i in E["lower"]])
    out, inn = P(E["outer"]), P(E["inner"])
    ew = float(np.linalg.norm(out - inn))
    brow = np.array([P(i) for i in E["brow_lo"]]).mean(0)
    tb = brow - up.mean(0)
    d = (out - inn) / ew
    a, b = P(E["hollow"][0]), P(E["hollow"][1])
    down = np.array([0.0, 1.0]) * ew
    pts = {
        "blush_high_A": lo.mean(0) - tb * 1.5 + d * ew * 0.25,
        "blush_high_B": None,
        "under_eye_A": lo.mean(0) - tb * 0.35,
        "lash_inner_A": lo[-3] - tb * 0.12,
        "cheek_hollow_A": a + (b - a) * 0.35 - down * 0.4,
        "temple_A": np.array([P(i) for i in E["temple"]]).mean(0),
        "nose_bridge": (P(6) + P(197)) / 2,
        "nose_tip": P(4),
        "forehead": P(151),
        "chin": P(175) * 0.6 + P(199) * 0.4,
        "neck": P(152) + down * 0.9,
        "lip_upper": (P(0) + P(13)) / 2,
        "lip_lower": (P(14) + P(17)) / 2,
        "lip_line_upper": P(0) + (P(0) - P(13)) * 0.12,
    }
    B = Z.EYE["B"]
    lob = np.array([P(i) for i in B["lower"]])
    upb = np.array([P(i) for i in B["upper"]])
    tbb = np.array([P(i) for i in B["brow_lo"]]).mean(0) - upb.mean(0)
    db_ = (P(B["outer"]) - P(B["inner"])) / np.linalg.norm(P(B["outer"]) - P(B["inner"]))
    pts["blush_high_B"] = lob.mean(0) - tbb * 1.5 + db_ * ew * 0.25
    return pts, ew


def lab_at(img, p, r):
    x, y, r = int(round(p[0])), int(round(p[1])), max(2, int(round(r)))
    patch = img[max(0, y - r):y + r + 1, max(0, x - r):x + r + 1]
    yy, xx = np.mgrid[:patch.shape[0], :patch.shape[1]]
    cy, cx = y - max(0, y - r), x - max(0, x - r)
    m = (yy - cy) ** 2 + (xx - cx) ** 2 <= r * r
    lab = cv2.cvtColor(patch, cv2.COLOR_BGR2LAB).astype(np.float32)[m]
    if not len(lab):
        return None
    lab = lab.mean(0)
    return np.array([lab[0] * 100 / 255, lab[1] - 128, lab[2] - 128])


def deltas(before, after, lm):
    pts, ew = points(lm)
    out = {}
    for k, p in pts.items():
        a, b = lab_at(before, p, ew * 0.08), lab_at(after, p, ew * 0.08)
        if a is not None and b is not None:
            out[k] = [round(float(v), 1) for v in (b - a)]
    return out


def verdict(d):
    res = {}
    for k, t in TARGETS.items():
        if k not in d:
            continue
        bad = []
        for ax, (lo, hi) in t.items():
            v = d[k][{"dL": 0, "da": 1, "db": 2}[ax]]
            if not lo <= v <= hi:
                bad.append("%s %.1f not in [%g, %g]" % (ax, v, lo, hi))
        res[k] = "ok" if not bad else "; ".join(bad)
    return res


SAVED = r"C:/Users/Danculus/Desktop/codex/1hra/SFX/MyProject/Saved/AgoraMakeup/MH_DepesaKF/base_BC.png"


def view(look_id, base_path=SAVED):
    import cli
    from agora_makeup import paint
    vm, face = paint.view_face()
    base = cv2.imread(base_path)
    if base is None:
        raise SystemExit("base texture missing: " + base_path)
    kp = os.path.join(os.path.dirname(os.path.abspath(base_path)), "keep_brows.png")
    keep = cv2.imread(kp, cv2.IMREAD_GRAYSCALE) if os.path.exists(kp) else None
    out, _, _ = paint.paint(base, None, cli.find(look_id), keep_brows=keep)
    b, a = vm.frontal(base), vm.frontal(out)
    lm = json.load(open(os.path.join(HERE, "agora_makeup", "data", "view_landmarks.json")))
    return deltas(b, a, lm), (b, a)


if __name__ == "__main__":
    if sys.argv[1] == "view":
        d, _ = view(sys.argv[2], *sys.argv[3:4])
    else:
        lm = json.load(open(sys.argv[4]))
        lm = lm[sys.argv[2]] if sys.argv[2] in lm else list(lm.values())[0]
        d = deltas(cv2.imread(sys.argv[2]), cv2.imread(sys.argv[3]), lm)
    print(json.dumps({"delta_Lab": d, "verdict": verdict(d)}, indent=1))

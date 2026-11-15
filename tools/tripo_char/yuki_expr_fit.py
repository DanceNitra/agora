"""Learns per-channel corrections for Yuki's face from audited runs and applies them to a solved face animation.

    .venv_mp/Scripts/python.exe yuki_expr_fit.py --train sinead_100_60,brel_nmqp --dump <stem> --out <stem>

Training data: perf/<run>/audit.json written by perf_audit.py (MediaPipe on the singer and on Yuki, same frames). For
every ARKit channel the gain is the geometric mean of 1 / amp over the runs where the singer moves it (std >= 0.02)
and Yuki follows it in time (corr >= 0.4) or overshoots it (amp > 1.43). A gain is used only when it is consistent:
seen in at least --min-runs runs, every run deviates the same way, and the mean deviation is above 25 %. A deviation in
one singer only is that singer's, not Yuki's, and is left alone. Gains are clipped to [0.33, 3].

The gains act on the MetaHuman controls (CTRL_expressions_*) that form each ARKit channel: value * gain, clipped to
[0, 1]. --dump is a curve dump of ue_yuki_curves_dump.py (key-reduced); --out is written dense, one key per frame at
30 fps, in the format ue_yuki_curves_apply.py reads. The gains and their evidence go to acting_db/yuki_fit_gains.json."""
import argparse, json, math, time
from pathlib import Path

import numpy as np

from yuki_curves_io import FPS, load

ROOT = Path(__file__).resolve().parent
PERF = ROOT / "reports" / "yuki_lipsync" / "perf"
# ARKit channel -> MetaHuman controls that form it (CTRL_expressions_ prefix omitted).
MAP = {
    "browInnerUp": ["browRaiseInL", "browRaiseInR"], "browOuterUpLeft": ["browRaiseOuterL"], "browOuterUpRight": ["browRaiseOuterR"],
    "browDownLeft": ["browDownL", "browLateralL"], "browDownRight": ["browDownR", "browLateralR"],
    "eyeBlinkLeft": ["eyeBlinkL"], "eyeBlinkRight": ["eyeBlinkR"], "eyeSquintLeft": ["eyeSquintInnerL"], "eyeSquintRight": ["eyeSquintInnerR"],
    "eyeWideLeft": ["eyeWidenL"], "eyeWideRight": ["eyeWidenR"], "cheekSquintLeft": ["eyeCheekRaiseL"], "cheekSquintRight": ["eyeCheekRaiseR"],
    "noseSneerLeft": ["noseWrinkleL"], "noseSneerRight": ["noseWrinkleR"], "jawOpen": ["jawOpen"],
    "mouthFunnel": ["mouthFunnelUL", "mouthFunnelUR", "mouthFunnelDL", "mouthFunnelDR"],
    "mouthPucker": ["mouthLipsPurseUL", "mouthLipsPurseUR", "mouthLipsPurseDL", "mouthLipsPurseDR"],
    "mouthSmileLeft": ["mouthCornerPullL"], "mouthSmileRight": ["mouthCornerPullR"],
    "mouthFrownLeft": ["mouthCornerDepressL"], "mouthFrownRight": ["mouthCornerDepressR"],
    "mouthStretchLeft": ["mouthStretchL"], "mouthStretchRight": ["mouthStretchR"], "mouthDimpleLeft": ["mouthDimpleL"], "mouthDimpleRight": ["mouthDimpleR"],
    "mouthUpperUpLeft": ["mouthUpperLipRaiseL"], "mouthUpperUpRight": ["mouthUpperLipRaiseR"],
    "mouthLowerDownLeft": ["mouthLowerLipDepressL"], "mouthLowerDownRight": ["mouthLowerLipDepressR"],
    "mouthPressLeft": ["mouthPressUL", "mouthPressDL", "mouthLipsPressL"], "mouthPressRight": ["mouthPressUR", "mouthPressDR", "mouthLipsPressR"],
    "mouthRollLower": ["mouthLowerLipRollInL", "mouthLowerLipRollInR"], "mouthRollUpper": ["mouthUpperLipRollInL", "mouthUpperLipRollInR"],
    "mouthShrugLower": ["jawChinRaiseDL", "jawChinRaiseDR"], "mouthShrugUpper": ["jawChinRaiseUL", "jawChinRaiseUR"],
}
ap = argparse.ArgumentParser()
ap.add_argument("--train", required=True)
ap.add_argument("--min-runs", type=int, default=2)
ap.add_argument("--dump")
ap.add_argument("--out")
a = ap.parse_args()
runs = a.train.split(",")
audits = {r: json.load(open(PERF / r / "audit.json")) for r in runs}
gains, evidence = {}, {}
for ch in MAP:
    amps = []
    for r, au in audits.items():
        c = au["channels"].get(ch)
        if c and c["src_std"] >= 0.02 and (c["corr"] >= 0.4 or c["amp"] > 1.43):
            amps.append((r, c["amp"], c["corr"]))
    if not amps:
        continue
    logs = [math.log(1 / max(x[1], 1e-3)) for x in amps]
    g = math.exp(sum(logs) / len(logs))
    same_way = all(v > 0 for v in logs) or all(v < 0 for v in logs)
    used = len(amps) >= a.min_runs and same_way and abs(math.log(g)) > math.log(1.25)
    evidence[ch] = dict(runs=[dict(run=r, amp=am, corr=co) for r, am, co in amps], gain=round(min(max(g, 0.33), 3.0), 3), used=used)
    if used:
        gains[ch] = evidence[ch]["gain"]
out_g = dict(date=time.strftime("%Y-%m-%d %H:%M"), train=runs, min_runs=a.min_runs, gains=gains, evidence=evidence)
(ROOT / "acting_db").mkdir(exist_ok=True)
json.dump(out_g, open(ROOT / "acting_db" / "yuki_fit_gains.json", "w"), indent=1)
print("FIT gains", json.dumps(gains))
for ch, e in sorted(evidence.items()):
    if not e["used"]:
        print("  not used", ch, [(x["run"], x["amp"]) for x in e["runs"]], "gain", e["gain"])
if a.dump:
    names, cur = load(a.dump)
    cur = cur.astype(np.float64)
    ix = {n.replace("CTRL_expressions_", ""): i for i, n in enumerate(names)}
    for ch, g in gains.items():
        for c in MAP[ch]:
            if c in ix:
                cur[ix[c]] = np.clip(cur[ix[c]] * g, 0.0, 1.0)
    N = cur.shape[1]
    cur.astype(np.float32).tofile(a.out + ".f32")
    json.dump({"names": names, "keys": int(N), "length": (N - 1) / FPS}, open(a.out + ".json", "w"))
    print("FIT wrote", a.out, "curves", len(names), "frames", N)

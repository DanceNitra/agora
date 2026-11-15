"""Audits one yuki_song_pipeline run against the singer and writes what to fix, so every run teaches the next one.

    .venv_mp/Scripts/python.exe perf_audit.py <run_dir> [--label "Singer, Song, year"]

Reads <run_dir>/_tight.mp4 (singer left, Yuki right), measures all 52 MediaPipe blendshapes on both halves per frame
(cached in audit_bs.npz), and per channel reports correlation, amplitude ratio (std Yuki / std singer) and a null
control (Yuki shifted by 10 s). Composite checks catch shape and direction errors that single channels hide: the
oblique sad brow (inner up, outer not), brow knit, sad mouth (corners down against smile), lip press, left-right
asymmetry, and gaze. Writes <run_dir>/audit.json and appends one entry to ACTING_LEARNING_LOG.md: what is new in this
run, what recurs across runs (a property of Yuki or of the pipeline, not of the singer), and the fix for each.

Verdicts for a channel that moves in the singer (std >= 0.02): DEAD (amp < 0.15), WRONG_DIR (corr < -0.2), TIMING
(corr < 0.4 or less than 0.15 above the null control), WEAK (amp < 0.7), OVER (amp > 1.43), else OK. A channel that
barely moves in the singer (std < 0.005) but moves on Yuki (std >= 0.02) is YUKI_ONLY. Fit gains per channel go to
audit.json for yuki_expr_fit.py: 1 / amp, clipped to [0.33, 3], for WEAK channels with corr >= 0.4 and for OVER
channels; 0.5 for YUKI_ONLY."""
import argparse, glob, json, os, time
from pathlib import Path

import cv2, mediapipe as mp, numpy as np
from mediapipe.tasks.python import BaseOptions, vision

MODEL = r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit\models\face_landmarker.task"
ROOT = Path(__file__).resolve().parent
LOG = ROOT / "ACTING_LEARNING_LOG.md"
ap = argparse.ArgumentParser()
ap.add_argument("run")
ap.add_argument("--label", default="")
ap.add_argument("--variant", default="", help="audit the variant render _tight_<V>.mp4, before and after the base run")
a = ap.parse_args()
W = Path(a.run).resolve()
SFX = f"_{a.variant}" if a.variant else ""
RUN = W.name + SFX
cache = W / f"audit_bs{SFX}.npz"
if cache.exists():
    z = np.load(cache, allow_pickle=True)
    L, R, names = z["L"], z["R"], list(z["names"])
else:
    det = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=MODEL), num_faces=1, output_face_blendshapes=True))
    cap, L, R, names = cv2.VideoCapture(str(W / f"_tight{SFX}.mp4")), [], [], None
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        rgb = cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)
        w = rgb.shape[1] // 2
        for half, acc in ((rgb[:, :w].copy(), L), (rgb[:, w:].copy(), R)):
            r = det.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=half))
            if r.face_blendshapes:
                cats = [c for c in r.face_blendshapes[0] if c.category_name != "_neutral"]
                names = names or [c.category_name for c in cats]
                acc.append([c.score for c in cats])
            else:
                acc.append(None)
        if len(L) % 300 == 0:
            print("AUDIT frames", len(L), flush=True)
    K = len(names)
    L = np.array([x if x is not None else [np.nan] * K for x in L], float)
    R = np.array([x if x is not None else [np.nan] * K for x in R], float)
    np.savez(cache, L=L, R=R, names=np.array(names, dtype=object))
ok = ~np.isnan(L).any(1) & ~np.isnan(R).any(1)
A, B = L[ok], R[ok]
ix = {n: i for i, n in enumerate(names)}
NULL_SHIFT = 300


def corr(x, y):
    return float(np.corrcoef(x, y)[0, 1]) if x.std() > 1e-4 and y.std() > 1e-4 else float("nan")


def highpass(x, n=90):
    """Removes the slow trend (3 s moving mean) so a correlation reads frame-level shape, not a drift."""
    return x - np.convolve(np.pad(x, (n // 2, n - 1 - n // 2), mode="edge"), np.ones(n) / n, mode="valid")


def judge(x, y, hp=False):
    sx, sy = float(x.std()), float(y.std())
    xc, yc = (highpass(x), highpass(y)) if hp else (x, y)
    c, amp = corr(xc, yc), sy / max(sx, 1e-6)
    cn = corr(xc, np.roll(yc, NULL_SHIFT)) if len(x) > 2 * NULL_SHIFT else float("nan")
    if sx < 0.005:
        v = "YUKI_ONLY" if sy >= 0.02 else "QUIET"
    elif sx < 0.02:
        v = "QUIET"
    elif amp < 0.15:
        v = "DEAD"
    elif c < -0.2:
        v = "WRONG_DIR"
    elif not c >= 0.4 or (cn == cn and c - abs(cn) < 0.15):
        v = "TIMING"
    elif amp < 0.7:
        v = "WEAK"
    elif amp > 1.43:
        v = "OVER"
    else:
        v = "OK"
    gain = 1.0
    if (v == "WEAK" and c >= 0.4) or v == "OVER":
        gain = float(np.clip(1 / amp, 0.33, 3.0))
    elif v == "YUKI_ONLY":
        gain = 0.5
    return dict(corr=round(c, 3), amp=round(amp, 3), null=round(cn, 3), src_std=round(sx, 4), yuki_std=round(sy, 4), verdict=v, gain=round(gain, 3))


ch = {n: judge(A[:, i], B[:, i]) for n, i in ix.items()}
g = lambda M, n: M[:, ix[n]]
COMP = {
    "sad_brow_oblique (AU1 without AU2)": lambda M: g(M, "browInnerUp") - 0.5 * (g(M, "browOuterUpLeft") + g(M, "browOuterUpRight")),
    "brow_knit (AU4)": lambda M: 0.5 * (g(M, "browDownLeft") + g(M, "browDownRight")),
    "sad_mouth (AU15 against AU12)": lambda M: 0.5 * (g(M, "mouthFrownLeft") + g(M, "mouthFrownRight") - g(M, "mouthSmileLeft") - g(M, "mouthSmileRight")),
    "lip_press (AU24)": lambda M: 0.5 * (g(M, "mouthPressLeft") + g(M, "mouthPressRight")),
    "smile_asymmetry L-R": lambda M: g(M, "mouthSmileLeft") - g(M, "mouthSmileRight"),
    "blink_asymmetry L-R": lambda M: g(M, "eyeBlinkLeft") - g(M, "eyeBlinkRight"),
    "brow_asymmetry L-R": lambda M: g(M, "browOuterUpLeft") - g(M, "browOuterUpRight") + g(M, "browDownRight") - g(M, "browDownLeft"),
    "gaze_horizontal": lambda M: 0.5 * (g(M, "eyeLookOutLeft") - g(M, "eyeLookInLeft") + g(M, "eyeLookInRight") - g(M, "eyeLookOutRight")),
    "gaze_vertical": lambda M: 0.5 * (g(M, "eyeLookUpLeft") + g(M, "eyeLookUpRight") - g(M, "eyeLookDownLeft") - g(M, "eyeLookDownRight")),
}
comp = {k: judge(f(A), f(B), hp=True) for k, f in COMP.items()}
# Brow shape: how much the inner brow moves against the outer brow. A sad or pleading brow needs inner >= outer.
bshape = {who: round(float(M[:, ix["browInnerUp"]].std() / max(0.5 * (M[:, ix["browOuterUpLeft"]].std() + M[:, ix["browOuterUpRight"]].std()), 1e-6)), 3)
          for who, M in (("singer", A), ("yuki", B))}
UPPER = ["browInnerUp", "browDownLeft", "browDownRight", "browOuterUpLeft", "browOuterUpRight", "eyeBlinkLeft", "eyeBlinkRight",
         "eyeSquintLeft", "eyeSquintRight", "eyeWideLeft", "eyeWideRight", "cheekSquintLeft", "cheekSquintRight", "noseSneerLeft", "noseSneerRight"]
moving = lambda sel: [n for n in sel if ch[n]["src_std"] >= 0.02]
summary = {}
for grp, sel in (("upper", UPPER), ("mouth_jaw", [n for n in names if n.startswith(("mouth", "jaw"))]), ("gaze", [n for n in names if n.startswith("eyeLook")])):
    mv = moving(sel)
    summary[grp] = dict(n=len(mv), corr=round(float(np.nanmean([ch[n]["corr"] for n in mv])), 3) if mv else None,
                        null=round(float(np.nanmean([abs(ch[n]["null"]) for n in mv])), 3) if mv else None,
                        amp=round(float(np.nanmean([ch[n]["amp"] for n in mv])), 3) if mv else None)
rec = dict(run=RUN, label=a.label, date=time.strftime("%Y-%m-%d %H:%M"), frames=int(len(L)), both=int(ok.sum()),
           summary=summary, brow_inner_to_outer=bshape, channels=ch, composites=comp)
json.dump(rec, open(W / f"audit{SFX}.json", "w"), indent=1)
base = json.load(open(W / "audit.json")) if SFX and (W / "audit.json").exists() else None

# Across runs: a problem in most audited runs is Yuki's or the pipeline's; one seen only here is the singer's.
others = []
for p in glob.glob(str(W.parent / "*" / "audit.json")):
    if Path(p).parent != W:
        others.append(json.load(open(p)))
bad = {"DEAD", "WRONG_DIR", "TIMING", "WEAK", "OVER", "YUKI_ONLY"}
lines = [f"\n## {rec['date']} {RUN}" + (f" ({a.label})" if a.label else ""), ""]
lines.append(f"Frames {rec['frames']}, both faces {rec['both']}. Means over channels that move in the singer, with the null "
             "control (Yuki shifted 10 s) in brackets:")
for k, s in summary.items():
    if s["n"]:
        lines.append(f"- {k}: {s['n']} channels, corr {s['corr']:+.2f} (null {s['null']:.2f}), amp {s['amp']:.2f}")
lines.append(f"- brow shape, inner to outer movement: singer {bshape['singer']:.2f}, Yuki {bshape['yuki']:.2f}"
             + (" (Yuki tilts the brow the other way)" if bshape["yuki"] < 0.6 * bshape["singer"] else ""))
lines += ["", "Composite checks correlate after removing the 3 s trend.", "",
          "| check | corr | amp | verdict | " + ("before (base run) |" if base else "seen in other runs |"), "|---|---|---|---|---|"]
rows = [(k, v) for k, v in comp.items()] + [(k, v) for k, v in sorted(ch.items())
                                            if v["verdict"] in bad or (base and base["channels"][k]["verdict"] in bad)]
for k, v in rows:
    seen = [o["run"] for o in others if (o["composites"].get(k) or o["channels"].get(k) or {}).get("verdict") == v["verdict"]]
    if base:
        b = base["composites"].get(k) or base["channels"].get(k)
        last = f"{b['corr']:+.2f} / {b['amp']:.2f} {b['verdict']}"
    else:
        last = ", ".join(seen) if seen else "new"
    lines.append(f"| {k} | {v['corr']:+.2f} | {v['amp']:.2f} | {v['verdict']} | {last} |")
fixes = []
for k, v in comp.items():
    if v["verdict"] in bad:
        fixes.append(f"- {k}: {v['verdict']}. " + {
            "WEAK": "Strength missing: raise the channels that form it (fit gains) and check the shape on frames.",
            "DEAD": "The shape does not exist on Yuki: a curve or a corrective shape is missing; build it.",
            "WRONG_DIR": "Moves the opposite way: the control mapping is wrong; fix the mapping, not the gain.",
            "TIMING": "Timing or detection does not follow the singer; check the solve on frames before any gain.",
            "OVER": "Too strong: damp the channels that form it.",
            "YUKI_ONLY": "Moves on Yuki only: damp it.",
        }[v["verdict"]])
gains = {k: v["gain"] for k, v in ch.items() if v["gain"] != 1.0}
lines += ["", "Fixes:"] + (fixes or ["- none from the composite checks"])
lines.append("- fit gains for yuki_expr_fit.py: " + (", ".join(f"{k} x{v}" for k, v in sorted(gains.items())) or "none"))
if not LOG.exists():
    LOG.write_text("# Acting learning log\n\nOne entry per audited run, written by `perf_audit.py`. A row marked `new` is "
                   "seen in this run only (the singer's); a row seen in other runs is Yuki's or the pipeline's and is "
                   "fixed first. Nothing here is a visual verdict: frames are checked by eye before any claim.\n",
                   encoding="utf-8")
# Re-auditing a run replaces its entry instead of adding a second one.
parts = LOG.read_text(encoding="utf-8").split("\n## ")
keep = [parts[0]] + [q for q in parts[1:] if q.split("\n", 1)[0].split()[2:3] != [RUN]]
LOG.write_text("\n## ".join(keep).rstrip("\n") + "\n" + "\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))

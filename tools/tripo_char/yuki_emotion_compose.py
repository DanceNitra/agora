"""Compose one face animation for a song from several mood solves and a director's sheet.

    .venv_mp/Scripts/python.exe yuki_emotion_compose.py <curves_dir> <score.json> <vocals_16k_s16.raw> <out_stem> [prefix]

<curves_dir> holds the dumps of ue_yuki_curves_dump.py: <prefix><mood>_face.f32 / .json for the moods the score names
(default prefix AS_Puzzle_). All solves come from the same audio, so they share the clock and the articulation.

Method. (1) Per frame, the mood weights of the phrase the frame lies in, cross-faded over FADE seconds, blend ALL curves
of the solves. (2) A performance layer is added on top, only on curves that do not shape speech sounds: a resting lid
level, a smile that follows the sheet and swells in the gaps between phrases, inner brows up and lower lids for "sad",
a brow lift on loud notes (loudness of the vocals, slow envelope removed), blinks at phrase ends where the solver has
none, and small gaze moves. (3) The frown of the solves (browDown, noseWrinkle) is scaled by FROWN.
Writes <out_stem>.f32 / .json in the dump format and <out_stem>.report.json with the checks: correlation and lag of
jawOpen against every solve (the lips must not move in time), and the range of every layered curve."""
import json
import os
import sys
from pathlib import Path

import numpy as np

from yuki_curves_io import FPS, load

cdir, score_p, voc_p, out = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
PRE = sys.argv[5] if len(sys.argv) > 5 else "AS_Puzzle_"
E = lambda k, d: float(os.environ.get(k, d))
FADE, LID, FROWN, BROW_ACCENT, SMILE_GAIN, GAP_SMILE = E("FADE", 0.6), E("LID", 0.12), E("FROWN", 0.35), E("BROW_ACCENT", 0.22), E("SMILE_GAIN", 0.12), E("GAP_SMILE", 0.22)
SMILE_CAP = E("SMILE_CAP", 0.55)
WIDEN, BROW_IN, BLINK_EVERY = E("WIDEN", 0.15), E("BROW_IN", 0.55), E("BLINK_EVERY", 3.4)
score = json.load(open(score_p, encoding="utf-8"))
moods = sorted({m for p in score["phrases"] for m in p[2]["moods"]} | set(score["default"]["moods"]))
D, names, fps = {}, None, FPS
for m in moods:
    nm, a = load(cdir / f"{PRE}{m}_face")
    if names is None:
        names, N = nm, a.shape[1]
    assert nm == names and a.shape[1] == N, (m, "curve set differs")
    D[m] = a.astype(np.float64)
t = np.arange(N) / fps
ix = {n: i for i, n in enumerate(names)}


def C(short):
    n = "CTRL_expressions_" + short
    assert n in ix, f"curve {n} is not in the solve; near: {[k for k in names if short[:6].lower() in k.lower()][:8]}"
    return ix[n]


def smooth(x, sec):
    k = max(1, int(round(sec * fps)))
    return np.convolve(np.pad(x, k, mode="edge"), np.hanning(2 * k + 1) / np.hanning(2 * k + 1).sum(), mode="same")[k:-k]


# per-frame sheet values: phrase values inside a phrase, default in the gaps, then smoothed
ph = score["phrases"]
W = {m: np.full(N, score["default"]["moods"].get(m, 0.0)) for m in moods}
smile, sad = np.full(N, score["default"]["smile"]), np.full(N, score["default"]["sad"])
gaze_x, gaze_y, sing = np.zeros(N), np.zeros(N), np.zeros(N)
rng = np.random.default_rng(7)
for a, b, v in ph:
    k = (t >= a) & (t < b)
    for m in moods:
        W[m][k] = v["moods"].get(m, 0.0)
    smile[k], sad[k], sing[k] = v["smile"], v["sad"], 1.0
    if v["gaze"] == "down":
        gaze_y[k] = -0.16
    elif v["gaze"] == "away":
        gaze_x[k] = rng.choice([-1, 1]) * 0.22
        gaze_y[k] = -0.08
tot = sum(W.values())
W = {m: smooth(W[m] / tot, FADE) for m in moods}
tot = sum(W.values())
out_c = sum((W[m] / tot)[None, :] * D[m] for m in moods)
smile_s, sad_s = smooth(smile, 0.5), smooth(sad, 0.6)
gap = smooth(1.0 - sing, 0.35)                       # 1 in the pauses between phrases
report = {"fps": fps, "frames": int(N), "moods": moods, "layer": {}}


def add(short, v, lo=0.0, hi=1.0):
    for s in ("L", "R"):
        i = C(short + s)
        out_c[i] = np.clip(out_c[i] + v, lo, hi)
    report["layer"][short] = [round(float(np.min(v)), 3), round(float(np.max(v)), 3)]


def scale(short, f):
    for s in ("L", "R"):
        out_c[C(short + s)] *= f


# frown of the solves down (it read as anger on the sung test), less so where the sheet says sad
frown = FROWN + (1 - FROWN) * 0.5 * sad_s
scale("browDown", frown)
scale("noseWrinkle", FROWN)
# Measured on the five solves of PUZZLE (2026-11-14): eyeWiden averages 0.08 to 0.24 over the whole song and inner brow
# raise 0.23 to 0.62: the solver holds the eyes wide and the brows worried the whole time. Both are scaled down;
# "sad" keeps more of the inner brow raise.
scale("eyeWiden", WIDEN)
scale("browRaiseIn", BROW_IN + (1 - BROW_IN) * sad_s)
# smile: the sheet's level while singing, a little more in the pauses (mouth is closed there)
sm = SMILE_GAIN * smile_s + GAP_SMILE * gap * (1 - sad_s)
add("mouthCornerPull", sm)
add("mouthSharpCornerPull", 0.45 * sm)
add("mouthDimple", 0.15 * sm)
add("eyeCheekRaise", 0.55 * sm)
add("eyeSquintInner", 0.25 * sm)
# sad: inner brows up and together, lids lower
# The sad solve raises the cheeks (0.46 on average) and squints (0.29); with the gaze down the eyes were nearly shut on
# the check stills of 2026-11-14. Both are halved where the sheet says sad.
scale("eyeCheekRaise", 1 - 0.5 * sad_s)
scale("eyeSquintInner", 1 - 0.5 * sad_s)
# brow lift on loud notes: loudness of the vocals above its own 2 s envelope
raw = np.fromfile(voc_p, dtype=np.int16).astype(np.float32) / 32768
hop = 16000 / fps
rms = np.array([np.sqrt(np.mean(raw[int(i * hop):int(i * hop + 2 * hop)] ** 2) + 1e-12) for i in range(N)])
db = 20 * np.log10(rms + 1e-5)
acc = np.clip((smooth(db, 0.12) - smooth(db, 2.0)) / 9.0, 0, 1) * (db > -32)
acc = smooth(acc, 0.18)
add("browRaiseOuter", BROW_ACCENT * acc * (1 - 0.5 * sad_s))
add("browRaiseIn", 0.6 * BROW_ACCENT * acc)
add("eyeWiden", 0.12 * acc * (1 - sad_s))
# resting lids: a little lower all the time, lower when sad; never below what the solver's own blink asks
add("eyeBlink", LID + 0.03 * sad_s - 0.06 * acc)
# blinks at phrase ends where the solver has none within 0.6 s
bl = np.maximum(out_c[C("eyeBlinkL")], out_c[C("eyeBlinkR")])
# The solves blink about once in 30 s (eyeBlink averages 0.003 to 0.011): a stare. Blinks are added at phrase ends and
# then wherever more than BLINK_EVERY seconds (jittered) pass without one; not on a loud note.
pulse = np.array([0.4, 0.85, 1.0, 1.0, 0.8, 0.5, 0.25, 0.08])
blink_at = [int(round((b + 0.12) * fps)) for a, b, v in ph]
blink_at += [int(round(x * fps)) for x in np.arange(1.2, t[-1] - 1, 0.25)]      # candidates, kept only where the wait is long enough
done, last = [], -1e9
solver = np.where(bl > 0.7)[0]
for f in sorted(set(blink_at)):
    wait = BLINK_EVERY * (0.7 + 0.6 * rng.random())
    prev = max([last] + [int(x) for x in solver[solver < f][-1:]])
    is_end = any(abs(f - int(round((b + 0.12) * fps))) <= 1 for a, b, v in ph)
    if f + len(pulse) >= N or (f - prev) / fps < (1.2 if is_end else wait) or (not is_end and acc[f] > 0.4):
        continue
    if len(solver) and np.abs(solver - f).min() < 0.5 * fps:
        continue
    for s in ("L", "R"):
        i = C("eyeBlink" + s)
        out_c[i, f:f + len(pulse)] = np.maximum(out_c[i, f:f + len(pulse)], pulse)
    done.append(f)
    last = f
report["blinks_added"] = len(done)
report["blinks_solver"] = int((np.diff((bl > 0.7).astype(int)) == 1).sum())
# gaze: the sheet's direction, eased; a look down pulls the upper lid with it (the rig does that from eyeLookDown)
# small fixation changes every 1.5 to 4 s, so the eyes are never locked
fx, fy, f = np.zeros(N), np.zeros(N), 0
while f < N:
    n = int(fps * (1.5 + 2.5 * rng.random()))
    fx[f:f + n], fy[f:f + n] = rng.normal(0, 0.035), rng.normal(0, 0.02)
    f += n
gx, gy = smooth(gaze_x, 0.25) + smooth(fx, 0.06), smooth(gaze_y, 0.3) + smooth(fy, 0.06)
for s in ("L", "R"):
    for short, v in (("eyeLookLeft", np.clip(-gx, 0, 1)), ("eyeLookRight", np.clip(gx, 0, 1)), ("eyeLookDown", np.clip(-gy, 0, 1)), ("eyeLookUp", np.clip(gy, 0, 1))):
        i = C(short + s)
        out_c[i] = np.clip(out_c[i] + v, 0, 1)
report["layer"]["gaze_x"] = [round(float(gx.min()), 3), round(float(gx.max()), 3)]
report["layer"]["gaze_y"] = [round(float(gy.min()), 3), round(float(gy.max()), 3)]

# Soft ceiling on the smile: the happy solve reaches 1.0 on mouthCornerPull and with the layer the peak was a grin that
# bared both rows of teeth (check still at 27.4 s, 2026-11-14). x -> cap * tanh(x / cap) leaves small values alone.
for short, cap in (("mouthCornerPull", SMILE_CAP), ("mouthSharpCornerPull", 0.6 * SMILE_CAP), ("mouthDimple", 0.6 * SMILE_CAP), ("mouthLowerLipDepress", 0.45)):
    for sd in ("L", "R"):
        i = C(short + sd)
        out_c[i] = cap * np.tanh(out_c[i] / cap)
# Enunciation (ENUN, 1 = as solved): on the full render of 2026-11-14 a rounded word onset showed a narrower mouth in
# 0.49 of the cases (chance 0.38) and an open vowel a wider gap in 0.57 (chance 0.45): the sung solve is mushy. The
# rounding curves (funnel, purse) are scaled by ENUN and the jaw's swing around its own 0.5 s average is widened by the
# same factor, so the visemes the solver already times become more distinct. No timing changes.
ENUN = E("ENUN", 1.0)
if ENUN != 1.0:
    for n_ in names:
        sh = n_.replace("CTRL_expressions_", "")
        if sh.startswith("mouthFunnel") or sh.startswith("mouthLipsPurse"):
            out_c[ix[n_]] = np.clip(out_c[ix[n_]] * ENUN, 0, 1)
    j_ = C("jawOpen")
    avg_ = smooth(out_c[j_], 0.5)
    out_c[j_] = np.clip(avg_ + (out_c[j_] - avg_) * ENUN, 0, 1)
# Asymmetry (ASYM): a face that moves both sides by the same amount reads as a mask. The smile and the brows get a slow
# left/right imbalance of up to ASYM, each with its own drift.
ASYM = E("ASYM", 0.14)
if ASYM > 0:
    for shorts, seed_ in ((("mouthCornerPull", "mouthSharpCornerPull", "mouthDimple", "eyeCheekRaise"), 21), (("browRaiseOuter", "browRaiseIn", "browDown"), 22)):
        r_ = np.random.default_rng(seed_)
        n_ = np.clip(smooth(r_.normal(0, 1, N), 2.5) * np.sqrt(2.5 * fps) * 0.9, -1, 1) * ASYM
        for short in shorts:
            out_c[C(short + "L")] = np.clip(out_c[C(short + "L")] * (1 + n_), 0, 1)
            out_c[C(short + "R")] = np.clip(out_c[C(short + "R")] * (1 - n_), 0, 1)
# Bilabials (WORDS = a faster-whisper json with word times): for m, b and p the lips must meet. Measured on the render
# of 2026-11-14, 4 of the 7 such words in the first 31 s reached a closure (chance 0.22); the solver only dips on a sung
# "being" or "but". At each such word the deepest dip of the mouth opening within BIL_WIN of the word's start is taken
# as the moment the solver meant, and the dip is closed for a few frames: jaw and the lip-opening curves fade out, the
# lips-together curves come in.
if os.environ.get("WORDS"):
    wj = json.load(open(os.environ["WORDS"], encoding="utf-8"))
    BIL_WIN = E("BIL_WIN", 0.2)
    lt = [C("mouthLipsTogether" + q) for q in ("UL", "UR", "DL", "DR")]
    opening = out_c[C("jawOpen")] * (1 - out_c[lt].mean(0))
    openers = [C(n_) for n_ in ("jawOpen", "mouthUpperLipRaiseL", "mouthUpperLipRaiseR", "mouthLowerLipDepressL", "mouthLowerLipDepressR", "mouthFunnelUL", "mouthFunnelUR",
                                "mouthFunnelDL", "mouthFunnelDR", "mouthStretchL", "mouthStretchR")]
    pulse_b = np.array([0.35, 0.8, 1.0, 1.0, 0.7, 0.3])
    closed_n = 0
    for sg in wj["segments"]:
        for x in sg.get("words", []):
            word, st = x.get("word", x.get("w", "")).strip().lower(), x.get("start", x.get("s", 0.0))
            if word[:1] not in ("m", "b", "p"):
                continue
            k0, k1 = max(0, int((st - BIL_WIN) * fps)), min(N - len(pulse_b), int((st + BIL_WIN) * fps))
            if k1 <= k0:
                continue
            f = k0 + int(opening[k0:k1 + 1].argmin()) - 2
            f = max(0, min(N - len(pulse_b), f))
            keep_ = 1 - pulse_b
            for i_ in openers:
                out_c[i_, f:f + len(pulse_b)] *= np.where(i_ == C("jawOpen"), 0.25 + 0.75 * keep_, keep_)
            for i_ in lt:
                out_c[i_, f:f + len(pulse_b)] = np.maximum(out_c[i_, f:f + len(pulse_b)], pulse_b)
            closed_n += 1
    report["bilabial_closures_set"] = closed_n
# checks: the jaw must keep the solves' timing
j = out_c[C("jawOpen")]


def lagcorr(a, b, span=6):
    best = max(range(-span, span + 1), key=lambda k: np.corrcoef(a[span + k:len(a) - span + k], b[span:len(b) - span])[0, 1])
    return int(best), round(float(np.corrcoef(a[span + best:len(a) - span + best], b[span:len(b) - span])[0, 1]), 3)


report["jaw_vs_solve"] = {m: lagcorr(j, D[m][C("jawOpen")]) for m in moods}
report["jaw_between_solves"] = {f"{a}-{b}": lagcorr(D[a][C("jawOpen")], D[b][C("jawOpen")]) for i, a in enumerate(moods) for b in moods[i + 1:]}
# per phrase: what the face does (mean of the left side), for reading against the lyrics
rows = ("mouthCornerPullL", "eyeCheekRaiseL", "browDownL", "browRaiseInL", "browRaiseOuterL", "eyeBlinkL", "eyeWidenL", "mouthCornerDepressL")
report["per_phrase"] = [[a, b] + [round(float(out_c[C(r[:-1]) if False else ix["CTRL_expressions_" + r], (t >= a) & (t < b)].mean()), 2) for r in rows] for a, b, v in ph]
report["rows"] = rows
out_c.astype(np.float32).tofile(out + ".f32")
json.dump({"names": names, "keys": int(N), "length": (N - 1) / fps}, open(out + ".json", "w"))
json.dump(report, open(out + ".report.json", "w"), indent=1)
print("COMPOSE", json.dumps({k: v for k, v in report.items() if k != "per_phrase"}))
print("%14s" % "phrase", *["%9s" % r[:9] for r in rows])
for row in report["per_phrase"]:
    print("%6.1f-%6.1f " % (row[0], row[1]), *["%9.2f" % x for x in row[2:]])

"""Brow animation layer from the song audio, following RESEARCH_eyebrows_animation_2026-11-08.md section 5.
Outputs per-frame ADDITIVE values (30 fps) for the MetaHuman brow controls, to be added on top of Speech2Face.

Layers (values are our design choices, rules from the sources cited in the research file):
  A  mood pose (seductive): slight brow-down + lateral, one-sided outer raise, held, blended in over 400 ms
  B  prominence accents: at most one per phrase, cooldown 1.2 s, onset 60 ms before the syllable,
     rise 120 ms, hold 100 ms, fall 200 ms, outer 0.15-0.30 scaled by the F0 excursion, inner 0.5x,
     symmetric 30 %, one-sided 70 % (deliberate, seductive), 60 % probability gate
  C  singing pitch track: outer raise follows note height on notes held > 300 ms, k = 0.15, smoothed
  E  eyebrow flash at the first phrase start (inner+outer 0.3, 200 ms)
Usage: brow_layer.py <wav> <n_frames> <out.json> [seed]
"""
import json
import sys

import librosa
import numpy as np

wav, nfr, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
rng = np.random.default_rng(int(sys.argv[4]) if len(sys.argv) > 4 else 7)
FPS = 30.0
y, sr = librosa.load(wav, sr=16000, mono=True)
hop = 160  # 10 ms
f0, vflag, _ = librosa.pyin(y, fmin=60, fmax=700, sr=sr, frame_length=2048, hop_length=hop)
rms = librosa.feature.rms(y=y, frame_length=1024, hop_length=hop)[0]
n = min(len(f0), len(rms))
f0, vflag, rms = f0[:n], vflag[:n], rms[:n]
t10 = np.arange(n) * 0.01
semi = np.where(vflag, 12 * np.log2(np.nan_to_num(f0, nan=1.0) / 440.0), np.nan)

# phrases: voiced/energetic regions separated by pauses > 200 ms
act = (rms > np.median(rms) * 0.6) & vflag
phr = []
i = 0
while i < n:
    if act[i]:
        j = i
        gap = 0
        while j < n and gap < 20:
            gap = 0 if act[j] else gap + 1
            j += 1
        phr.append((i, j - gap))
        i = j
    else:
        i += 1
phr = [(a, b) for a, b in phr if b - a > 30]

# singer range for layer C
vs = semi[~np.isnan(semi)]
p50, p95 = np.percentile(vs, 50), np.percentile(vs, 95)

frames = np.arange(nfr) / FPS
L = {k: np.zeros(nfr) for k in ("raiseIn_L", "raiseIn_R", "raiseOut_L", "raiseOut_R", "down_L", "down_R",
                                 "lateral_L", "lateral_R")}


def env(t, on, rise, hold, fall):
    if t < on or t > on + rise + hold + fall:
        return 0.0
    if t < on + rise:
        x = (t - on) / rise
    elif t < on + rise + hold:
        return 1.0
    else:
        x = 1 - (t - on - rise - hold) / fall
    return x * x * (3 - 2 * x)


# A: seductive mood pose, blended in over 400 ms from the first phrase
t0 = phr[0][0] * 0.01 if phr else 0.0
blend = np.ones(nfr)  # the brow pose is part of her look, held from frame 0
# p6 brow pose: inner heads low and drawn in (down + lateral), outer part lifted (raiseOut) -> angled arch
import os
A = json.loads(os.environ.get("BROW_POSE", '{"down": 0.30, "lateral": 0.20, "raiseOut_L": 0.28, "raiseOut_R": 0.22}'))
L["down_L"] += A["down"] * blend; L["down_R"] += A["down"] * blend
L["lateral_L"] += A["lateral"] * blend; L["lateral_R"] += A["lateral"] * blend
L["raiseOut_L"] += A["raiseOut_L"] * blend; L["raiseOut_R"] += A["raiseOut_R"] * blend

# B: prominence accents
accents = []
last = -9.0
for k, (a, b) in enumerate(phr):
    med = np.nanmedian(semi[a:b]); emed = np.median(rms[a:b])
    cand = [i for i in range(a, b) if vflag[i] and semi[i] - med >= 1.5 and rms[i] > emed]
    if not cand:
        continue
    i = max(cand, key=lambda i: (semi[i] - med) + 5 * rms[i] / (emed + 1e-6))
    # onset of the syllable: walk back to where energy rose
    s = i
    while s > a and rms[s - 1] < rms[s] * 1.05 and i - s < 25:
        s -= 1
    tt = s * 0.01
    if tt - last < 1.2 or rng.random() > 0.6:
        continue
    last = tt
    exc = float(np.clip((semi[i] - med) / 6.0, 0, 1))
    amp = 0.15 + 0.15 * exc
    side = "both" if rng.random() < 0.3 else ("L" if rng.random() < 0.5 else "R")
    on = tt - 0.06 + rng.uniform(-0.04, 0.04)
    accents.append({"t": round(tt, 3), "amp": round(amp, 3), "side": side})
    e = np.array([env(t, on, 0.12, 0.10, 0.20) for t in frames])
    for sd in ("L", "R"):
        g = 1.0 if side in ("both", sd) else 0.25
        L["raiseOut_" + sd] += amp * g * e
        L["raiseIn_" + sd] += 0.5 * amp * g * e

# C: singing pitch-height track on held notes (> 300 ms of stable pitch)
track = np.zeros(n)
i = 0
while i < n:
    if vflag[i]:
        j = i
        while j + 1 < n and vflag[j + 1] and abs(semi[j + 1] - semi[i]) < 1.0:
            j += 1
        if (j - i) * 0.01 > 0.3:
            pos = np.clip((np.nanmean(semi[i:j + 1]) - p50) / max(1e-3, p95 - p50), 0, 1)
            track[i:j + 1] = 0.15 * pos
        i = j + 1
    else:
        i += 1
# attack ~250 ms, release ~400 ms
sm = np.zeros(n)
for i in range(1, n):
    a = 0.04 if track[i] > sm[i - 1] else 0.025
    sm[i] = sm[i - 1] + a * (track[i] - sm[i - 1])
c = np.interp(frames, t10, sm)
L["raiseOut_L"] += c; L["raiseOut_R"] += c

# E: one eyebrow flash at the first phrase start
if phr:
    e = np.array([env(t, phr[0][0] * 0.01 - 0.15, 0.07, 0.06, 0.07) for t in frames])
    for sd in ("L", "R"):
        L["raiseIn_" + sd] += 0.3 * e; L["raiseOut_" + sd] += 0.3 * e

json.dump({"fps": FPS, "layers": {k: [round(float(v), 4) for v in a] for k, a in L.items()},
           "accents": accents, "phrases": [(round(a * 0.01, 2), round(b * 0.01, 2)) for a, b in phr]},
          open(out, "w"))
print("phrases", len(phr), "accents", len(accents), accents)
print("max", {k: round(float(a.max()), 3) for k, a in L.items()})

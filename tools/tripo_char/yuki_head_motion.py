"""Head motion for a sung performance, from the same director's sheet as the face (yuki_emotion_compose) and the audio.

    .venv_mp/Scripts/python.exe yuki_head_motion.py <score.json> <vocals_16k_s16.raw> <mix_16k_s16.raw> <out.json> [seconds]

Per frame at 30 fps: yaw, pitch and roll of the head in degrees (yaw + to the character's left, pitch + up, roll + is
the head tilting to the character's left shoulder; the Unreal script maps these to bones and checks the signs).
Parts: the head follows the sheet's gaze (away, down) by a part of the way; it sinks and tilts where the sheet says sad
and lifts a little on loud notes; it tilts to alternating sides phrase by phrase; a small nod runs on the song's beat
(tempo and phase from the onset envelope of the mix), larger where the sheet smiles; slow noise keeps it from ever
standing still. Everything is eased and the speed is limited to SPEED degrees per second.
CALIB=1 writes a test instead: +20 degrees yaw, then pitch, then roll, 20 frames each."""
import json
import os
import sys

import numpy as np

score_p, voc_p, mix_p, out = sys.argv[1:5]
FPS = 30.0
score = json.load(open(score_p, encoding="utf-8"))
dur = float(sys.argv[5]) if len(sys.argv) > 5 else max(p[1] for p in score["phrases"])
N = int(round(dur * FPS)) + 1
t = np.arange(N) / FPS
if os.environ.get("CALIB"):
    y, p, r = np.zeros(N), np.zeros(N), np.zeros(N)
    y[0:20], p[20:40], r[40:60] = 20, 20, 20
    json.dump({"fps": FPS, "yaw": y.tolist(), "pitch": p.tolist(), "roll": r.tolist()}, open(out, "w"))
    print("HEAD calibration written", N)
    sys.exit()
E = lambda k, d: float(os.environ.get(k, d))
NOD, TILT, FOLLOW, SAD_DOWN, NOISE, SPEED = E("NOD", 1.6), E("TILT", 4.0), E("FOLLOW", 0.6), E("SAD_DOWN", 7.0), E("NOISE", 1.0), E("SPEED", 45.0)


def smooth(x, sec):
    k = max(1, int(round(sec * FPS)))
    w = np.hanning(2 * k + 1)
    return np.convolve(np.pad(x, k, mode="edge"), w / w.sum(), mode="same")[k:-k]


def rms30(path):
    raw = np.fromfile(path, dtype=np.int16).astype(np.float32) / 32768
    hop = 16000 / FPS
    return np.array([np.sqrt(np.mean(raw[int(i * hop):int(i * hop + 2 * hop)] ** 2) + 1e-12) if int(i * hop) < len(raw) else 1e-6 for i in range(N)])


rng = np.random.default_rng(11)
smile, sad = np.full(N, score["default"]["smile"]), np.full(N, score["default"]["sad"])
gx, gy, side = np.zeros(N), np.zeros(N), np.zeros(N)
for i, (a, b, v) in enumerate(score["phrases"]):
    k = (t >= a) & (t < b)
    smile[k], sad[k] = v["smile"], v["sad"]
    side[k] = 1 if i % 2 == 0 else -1
    if v["gaze"] == "down":
        gy[k] = -1
    elif v["gaze"] == "away":
        gx[k] = rng.choice([-1, 1])
smile, sad, side = smooth(smile, 0.6), smooth(sad, 0.7), smooth(side, 0.9)
db = 20 * np.log10(rms30(voc_p) + 1e-5)
acc = smooth(np.clip((smooth(db, 0.12) - smooth(db, 2.0)) / 9.0, 0, 1) * (db > -32), 0.25)
# beat: onset envelope of the mix, tempo by autocorrelation between 70 and 180 beats per minute, phase by a comb
m = np.log(rms30(mix_p) + 1e-4)
on = np.clip(np.diff(m, prepend=m[0]), 0, None)
on = on - smooth(on, 1.0)
lags = np.arange(int(FPS * 60 / 180), int(FPS * 60 / 70) + 1)
ac = np.array([np.dot(on[:-l], on[l:]) for l in lags])
# finer than one frame: parabola through the peak
i0 = int(ac.argmax())
frac = 0.0
if 0 < i0 < len(ac) - 1:
    d = ac[i0 - 1] - 2 * ac[i0] + ac[i0 + 1]
    frac = 0.5 * (ac[i0 - 1] - ac[i0 + 1]) / d if d != 0 else 0.0
period = (lags[i0] + frac) / FPS
if 60 / period > 125:            # the onset envelope locks onto the off-beats of a slow song; nod on the half tempo
    period *= 2
phase = max(np.linspace(0, period, 40, endpoint=False), key=lambda ph: np.sum(on * np.cos(2 * np.pi * (t - ph) / period)))
beat = np.cos(2 * np.pi * (t - phase) / period)                 # +1 on the beat


def noise(sec, amp):
    return smooth(rng.normal(0, 1, N), sec) * amp * np.sqrt(sec * FPS)


yaw = FOLLOW * 14.0 * smooth(gx, 0.5) + noise(1.6, 0.9 * NOISE)
pitch = -SAD_DOWN * sad + FOLLOW * 9.0 * smooth(gy, 0.5) + 3.0 * acc - NOD * (0.5 + smile) * smooth(np.clip(beat, 0, 1) ** 2, 0.05) + noise(1.3, 0.6 * NOISE)
roll = TILT * side * (0.35 + 0.65 * np.maximum(smile, sad)) + noise(1.9, 0.6 * NOISE)
res = {}
for name, v in (("yaw", yaw), ("pitch", pitch), ("roll", roll)):
    v = smooth(v, 0.12)
    step = SPEED / FPS
    for i in range(1, N):                                         # speed limit
        v[i] = v[i - 1] + np.clip(v[i] - v[i - 1], -step, step)
    res[name] = v
# Body (BODY=1): feet stay planted, so only rotations above the pelvis. A sway of the spine over two beats, a slow
# twist over four, a breath before every phrase (chest back, both shoulders up, then released over the phrase), a small
# shoulder bounce on the beat where the sheet smiles, and the upper arms giving way against the sway.
extra = {}
if int(os.environ.get("BODY", 1)):
    energy = np.clip(0.35 + 0.65 * smile + 0.4 * acc - 0.3 * sad, 0.15, 1.2)
    sway = smooth(np.sin(np.pi * (t - phase) / period) * E("SWAY", 2.6) * energy, 0.1)            # degrees, whole spine
    twist = smooth(np.sin(0.5 * np.pi * (t - phase) / period + 0.7) * E("TWIST", 3.0) * energy, 0.2)
    breath = np.zeros(N)
    for a, b, v in score["phrases"]:
        k = (t >= a - 0.55) & (t < a + 0.1)
        breath[k] = 1
        k2 = (t >= a + 0.1) & (t < b)
        breath[k2] = np.maximum(breath[k2], np.linspace(0.8, 0.0, int(k2.sum())))
    breath = smooth(breath, 0.22)
    bounce = smooth(np.clip(beat, 0, 1) ** 2, 0.05) * smile
    lean = -2.0 * sad + 1.5 * breath                                                              # chest pitch, + is back/up
    z = np.zeros(N)
    for bone, share in (("spine_01", 0.3), ("spine_02", 0.35), ("spine_03", 0.35)):
        extra[bone] = {"yaw": (twist * share).round(3).tolist(), "pitch": (lean * share).round(3).tolist(), "roll": (sway * share).round(3).tolist()}
    sh = E("SHOULDER", 3.0) * breath + 1.2 * bounce
    extra["clavicle_l"] = {"yaw": z.tolist(), "pitch": z.tolist(), "roll": (-sh - 0.25 * sway).round(3).tolist()}
    extra["clavicle_r"] = {"yaw": z.tolist(), "pitch": z.tolist(), "roll": (sh - 0.25 * sway).round(3).tolist()}
    arm = -0.8 * sway
    extra["upperarm_l"] = {"yaw": (0.6 * twist).round(3).tolist(), "pitch": z.tolist(), "roll": arm.round(3).tolist()}
    extra["upperarm_r"] = {"yaw": (0.6 * twist).round(3).tolist(), "pitch": z.tolist(), "roll": arm.round(3).tolist()}
    # Arms (GESTURE, 0 = hang): never dead straight (forearms a little bent, arms a little off the hips). On a phrase
    # the sheet marks bright (smile > 0.5) one hand comes up in front of the chest, the side alternating, both hands on
    # the brightest (smile >= 0.8); it rises over the phrase's first 0.8 s, pulses lightly on the beat and sinks after
    # the phrase. Sad phrases keep the arms down. Pitch + swings a hanging arm forward, roll + moves it to her right.
    # First try (render h3): the arms opened to the sides and the hands left the frame; less roll, more pitch, forearm turned in.
    G = E("GESTURE", 1.0)
    gR, gL, turn = np.zeros(N), np.zeros(N), 0
    for a, b, v in score["phrases"]:
        if v["smile"] <= 0.5 or v["sad"] > 0.3:
            continue
        k = (t >= a - 0.2) & (t < b + 0.3)
        if v["smile"] >= 0.8:
            gR[k], gL[k] = 1.0, 0.85
        elif turn % 2 == 0:
            gR[k] = 0.8
        else:
            gL[k] = 0.8
        turn += 1
    gR, gL = smooth(gR, 0.55) * G, smooth(gL, 0.55) * G
    pulse = 0.12 * smooth(np.clip(beat, 0, 1) ** 2, 0.06)
    for sd, g, sgn in (("r", gR, 1.0), ("l", gL, -1.0)):
        up = extra["upperarm_" + sd]
        lift = g * (1 + pulse)
        up["pitch"] = (4.0 + 24.0 * lift).round(3).tolist()
        up["roll"] = (np.array(up["roll"]) + sgn * (4.0 + 2.0 * lift)).round(3).tolist()
        extra["lowerarm_" + sd] = {"yaw": (sgn * 14.0 * lift).round(3).tolist(), "pitch": (12.0 + 50.0 * lift).round(3).tolist(), "roll": z.tolist()}
        extra["hand_" + sd] = {"yaw": z.tolist(), "pitch": (10.0 * lift).round(3).tolist(), "roll": (sgn * 8.0 * lift).round(3).tolist()}
    # the head stays level while the spine sways under it: half of the sway is taken back at the head
    res["roll"] = res["roll"] - 0.5 * sway
# Everything starts from the rest pose and comes in over the first 0.8 s. A render that began in the middle of a pose
# made the hair fly for half a second: the warm-up frames run without this layer (seen 2026-11-14, frames 0 to 15).
fade = np.clip(t / 0.8, 0, 1)
fade = fade * fade * (3 - 2 * fade)
res = {k: v * fade for k, v in res.items()}
extra = {bn: {k: (np.array(v) * fade).round(3).tolist() for k, v in ch.items()} for bn, ch in extra.items()}
json.dump({"fps": FPS, "bpm": 60 / period, "beat_phase_s": float(phase), "extra": extra, **{k: np.round(v, 3).tolist() for k, v in res.items()}}, open(out, "w"))
print("HEAD frames", N, "bpm", round(60 / period, 2), "phase", round(float(phase), 3), {k: [round(float(v.min()), 1), round(float(v.max()), 1)] for k, v in res.items()})

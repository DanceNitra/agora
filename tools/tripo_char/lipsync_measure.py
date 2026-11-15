"""Measure, on rendered frames, how the mouth follows the face animation and the song.

    .venv_mp/Scripts/python.exe lipsync_measure.py <frames_dir> <curves.json> <vocals_16k_mono.raw> [fps]

MediaPipe gives the inner lip gap of every frame (in units of the interocular distance). It is compared with the
animation's own jawOpen curve (the same signal before rendering): the lag between them is the timing error the render
and the frame numbering add, and it must be 0 frames. The lag against the loudness of the vocals is printed too; it is
loose by nature, because loudness is not mouth opening."""
import glob
import json
import sys

import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions, vision

MODEL = r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit\models\face_landmarker.task"
frames, curves_p, raw = sys.argv[1], sys.argv[2], sys.argv[3]
fps = float(sys.argv[4]) if len(sys.argv) > 4 else 30.0
det = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(base_options=BaseOptions(model_asset_path=MODEL), num_faces=1))
fs = sorted(glob.glob(frames + "/*.png"))
gap, miss, width = [], 0, []
for i, f in enumerate(fs):
    r = det.detect(mp.Image.create_from_file(f))
    if not r.face_landmarks:
        gap.append(np.nan)
        width.append(np.nan)
        miss += 1
        continue
    L = np.array([[p.x, p.y] for p in r.face_landmarks[0]])
    L[:, 0] *= 9 / 16                                 # portrait frame: x in the same unit as y
    gap.append(np.linalg.norm(L[13] - L[14]) / np.linalg.norm(L[33] - L[263]))
    width.append(np.linalg.norm(L[61] - L[291]) / np.linalg.norm(L[33] - L[263]))   # mouth corner to corner
    if i % 150 == 0:
        print("frame", i, "of", len(fs), flush=True)
gap = np.array(gap)
ok = ~np.isnan(gap)
gap[~ok] = np.interp(np.nonzero(~ok)[0], np.nonzero(ok)[0], gap[ok])
c = json.load(open(curves_p))
jt, jv = next(v for k, v in c.items() if k.lower().endswith("jawopen"))
t = np.arange(len(gap)) / fps
jaw = np.interp(t, jt, jv)


def best_lag(a, b, span):
    a, b = (a - a.mean()) / a.std(), (b - b.mean()) / b.std()
    out = []
    for L in range(-span, span + 1):
        x, y = (a[L:], b[:len(b) - L]) if L >= 0 else (a[:L], b[-L:])
        out.append(float(np.mean(x * y)))
    return int(np.argmax(out)) - span, max(out), out[span]


lag, cmax, c0 = best_lag(gap, jaw, 8)
v = np.fromfile(raw, np.int16).astype(np.float32) / 32768
env = np.sqrt(np.convolve(v ** 2, np.ones(533) / 533, "same"))[:: int(16000 / fps)][:len(gap)]
lag2, cmax2, c02 = best_lag(gap[:len(env)], env, 12)
rep = {"frames": len(fs), "frames_without_face": miss, "lip_gap_range_iod": [round(float(gap.min()), 3), round(float(gap.max()), 3)],
       "render_vs_animation": {"lag_frames": lag, "lag_ms": round(lag / fps * 1000), "correlation": round(cmax, 3), "correlation_at_zero": round(c0, 3)},
       "render_vs_vocal_loudness": {"lag_frames": lag2, "lag_ms": round(lag2 / fps * 1000), "correlation": round(cmax2, 3), "correlation_at_zero": round(c02, 3)}}
print("LIPSYNC MEASURE", json.dumps(rep))
width = np.array(width)
width[~ok] = np.interp(np.nonzero(~ok)[0], np.nonzero(ok)[0], width[ok])
json.dump({"report": rep, "gap": gap.round(4).tolist(), "width": width.round(4).tolist()}, open(frames.rstrip("/\\") + "_measure.json", "w"))

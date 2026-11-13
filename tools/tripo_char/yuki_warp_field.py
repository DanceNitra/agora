"""Displacement field that moves a head's face landmarks onto the concept's, in the head's own front plane.

    .venv_mp/Scripts/python.exe yuki_warp_field.py <front.png> <maps.json> <concept.png> <field.json> [gain] [observed.png]

<front.png> and <maps.json> come from `yuki_head_warp.py -- render` (orthographic front render and its camera).
MediaPipe finds 468 landmarks in both pictures. The concept's landmarks are laid over the render's by a similarity
transform (Procrustes over all points), so head size, place and tilt do not count as shape. What is left at each
landmark is the move this head needs, converted to metres (x to the image right, z up).
The concept smiles and the head is neutral: the lips keep their own shape and only follow the mean move of the mouth,
so the smile is not built into the neutral face (it belongs to the rig).
With <observed.png> (a front render of the finished MetaHuman in Unreal, long lens) the moves are measured there, not on
<front.png>: the field then also takes out what the conform and the build add on top of the target. The control points
stay on <front.png>, landmark for landmark. The brows are left out of the field: on the finished head they are paint.
Writes the control points and their moves, and prints the distance before the warp in percent of the interocular
distance (IOD), the same measure face_measure.py reports.
"""
import json
import sys

import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions, vision

MODEL = r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit\models\face_landmarker.task"
front_p, maps_p, concept_p, out_p = sys.argv[1:5]
GAIN = float(sys.argv[5]) if len(sys.argv) > 5 else 1.0
cfg = json.load(open(maps_p))
det = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(base_options=BaseOptions(model_asset_path=MODEL), num_faces=1))


def marks(path):
    im = mp.Image.create_from_file(path)
    r = det.detect(im)
    if not r.face_landmarks:
        raise SystemExit("no face found in " + path)
    return np.array([[l.x * im.width, l.y * im.height] for l in r.face_landmarks[0]])[:468]


F, C = marks(front_p), marks(concept_p)
OBS = sys.argv[6] if len(sys.argv) > 6 else None
R = marks(OBS) if OBS else F
ca, cb = C.mean(0), R.mean(0)
A, B = C - ca, R - cb
U, S, Vt = np.linalg.svd(A.T @ B)
Rot = U @ Vt
if np.linalg.det(Rot) < 0:
    U[:, -1] *= -1
    Rot = U @ Vt
Ca = S.sum() / (A ** 2).sum() * A @ Rot + cb            # concept landmarks in render pixels
d = Ca - R
iod = np.linalg.norm(R[33] - R[263])
LIPS = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409, 270, 269, 267, 0, 37, 39, 40, 185,
        78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308, 415, 310, 311, 312, 13, 82, 81, 80, 191]
dist = np.linalg.norm(d, axis=1) / iod * 100
d[LIPS] = d[LIPS].mean(0)
m_per_px = cfg["ortho"] / cfg["res"]
pts = np.stack([(F[:, 0] - cfg["res"] / 2) * m_per_px + cfg["cx"], (cfg["res"] / 2 - F[:, 1]) * m_per_px + cfg["cz"]], 1)
iod_m = float(np.linalg.norm(F[33] - F[263]) * m_per_px)
mov = np.stack([d[:, 0], -d[:, 1]], 1) / iod * iod_m * GAIN     # pixels of the measured picture -> metres on the target
BROWS_ALL = [70, 63, 105, 66, 107, 55, 65, 52, 53, 46, 336, 296, 334, 293, 300, 276, 283, 282, 295, 285]
use = np.array([i for i in range(len(F)) if not (OBS and i in BROWS_ALL)])
pts, mov = pts[use], mov[use]
json.dump({"points_xz_m": pts.round(5).tolist(), "moves_xz_m": mov.round(5).tolist(), "iod_m": iod_m, "gain": GAIN, "observed": OBS,
           "before_pct_iod": {"mean": round(float(dist.mean()), 2), "p90": round(float(np.percentile(dist, 90)), 2)}}, open(out_p, "w"))
print("FIELD before warp: mean %.2f %% IOD, p90 %.2f; IOD %.1f mm; mean move %.2f mm, max %.2f mm" % (
    dist.mean(), np.percentile(dist, 90), iod_m * 1000, np.linalg.norm(mov, axis=1).mean() * 1000, np.linalg.norm(mov, axis=1).max() * 1000))

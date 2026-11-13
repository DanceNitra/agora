"""Measure how far a rendered face is from the concept face, from MediaPipe's 478 landmarks.

    .venv_mp/Scripts/python.exe face_measure.py <concept.png> <candidate.png> <out_dir> [tag]

The candidate's landmarks are aligned to the concept's by a similarity transform (Procrustes over all points). Reports
the mean and 90th percentile landmark distance in percent of the concept's interocular distance (IOD, outer eye
corners), the same per region, and a table of proportions (each a ratio to IOD) for both faces. Writes
<tag>_measure.json and <tag>_overlay.png (concept with its points in green and the aligned candidate points in red).
A number here says where the shapes differ in a front view; it does not judge skin, colour or expression style.
"""
import json
import sys
from pathlib import Path

import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions, vision
from PIL import Image, ImageDraw

MODEL = r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit\models\face_landmarker.task"
concept_p, cand_p, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
tag = sys.argv[4] if len(sys.argv) > 4 else "face"
out.mkdir(parents=True, exist_ok=True)
det = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(base_options=BaseOptions(model_asset_path=MODEL), num_faces=1))


def marks(path):
    im = mp.Image.create_from_file(path)
    r = det.detect(im)
    if not r.face_landmarks:
        raise SystemExit("no face found in " + path)
    return np.array([[l.x * im.width, l.y * im.height] for l in r.face_landmarks[0]])


def d(P, a, b):
    return float(np.linalg.norm(P[a] - P[b]))


def props(P):
    iod = d(P, 33, 263)
    return {
        "eye_width": (d(P, 33, 133) + d(P, 362, 263)) / 2 / iod,
        "eye_open": (d(P, 159, 145) + d(P, 386, 374)) / 2 / iod,
        "eye_gap_inner": d(P, 133, 362) / iod,
        "eye_slant_deg": float(np.degrees(np.arctan2(P[133][1] - P[33][1], P[133][0] - P[33][0]) - np.arctan2(P[362][1] - P[263][1], P[263][0] - P[362][0]))) / 2,
        "brow_to_eye": (d(P, 105, 159) + d(P, 334, 386)) / 2 / iod,
        "nose_width": d(P, 129, 358) / iod,
        "nose_length": d(P, 168, 2) / iod,
        "mouth_width": d(P, 61, 291) / iod,
        "lip_height": d(P, 0, 17) / iod,
        "nose_to_mouth": d(P, 2, 13) / iod,
        "mouth_to_chin": d(P, 13, 152) / iod,
        "face_width_cheeks": d(P, 234, 454) / iod,
        "jaw_width": d(P, 172, 397) / iod,
        "face_height_brow_chin": d(P, 9, 152) / iod,
    }


REGIONS = {"eyes": list(range(33, 34)) + [133, 159, 145, 362, 263, 386, 374, 468, 473, 160, 158, 153, 144, 385, 387, 380, 373],
           "brows": [70, 63, 105, 66, 107, 336, 296, 334, 293, 300],
           "nose": [1, 2, 4, 5, 98, 327, 129, 358, 168, 6, 197, 195],
           "mouth": [61, 291, 0, 17, 13, 14, 37, 267, 84, 314, 40, 270],
           "jaw_chin": [152, 148, 377, 172, 397, 136, 365, 150, 379, 234, 454, 132, 361]}
C, K = marks(concept_p), marks(cand_p)
ca, cb = K.mean(0), C.mean(0)
A, B = K - ca, C - cb
U, S, Vt = np.linalg.svd(A.T @ B)
R = (U @ Vt)
if np.linalg.det(R) < 0:
    U[:, -1] *= -1
    R = U @ Vt
sc = S.sum() / (A ** 2).sum()
Ka = sc * A @ R + cb
iod = d(C, 33, 263)
dist = np.linalg.norm(Ka - C, axis=1) / iod * 100
pc, pk = props(C), props(K)
rep = {"concept": concept_p, "candidate": cand_p, "landmark_dist_pct_iod": {"mean": round(float(dist.mean()), 2), "p90": round(float(np.percentile(dist, 90)), 2)},
       "by_region_mean_pct_iod": {k: round(float(dist[v].mean()), 2) for k, v in REGIONS.items()},
       "proportions": {k: {"concept": round(pc[k], 3), "candidate": round(pk[k], 3),
                           "diff_pct": round((pk[k] - pc[k]) / abs(pc[k]) * 100, 1) if k != "eye_slant_deg" else round(pk[k] - pc[k], 1)} for k in pc}}
(out / f"{tag}_measure.json").write_text(json.dumps(rep, indent=1))
im = Image.open(concept_p).convert("RGB")
dr = ImageDraw.Draw(im)
r = max(2, im.width // 500)
for p, q in zip(C, Ka):
    dr.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=(0, 255, 0))
    dr.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r], fill=(255, 0, 0))
im.thumbnail((1400, 1400))
im.save(out / f"{tag}_overlay.png")
print("MEASURE", tag, json.dumps(rep["landmark_dist_pct_iod"]), json.dumps(rep["by_region_mean_pct_iod"]))
for k, v in rep["proportions"].items():
    print("  %-22s concept %6.3f  candidate %6.3f  diff %+6.1f" % (k, v["concept"], v["candidate"], v["diff_pct"]))

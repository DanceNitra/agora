"""Eye opening metrics from MediaPipe landmarks: how open and how round each eye is, and how much of the iris the lids cover."""
import sys
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions, vision
MODEL = r"C:/Users/Danculus/agora/agora_output/reverse/gpt-image-2-6-personas/3d/ue/fit/models/face_landmarker.task"
det = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(base_options=BaseOptions(model_asset_path=MODEL), num_faces=1))
EYES = {"R": dict(out=33, inn=133, up=159, lo=145, iris=(468, 469, 470, 471, 472)),
        "L": dict(out=263, inn=362, up=386, lo=374, iris=(473, 474, 475, 476, 477))}
for p in sys.argv[1:]:
    im = mp.Image.create_from_file(p)
    r = det.detect(im)
    if not r.face_landmarks:
        print(p, "NO FACE"); continue
    P = np.array([(l.x * im.width, l.y * im.height) for l in r.face_landmarks[0]])
    iod = np.linalg.norm(P[468] - P[473])
    row = []
    for k, e in EYES.items():
        w = np.linalg.norm(P[e["out"]] - P[e["inn"]])
        h = np.linalg.norm(P[e["up"]] - P[e["lo"]])
        c = P[e["iris"][0]]
        d = np.mean([np.linalg.norm(P[e["iris"][1]] - P[e["iris"][3]]), np.linalg.norm(P[e["iris"][2]] - P[e["iris"][4]])])
        top_cover = (P[e["up"]][1] - (c[1] - d / 2)) / d      # fraction of iris diameter hidden under the upper lid
        bot_gap = ((c[1] + d / 2) - P[e["lo"]][1]) / d        # >0: lower lid covers iris bottom; <0: white shows under it
        tilt = np.degrees(np.arctan2(-(P[e["out"]][1] - P[e["inn"]][1]), abs(P[e["out"]][0] - P[e["inn"]][0])))
        row.append(f"{k}: open/width {h/w:.2f} iris/open {d/h:.2f} iris/width {d/w:.2f} top_cover {top_cover:+.2f} bottom {bot_gap:+.2f} tilt {tilt:+.1f} width/IOD {w/iod:.2f}")
    print(p.split('/')[-1][:40], "|", " | ".join(row))

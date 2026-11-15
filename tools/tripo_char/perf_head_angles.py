"""Head yaw, pitch and roll of a filmed performer, per frame at 30 fps, from MediaPipe face landmarks, in the terms of
ue_yuki_head_additive: yaw + = toward the character's left, pitch + = up, roll + = the head tilting to the character's
left shoulder. Camera frame: X image right, Y up, Z toward the camera; ex = right outer eye corner (33) to left outer
eye corner (263), ey = chin (152) to forehead (10) made orthogonal to ex, ez = ex x ey = where the face points.
Values are relative to the clip's median pose and smoothed over 5 frames.

Why not the solve's own head curves: MetaHuman Animator's mono solve writes HeadYaw/HeadPitch/HeadRoll on the face
only, with a 27 to 35 degree offset and axes that did not match their names (measured on the Sinead clip, 2026-11-15).

    .venv_mp/Scripts/python.exe perf_head_angles.py <video> <out.json>"""
import json
import sys

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions, vision

MODEL = r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit\models\face_landmarker.task"
video, out = sys.argv[1], sys.argv[2]
det = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=MODEL), running_mode=vision.RunningMode.VIDEO, num_faces=1))
cap = cv2.VideoCapture(video)
fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
T, A, i = [], [], 0
while True:
    ok, fr = cap.read()
    if not ok:
        break
    H, W = fr.shape[:2]
    r = det.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)), int(i / fps * 1000))
    if r.face_landmarks:
        L = r.face_landmarks[0]
        V = lambda k: np.array([L[k].x * W, -L[k].y * H, -L[k].z * W])
        ex = V(263) - V(33)
        ex /= np.linalg.norm(ex)
        ey = V(10) - V(152)
        ey -= ex * (ey @ ex)
        ey /= np.linalg.norm(ey)
        ez = np.cross(ex, ey)
        A.append((np.degrees(np.arctan2(ez[0], ez[2])), np.degrees(np.arctan2(ez[1], np.hypot(ez[0], ez[2]))),
                  -np.degrees(np.arctan2(ex[1], ex[0]))))
        T.append(i / fps)
    i += 1
    if i % 300 == 0:
        print(f"HEADANG frame {i} face {len(T)}", flush=True)
T, A = np.array(T), np.array(A)
med = np.median(A, axis=0)
t30 = np.arange(int(round(i / fps * 30))) / 30.0
res = {"fps": 30.0, "source_frames": i, "face_frames": len(T), "median_deg": med.round(2).tolist()}
for j, nm in enumerate(("yaw", "pitch", "roll")):
    v = np.interp(t30, T, A[:, j] - med[j])
    res[nm] = np.convolve(np.pad(v, 2, mode="edge"), np.ones(5) / 5, "valid").tolist()
json.dump(res, open(out, "w"))
print("HEADANG", len(t30), "frames at 30 fps; face found in", len(T), "of", i, "; median", med.round(1).tolist(),
      "; range yaw", round(min(res["yaw"]), 1), round(max(res["yaw"]), 1), "pitch", round(min(res["pitch"]), 1),
      round(max(res["pitch"]), 1), "roll", round(min(res["roll"]), 1), round(max(res["roll"]), 1), flush=True)

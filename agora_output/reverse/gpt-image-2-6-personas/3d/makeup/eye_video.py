"""Eye close-up video from a full-resolution render: MediaPipe finds the eye corners in every frame, the centre is
smoothed over time, and a fixed-size window follows it. Usage: eye_video.py <frames_dir> <out_dir>"""
import sys, os
from pathlib import Path
import cv2, numpy as np, mediapipe as mp
from mediapipe.tasks.python import vision, BaseOptions
MODEL = str(Path(__file__).resolve().parents[1] / "ue" / "fit" / "models" / "face_landmarker.task")
det = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(base_options=BaseOptions(model_asset_path=MODEL), num_faces=1))
src, out = Path(sys.argv[1]), Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
files = sorted(src.glob("*.png"))
W, H, S = (int(sys.argv[3]), int(sys.argv[4]), 4) if len(sys.argv) > 4 else (1280, 560, 4)  # crop size; detection on 1/4 scale
DY = int(sys.argv[5]) if len(sys.argv) > 5 else 0  # shift the window up (negative) or down
cs = []
for i, f in enumerate(files):
    im = cv2.imread(str(f))
    sm = cv2.resize(im, (im.shape[1] // S, im.shape[0] // S))
    r = det.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(sm, cv2.COLOR_BGR2RGB)))
    if r.face_landmarks:
        lm = r.face_landmarks[0]
        pts = [(lm[k].x * im.shape[1], lm[k].y * im.shape[0]) for k in (33, 133, 362, 263)]
        cs.append(np.mean(pts, 0))
    else:
        cs.append(cs[-1] if cs else np.array([im.shape[1] / 2, im.shape[0] * 0.4]))
    if i % 50 == 0:
        print("track", i, len(files), flush=True)
cs = np.array(cs)
k = 9
sm = np.array([cs[max(0, i - k):i + k + 1].mean(0) for i in range(len(cs))])
for i, f in enumerate(files):
    im = cv2.imread(str(f))
    x0 = int(np.clip(sm[i][0] - W / 2, 0, im.shape[1] - W)); y0 = int(np.clip(sm[i][1] + DY - H / 2, 0, im.shape[0] - H))
    cv2.imwrite(str(out / f.name), im[y0:y0 + H, x0:x0 + W])
print("done", len(files))

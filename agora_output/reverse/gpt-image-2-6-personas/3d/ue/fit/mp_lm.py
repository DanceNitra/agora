"""Full-face 2D landmarks with MediaPipe Face Landmarker (478 points).
Usage: python mp_lm.py <image> [overlay.png]  -> prints JSON [[x,y],...] in pixels."""
import json, sys
from pathlib import Path
import cv2, numpy as np, mediapipe as mp
from mediapipe.tasks.python import vision, BaseOptions

MODEL = str(Path(__file__).with_name("models") / "face_landmarker.task")
_det = None

def detect(path):
    global _det
    if _det is None:
        _det = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=MODEL), num_faces=1))
    img = cv2.imread(str(path))
    h, w = img.shape[:2]
    r = _det.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(img, cv2.COLOR_BGR2RGB)))
    if not r.face_landmarks:
        return None
    return np.array([[p.x * w, p.y * h] for p in r.face_landmarks[0]])

def overlay(path, pts, out):
    img = cv2.imread(str(path))
    for x, y in pts:
        cv2.circle(img, (int(x), int(y)), 1, (0, 255, 0), -1)
    cv2.imwrite(str(out), img)

if __name__ == "__main__":
    p = detect(sys.argv[1])
    if p is None:
        sys.exit("no face")
    if len(sys.argv) > 2:
        overlay(sys.argv[1], p, sys.argv[2])
    print(json.dumps(p.round(2).tolist()))

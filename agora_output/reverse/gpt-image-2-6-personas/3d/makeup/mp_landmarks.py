"""MediaPipe 478 face landmarks for a list of images. Usage: mp_landmarks.py <out.json> <img>... -> {img: [[x,y,z],...]}"""
import json, sys
import mediapipe as mp
from mediapipe.tasks.python import vision, BaseOptions
det = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit\models\face_landmarker.task"), num_faces=1))
out = {}
for i, p in enumerate(sys.argv[2:]):
    im = mp.Image.create_from_file(p)
    r = det.detect(im)
    if r.face_landmarks:
        out[p] = [[l.x * im.width, l.y * im.height, l.z * im.width] for l in r.face_landmarks[0]]
    if i % 20 == 0:
        print("mp", i, len(sys.argv) - 2, flush=True)
json.dump(out, open(sys.argv[1], "w"))
print("done", len(out))

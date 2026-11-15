"""MediaPipe face landmarks on two front renders of the same camera (the Tripo head and the aligned MetaHuman skin,
from yuki_tripo_face_shapes.py MODE=lm), for the thin-plate warp of path T.

    .venv_mp/Scripts/python.exe yuki_face_lm_pair.py <dir with lm_tripo.png and lm_mh.png>

Writes lm.json: normalized (u, v) of all 478 landmarks per image and the indices used for the warp (eye lids, lips
inner and outer, nose, brows, lower face oval), plus lm_overlay.jpg with both sets drawn on both images."""
import json
import sys
from pathlib import Path

import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions, vision
from PIL import Image, ImageDraw

MODEL = r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit\models\face_landmarker.task"
d = Path(sys.argv[1])
FM = mp.solutions.face_mesh if hasattr(mp, "solutions") else None
EYES = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246,
        362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
LIPS_IN = [78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308, 415, 310, 311, 312, 13, 82, 81, 80, 191]
LIPS_OUT = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409, 270, 269, 267, 0, 37, 39, 40, 185]
NOSE = [1, 2, 4, 5, 6, 98, 327, 168, 197, 195, 64, 294]
BROWS = [70, 63, 105, 66, 107, 336, 296, 334, 293, 300]
OVAL = [152, 148, 176, 149, 150, 136, 172, 377, 400, 378, 379, 365, 397]
USE = EYES + LIPS_IN + LIPS_OUT + NOSE + BROWS + OVAL
det = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=MODEL), num_faces=1))
out = {"use": USE}
ims = {}
for key, fn in (("tripo", "lm_tripo.png"), ("mh", "lm_mh.png")):
    im = Image.open(d / fn).convert("RGB")
    r = det.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.asarray(im)))
    if not r.face_landmarks:
        raise SystemExit(f"no face found in {fn}")
    out[key] = [[p.x, p.y] for p in r.face_landmarks[0]]
    ims[key] = im
    print(key, "landmarks", len(out[key]))
json.dump(out, open(d / "lm.json", "w"))
W = 700
sheet = Image.new("RGB", (W * 2, W), "white")
for j, key in enumerate(("tripo", "mh")):
    im = ims[key].resize((W, W))
    dr = ImageDraw.Draw(im)
    for k2, col in (("tripo", (0, 255, 0)), ("mh", (255, 0, 0))):
        for i in USE:
            x, y = out[k2][i][0] * W, out[k2][i][1] * W
            dr.ellipse((x - 2, y - 2, x + 2, y + 2), fill=col)
    sheet.paste(im, (j * W, 0))
sheet.save(d / "lm_overlay.jpg", quality=90)
a, b = np.array(out["tripo"])[USE], np.array(out["mh"])[USE]
print("shift px (1024)", np.round(np.linalg.norm(a - b, axis=1).mean() * 1024, 1), "max", np.round(np.linalg.norm(a - b, axis=1).max() * 1024, 1))

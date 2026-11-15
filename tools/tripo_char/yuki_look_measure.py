"""Colour of a few face points in each look render against the unlit texture render ("ref") of the same frame.

    .venv_mp/Scripts/python.exe yuki_look_measure.py <looks dir>

Points from MediaPipe on the ref image: cheeks (50, 280), forehead (151), nose tip (4), lips (13, 14, 0, 17), irises
(468, 473), chin (152). For every look: mean RGB (0..255) in a 7 px box at each point, the distance to ref, the
brightness ratio (look / ref) and the saturation of the cheek colour. Writes look_measure.json and look_sheet.jpg."""
import json
import sys
from collections import defaultdict
from pathlib import Path

import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions, vision
from PIL import Image, ImageDraw

MODEL = r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit\models\face_landmarker.task"
d = Path(sys.argv[1])
det = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(base_options=BaseOptions(model_asset_path=MODEL), num_faces=1))
# skin points only: in the unlit reference the eyeballs and the mouth inside render black (no light reaches them), so
# iris and lip points measured the lighting of those parts, not the face colour (first run, 2026-11-14)
PTS = {"cheek_l": 50, "cheek_r": 280, "forehead": 151, "nose": 4, "chin": 152, "temple_l": 54, "temple_r": 284}
refs = sorted(d.glob("look_ref_*.png"))
looks = sorted({p.name.split("_")[1] for p in d.glob("look_*.png")} - {"ref"})
res = defaultdict(lambda: defaultdict(list))
for rp in refs:
    stem = rp.stem.replace("look_ref_", "")
    ref = np.asarray(Image.open(rp).convert("RGB")).astype(float)
    r = det.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=ref.astype(np.uint8)))
    if not r.face_landmarks:
        print("no face in", rp.name)
        continue
    lm = r.face_landmarks[0]
    h, w = ref.shape[:2]

    def col(img, k):
        x, y = int(lm[PTS[k]].x * w), int(lm[PTS[k]].y * h)
        return img[max(0, y - 3):y + 4, max(0, x - 3):x + 4].reshape(-1, 3).mean(0)

    for lk in looks:
        im = np.asarray(Image.open(d / f"look_{lk}_{stem}.png").convert("RGB")).astype(float)
        for k in PTS:
            a, b = col(im, k), col(ref, k)
            res[lk]["dist"].append(float(np.linalg.norm(a - b)))
            res[lk]["bright"].append(float(a.mean() / max(b.mean(), 1)))
        c = (col(im, "cheek_l") + col(im, "cheek_r")) / 2
        cr = (col(ref, "cheek_l") + col(ref, "cheek_r")) / 2
        res[lk]["sat"].append(float((c.max() - c.min()) / max(c.max(), 1)))
        res[lk]["sat_ref"].append(float((cr.max() - cr.min()) / max(cr.max(), 1)))
out = {lk: {k: round(float(np.mean(v)), 3) for k, v in m.items()} for lk, m in res.items()}
for lk, m in out.items():
    print(f"{lk:7s} colour distance to the texture {m['dist']:6.1f}  brightness x{m['bright']:.2f}  cheek saturation {m['sat']:.2f} (texture {m['sat_ref']:.2f})")
json.dump(out, open(d / "look_measure.json", "w"), indent=1)
# sheet: rows = frames, columns = ref + looks
cols = ["ref"] + looks
W = 420
sheet = Image.new("RGB", (W * len(cols), (W + 26) * len(refs)), "white")
dr = ImageDraw.Draw(sheet)
for i, rp in enumerate(refs):
    stem = rp.stem.replace("look_ref_", "")
    for j, lk in enumerate(cols):
        im = Image.open(d / f"look_{lk}_{stem}.png").convert("RGB")
        w0, h0 = im.size
        im = im.crop((int(w0 * 0.18), int(h0 * 0.12), int(w0 * 0.82), int(h0 * 0.76))).resize((W, W))
        sheet.paste(im, (j * W, i * (W + 26) + 26))
        if i == 0:
            lbl = "texture (unlit)" if lk == "ref" else lk
            dr.text((j * W + 8, 6), lbl, fill="black")
sheet.save(d / "look_sheet.jpg", quality=92)

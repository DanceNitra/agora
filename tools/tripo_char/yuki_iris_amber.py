"""Recolour a baked MetaHuman iris base colour (T_EyeIris*_BC, exported by ue_yuki_eyes.py) to Yuki's amber.

    .venv_mp/Scripts/python.exe yuki_iris_amber.py <Iris_Basecolor_Baked.png> <out.png>

The baked iris keeps its fibre pattern and pupil; only the colour changes. The colour is a radial ramp read off the
concept (a_flare_clean.png): yellow gold at the pupil, orange amber in the middle, a dark brown rim. The fibre detail
is the original luminance divided by its own blur, so it survives as a modulation of the ramp.
"""
import sys

import cv2
import numpy as np

src, dst = sys.argv[1], sys.argv[2]
im = cv2.imread(src, cv2.IMREAD_COLOR).astype(np.float32) / 255.0
h, w = im.shape[:2]
lum = im.max(axis=2)
yy, xx = np.mgrid[0:h, 0:w]
dark = lum < 0.02                                    # pupil
m = cv2.moments(dark.astype(np.uint8))
cx, cy = m["m10"] / m["m00"], m["m01"] / m["m00"]
pupil_r = float(np.sqrt(dark.sum() / np.pi)) / (w / 2)
r = np.hypot(xx - cx, yy - cy) / (w / 2)
detail = np.clip(lum / np.maximum(cv2.GaussianBlur(lum, (0, 0), w / 40), 1e-4), 0.55, 1.6)
# radius, then sRGB colour (R, G, B)
PUPIL = 0.33                                         # the concept's pupil is about a third of the iris
RAMP = [(PUPIL, (0.84, 0.60, 0.22)), (0.50, (0.74, 0.47, 0.14)), (0.68, (0.56, 0.32, 0.08)),
        (0.82, (0.35, 0.18, 0.05)), (0.93, (0.11, 0.05, 0.02)), (1.5, (0.09, 0.04, 0.02))]
rs = np.array([p[0] for p in RAMP])
out = np.zeros_like(im)
for ch in range(3):
    out[..., 2 - ch] = np.interp(r, rs, np.array([p[1][ch] for p in RAMP]))
out *= (0.35 + 0.65 * detail)[..., None]
edge = np.clip((r - PUPIL * 0.97) / (PUPIL * 0.08), 0, 1)   # soft pupil edge
out *= edge[..., None]
cv2.imwrite(dst, (np.clip(out, 0, 1) * 255).astype(np.uint8))
print("IRIS pupil radius", round(pupil_r, 3), "centre", round(cx), round(cy), "mean rgb",
      [round(float(x), 3) for x in out[..., ::-1].reshape(-1, 3).mean(0)])

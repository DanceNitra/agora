"""Grade Yuki's base colour toward the concept, from measured Lab values (OpenCV 8-bit Lab).

Measured 2026-11-13 on matching regions:
  hair     concept L 183 a 141 b 131   model texture L 172 a 146 b 122  -> b +9, L +6 (less lavender)
  cheek    concept L 184 a 145 b 137   model texture L 188 a 147 b 137  -> already matches, untouched
  lips     concept L 120 a 163 b 145   model texture L 157 a 154 b 135  -> a +9, b +9, L -15 (coral)
The concept's lips are also darkened by its lighting, so L moves only part of the way.

  uvx --from opencv-python-headless --with numpy python grade_texture.py <work_dir>
Writes base_graded.png and before/after crops of the mouth and a hair patch.
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

work = Path(sys.argv[1])
img = cv2.imread(str(work / "base_color.png"))
H, W = img.shape[:2]
lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
lm = json.loads((work / "landmarks.json").read_text())


def px(name):
    u, v = lm[name]["uv"]
    return np.array([u * W, (1 - v) * H])


# Hair: the lavender band only. Skin (b >= 133) and neon pink outfit (a > 160) stay out.
hair = ((a > 136) & (a < 158) & (b > 106) & (b < 130) & (L > 115)).astype(np.float32)
hair = cv2.GaussianBlur(hair, (0, 0), 2)
b += 9 * hair
L += 6 * hair

# Lips: an ellipse spanned by the corners and the upper/lower points, gated by lip redness.
c, lc, rc, up, lo_ = px("lips"), px("lcorner"), px("rcorner"), px("upper"), px("lower")
axis = (rc - lc) / np.linalg.norm(rc - lc)
half_w = np.linalg.norm(rc - lc) / 2 * 1.15
half_h = np.linalg.norm(up - lo_) / 2 * 1.4
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
d = np.stack([xx - c[0], yy - c[1]], -1)
along = d @ axis
across = d @ np.array([-axis[1], axis[0]])
ell = np.clip(1.3 - np.sqrt((along / half_w) ** 2 + (across / half_h) ** 2) * 1.3, 0, 1)
red = np.clip((a - 148) / 5, 0, 1)
lips = cv2.GaussianBlur(ell * red, (0, 0), 1.5)
a += 9 * lips
b += 9 * lips
L -= 15 * lips
print("hair texels", int((hair > 0.5).sum()), "lip texels", int((lips > 0.5).sum()))

out = cv2.cvtColor(np.clip(lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)
cv2.imwrite(str(work / "base_graded.png"), out)
x0, y0 = int(c[0] - 80), int(c[1] - 80)
crop = lambda im: cv2.resize(im[y0:y0 + 160, x0:x0 + 160], (480, 480), interpolation=cv2.INTER_NEAREST)
cv2.imwrite(str(work / "grade_mouth_before_after.png"), np.hstack([crop(img), crop(out)]))
print("done")

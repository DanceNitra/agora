"""Second grading pass on Yuki's texture, from the independent audit of 2026-11-13.

On top of base_graded.png (hair, lips):
  - latex: dark plum (L < 110, a > 134) pulled to near black, so the neon reads on black like the concept;
  - neon: bright magenta trim (a > 160, L > 80) becomes an emission mask, written as neon_emit.png;
  - blush: a soft pink gradient on both cheeks;
  - eyeliner wings: a tapered dark stroke out and up from each outer eye corner, direction taken in
    texture space from the eye centre, the outer corner and the lower lid (the wing tips themselves
    sit under hair in the front view, so they cannot be ray-cast);
  - lower lids: dark lash smears below the lid lightened toward the surrounding skin.

  uvx --from opencv-python-headless --with numpy python grade_texture2.py <work_dir>
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

work = Path(sys.argv[1])
img = cv2.imread(str(work / "base_graded.png"))
H, W = img.shape[:2]
lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
lm = json.loads((work / "landmarks.json").read_text())


def px(name):
    u, v = lm[name]["uv"]
    return np.array([u * W, (1 - v) * H], dtype=np.float32)


# --- latex and neon (global, by colour) -------------------------------------------------------
# b < 132: the trim is magenta (bluish); the coral lips (b about 144 after grading) glowed in v2.
neon = ((a > 160) & (L > 80) & (b < 132)).astype(np.float32)
neon = cv2.GaussianBlur(neon, (0, 0), 1.2)
latex = ((L < 110) & (a > 134) & (b < 134)).astype(np.float32) * (1 - neon)
latex = cv2.GaussianBlur(latex, (0, 0), 1.0)
L -= latex * (L * 0.35)                 # darker, keeps the gloss highlights relative
a -= latex * (a - 128) * 0.7            # less plum, toward neutral black
b -= latex * (b - 128) * 0.7
emit = np.zeros_like(img)
emit[...] = (np.array([200, 60, 255]) * neon[..., None]).astype(np.uint8)   # BGR hot pink
cv2.imwrite(str(work / "neon_emit.png"), emit)
print("neon texels", int((neon > 0.5).sum()), "latex texels", int((latex > 0.5).sum()))

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)


def radial(center, radius):
    d = np.hypot(xx - center[0], yy - center[1]) / radius
    return np.clip(1 - d, 0, 1) ** 2


def segment_mask(p0, p1, w0, w1):
    """Tapered stroke from p0 (width w0) to p1 (width w1)."""
    d = p1 - p0
    t = np.clip(((xx - p0[0]) * d[0] + (yy - p0[1]) * d[1]) / (d @ d), 0, 1)
    cx, cy = p0[0] + t * d[0], p0[1] + t * d[1]
    dist = np.hypot(xx - cx, yy - cy)
    width = w0 + (w1 - w0) * t
    return np.clip(1 - dist / np.maximum(width, 0.5), 0, 1)


for side in ("L", "R"):
    eye, outer, lid = px("eye" + side), px("outer" + side), px("lid" + side)
    out_v = outer - eye
    eye_w = np.linalg.norm(out_v)
    up = eye - lid
    up /= np.linalg.norm(up)
    # Blush on the cheek (the cheek ray hit the same island as this eye only on the left; on the
    # right it is placed below the lid in texture space for the same reason).
    cheek = lid - up * eye_w * 1.1
    blush = radial(cheek, eye_w * 1.3) * (b > 128) * (L > 150)      # skin only
    a += 6 * blush
    L -= 3 * blush
    # Eyeliner wing.
    tip = outer + out_v / eye_w * eye_w * 0.45 + up * eye_w * 0.28
    wing = segment_mask(outer - out_v / eye_w * eye_w * 0.12, tip, eye_w * 0.05, eye_w * 0.008)
    # Measured 2026-11-13: the right wing landed as a detached dash past a UV island seam that cuts
    # through the eye, so wings stay off until they can be painted in 3D instead of texture space.
    wing = cv2.GaussianBlur(wing, (0, 0), 0.8) * (__import__("os").environ.get("WINGS") == "1")
    L -= wing * (L - 35)
    a -= wing * (a - 130)
    b -= wing * (b - 128)
    # Lower-lid smear: dark texels below the lid line, lightened toward the skin around them.
    region = radial(lid - up * eye_w * 0.15, eye_w * 0.55)
    below = ((xx - lid[0]) * up[0] + (yy - lid[1]) * up[1]) < 0
    skin_L = np.median(L[(region > 0.2) & (L > 150)]) if np.any((region > 0.2) & (L > 150)) else 190
    smear = region * below * np.clip((skin_L - 40 - L) / 30, 0, 1)
    L += smear * 0.7 * (skin_L - L)
    print(side, "eye width px", round(float(eye_w), 1), "smear texels", int((smear > 0.3).sum()))

out = cv2.cvtColor(np.clip(lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)
cv2.imwrite(str(work / "base_graded2.png"), out)
for side in ("L", "R"):
    c = px("eye" + side).astype(int)
    crop = lambda im: cv2.resize(im[c[1] - 90:c[1] + 90, c[0] - 90:c[0] + 90], (360, 360), interpolation=cv2.INTER_CUBIC)
    cv2.imwrite(str(work / f"grade2_eye{side}.png"), np.hstack([crop(img), crop(out)]))
print("done")

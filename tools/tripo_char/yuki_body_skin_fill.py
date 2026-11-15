"""Paint skin over the underwear in a MetaHuman body base colour.

    .venv_mp/Scripts/python.exe yuki_body_skin_fill.py <base_body_BC.png> <yuki_body_BC.png> <out.png>

The MetaHuman body texture carries a grey sports top and briefs. Under Yuki's own costume the chest above the corset
showed them (pale blue after the skin gain, stills c1 of 2026-11-14). The underwear is found in the ORIGINAL texture,
where it is the only neutral grey (skin there is orange), grown by a few texels, and filled in the working texture from
the skin round it: normalised blurs of growing radius, nearest first."""
import sys

import cv2
import numpy as np

base = cv2.imread(sys.argv[1], cv2.IMREAD_COLOR).astype(np.float32) / 255
work = cv2.imread(sys.argv[2], cv2.IMREAD_COLOR).astype(np.float32) / 255
if base.shape != work.shape:
    base = cv2.resize(base, (work.shape[1], work.shape[0]), interpolation=cv2.INTER_AREA)
b, g, r = base[..., 0], base[..., 1], base[..., 2]
grey = (np.abs(r - g) < 0.07) & (np.abs(g - b) < 0.07)
S = work.shape[0]
mask = cv2.dilate(grey.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (S // 200 * 2 + 1, S // 200 * 2 + 1)))
mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((S // 100, S // 100), np.uint8)).astype(np.float32)
src_w = 1 - mask
fill, left = np.zeros_like(work), mask.copy()
for k in (S / 400, S / 200, S / 100, S / 50, S / 25, S / 12, S / 6):
    wk = cv2.GaussianBlur(src_w, (0, 0), k)
    fk = cv2.GaussianBlur(work * src_w[..., None], (0, 0), k) / np.maximum(wk, 1e-4)[..., None]
    take = left * np.clip(wk * 4, 0, 1)
    fill += fk * take[..., None]
    left = left - take
fill += np.median(work[mask < 0.5], 0) * left[..., None]
# the fill came out paler than the skin beside it (0.905, 0.731, 0.674 against 0.968, 0.601, 0.588): padding blocks
# leak into the blurs. Its mean is set to the mean of a ring of real skin round the underwear.
ring = (cv2.dilate(mask.astype(np.uint8), np.ones((S // 40, S // 40), np.uint8)) > 0) & (mask < 0.5)
gain = work[ring].mean(0) / np.maximum(fill[mask > 0.5].mean(0), 1e-4)
fill = np.clip(fill * gain, 0, 1)
soft = cv2.GaussianBlur(mask, (0, 0), S / 500)
out = work * (1 - soft[..., None]) + fill * soft[..., None]
cv2.imwrite(sys.argv[3], (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8))
print("SKINFILL underwear share", round(float(mask.mean()), 3), "skin there now (rgb)", out[mask > 0.5].mean(0)[::-1].round(3), "skin elsewhere", work[mask < 0.5].mean(0)[::-1].round(3))

"""Whiten the teeth in a baked MetaHuman teeth base colour (exported by ue_yuki_teeth, STEP export).

    python yuki_teeth_white.py <teeth_BC_baked.png> <out.png> [desaturate 0..1] [gain]

Teeth are the bright, weakly saturated texels; gums and tongue are saturated red and stay. Inside a soft mask the
saturation is cut and the value raised, so the yellow cast goes and the shading of each tooth stays."""
import sys

import cv2
import numpy as np

src, dst = sys.argv[1], sys.argv[2]
DES, GAIN = (float(sys.argv[3]) if len(sys.argv) > 3 else 0.8), (float(sys.argv[4]) if len(sys.argv) > 4 else 1.12)
im = cv2.imread(src, cv2.IMREAD_UNCHANGED)
bgr = im[..., :3].astype(np.float32) / 255
hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
mask = np.clip((hsv[..., 2] - 0.35) / 0.15, 0, 1) * np.clip((0.5 - hsv[..., 1]) / 0.15, 0, 1)
mask = cv2.GaussianBlur(mask, (0, 0), 2)
before = bgr[mask > 0.9].mean(0)[::-1]
hsv[..., 1] *= 1 - DES * mask
hsv[..., 2] = np.clip(hsv[..., 2] * (1 + (GAIN - 1) * mask), 0, 1)
out = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
out[..., 0] = np.clip(out[..., 0] * (1 + 0.03 * mask), 0, 1)           # a touch of blue: reads as white under warm light
res = (out * 255 + 0.5).astype(np.uint8)
if im.shape[2] == 4:
    res = np.dstack([res, im[..., 3]])
cv2.imwrite(dst, res)
print("TEETH mask share", round(float((mask > 0.5).mean()), 3), "rgb before", before.round(3), "after", out[mask > 0.9].mean(0)[::-1].round(3))

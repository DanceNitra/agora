"""Overlay the head relief (convexity of the mesh, so the supraorbital ridge shows) on the brow area of the face
texture, with the brow fill outline on top. Usage: brow_bone_overlay.py <bc.png> <mask.png> <relief.json> <out.png>"""
import json, sys
import cv2, numpy as np
from scipy.interpolate import griddata
bc = cv2.imread(sys.argv[1]); H, W = bc.shape[:2]
mask = cv2.imread(sys.argv[2], 0)
R = np.array(json.load(open(sys.argv[3])))
L = np.array(json.load(open("keenface/alb_landmarks.json"))) * (W / 2048)
pts = L[[70, 63, 105, 66, 107, 46, 53, 52, 65, 55, 300, 293, 334, 296, 336, 276, 283, 282, 295, 285]]
x0, y0 = (pts.min(0) - 260 * W / 2048).astype(int); x1, y1 = (pts.max(0) + 260 * W / 2048).astype(int)
S = 4  # work at 1/4 of the crop
gx, gy = np.meshgrid(np.arange(x0, x1, S), np.arange(y0, y1, S))
px, py = R[:, 0] * W, (1 - R[:, 1]) * H
sel = (px > x0 - 50) & (px < x1 + 50) & (py > y0 - 50) & (py < y1 + 50)
conv = griddata((px[sel], py[sel]), R[sel, 2], (gx, gy), method="linear")
depth = griddata((px[sel], py[sel]), R[sel, 3], (gx, gy), method="linear")
def norm(a):
    lo, hi = np.nanpercentile(a, 3), np.nanpercentile(a, 97); return np.clip((a - lo) / (hi - lo), 0, 1)
c = norm(np.nan_to_num(conv, nan=np.nanmedian(conv)))
d = norm(np.nan_to_num(depth, nan=np.nanmedian(depth)))
crop = cv2.resize(bc[y0:y1, x0:x1], (gx.shape[1], gx.shape[0]))
heat = cv2.applyColorMap((c * 255).astype(np.uint8), cv2.COLORMAP_INFERNO)
iso = (d * 255).astype(np.uint8)
out = cv2.addWeighted(crop, 0.45, heat, 0.55, 0)
# depth contour lines: the orbit rim shows as where the depth contours bunch up
for lev in range(10, 250, 12):
    cs, _ = cv2.findContours(((iso >= lev) * 255).astype(np.uint8), cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    cv2.drawContours(out, cs, -1, (200, 200, 200), 1)
mk = cv2.resize(mask[y0:y1, x0:x1], (gx.shape[1], gx.shape[0]))
cs, _ = cv2.findContours(((mk > 110) * 255).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
cv2.drawContours(out, cs, -1, (60, 255, 60), 2)
cv2.imwrite(sys.argv[4], cv2.resize(out, (1400, int(1400 * out.shape[0] / out.shape[1]))))

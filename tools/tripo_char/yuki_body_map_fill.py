"""Fill the painted underwear in any baked map of the MetaHuman body with what surrounds it.

    .venv_mp/Scripts/python.exe yuki_body_map_fill.py <base_body_BC.png> <map_in.png> <map_out.png> [normal]

The underwear is found as in yuki_body_skin_fill: in the ORIGINAL base colour it is the only neutral grey. The same
mask (scaled to the map) is filled from the map's own surroundings by normalised blurs of growing radius. With
"normal" the result is renormalised as a tangent-space normal map. Prints the mean of the map inside and outside the
mask before and after: if they already agree, the map does not carry the cloth."""
import sys

import cv2
import numpy as np

base = cv2.imread(sys.argv[1], cv2.IMREAD_COLOR).astype(np.float32) / 255
raw = cv2.imread(sys.argv[2], cv2.IMREAD_UNCHANGED)
work = raw.astype(np.float32) / (65535.0 if raw.dtype == np.uint16 else 255.0)
if work.ndim == 2:
    work = work[..., None]
S = work.shape[0]
if base.shape[0] != S:
    base = cv2.resize(base, (work.shape[1], S), interpolation=cv2.INTER_AREA)
b, g, r = base[..., 0], base[..., 1], base[..., 2]
grey = (np.abs(r - g) < 0.07) & (np.abs(g - b) < 0.07)
k1 = max(3, S // 200 * 2 + 1)
mask = cv2.dilate(grey.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k1, k1)))
mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((max(3, S // 100), max(3, S // 100)), np.uint8)).astype(np.float32)
# The fill is smooth by construction, so it is computed on a 1024 px copy and scaled up: the blurs with a radius of a
# sixth of an 8K map did not finish in ten minutes at full size (2026-11-14).
LO = 1024
wl = cv2.resize(work, (LO, LO), interpolation=cv2.INTER_AREA)
if wl.ndim == 2:
    wl = wl[..., None]
ml = (cv2.resize(mask, (LO, LO), interpolation=cv2.INTER_AREA) > 0.01).astype(np.float32)
src_w = 1 - ml
fl, left = np.zeros_like(wl), ml.copy()
for k in (LO / 400, LO / 200, LO / 100, LO / 50, LO / 25, LO / 12, LO / 6):
    wk = cv2.GaussianBlur(src_w, (0, 0), k)
    fk = cv2.GaussianBlur(wl * src_w[..., None], (0, 0), k)
    if fk.ndim == 2:
        fk = fk[..., None]
    fk = fk / np.maximum(wk, 1e-4)[..., None]
    take = left * np.clip(wk * 4, 0, 1)
    fl += fk * take[..., None]
    left = left - take
fl += np.median(wl[ml < 0.5], 0) * left[..., None]
fill = cv2.resize(fl, (work.shape[1], S), interpolation=cv2.INTER_CUBIC)
if fill.ndim == 2:
    fill = fill[..., None]
before = (work[mask > 0.5].mean(0).round(3).tolist(), work[mask < 0.5].mean(0).round(3).tolist())
soft = cv2.GaussianBlur(mask, (0, 0), S / 400)
out = work * (1 - soft[..., None]) + fill * soft[..., None]
if len(sys.argv) > 4 and sys.argv[4] == "normal" and out.shape[2] >= 3:
    n = out[..., :3][..., ::-1] * 2 - 1                      # BGR on disk
    n /= np.maximum(np.linalg.norm(n, axis=2, keepdims=True), 1e-6)
    out[..., :3] = (n * 0.5 + 0.5)[..., ::-1]
res = np.clip(out, 0, 1)
cv2.imwrite(sys.argv[3], (res * (65535 if raw.dtype == np.uint16 else 255) + 0.5).astype(raw.dtype) if res.shape[2] > 1 else (res[..., 0] * (65535 if raw.dtype == np.uint16 else 255) + 0.5).astype(raw.dtype))
print("MAPFILL", sys.argv[2].split("/")[-1].split("\\")[-1], "shape", raw.shape, "underwear share", round(float(mask.mean()), 3), "mean inside, outside before", before,
      "inside after", res[mask > 0.5].mean(0).round(3).tolist())

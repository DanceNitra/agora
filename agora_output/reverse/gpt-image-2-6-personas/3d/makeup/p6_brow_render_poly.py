"""The p6 brow outline, cleaned (no lashes, no hair strand), in RENDER pixels: p6 aligned to the render by the eye
corners + nose bridge (makeup/p6_to_render_M.npy). Writes makeup/p6_brow_render_poly.json with the outline and the
render landmarks used later to place it on the 3D head. Usage: p6_brow_render_poly.py [dilate_px]"""
import json, sys
import cv2, numpy as np
from scipy.ndimage import median_filter, uniform_filter1d
P6L = np.array(json.load(open('makeup/p6_landmarks.json'))); p6 = cv2.imread('beauty/depesa_p6.png'); h6, w6 = p6.shape[:2]
up, lo = [336, 296, 334, 293, 300], [285, 295, 282, 283, 276]
pts = np.vstack([P6L[up], P6L[lo]]); c = pts.mean(0)
band = np.zeros((h6, w6), np.uint8)
cv2.fillConvexPoly(band, cv2.convexHull(((pts - c) * np.array([1.25, 2.0]) + c).astype(np.int32)), 255)
lid = P6L[[386, 385, 387, 384, 388, 466, 263, 362]]; ewp = np.linalg.norm(P6L[263] - P6L[362])
for x in range(w6):
    band[int(lid[:, 1][np.argsort(np.abs(lid[:, 0] - x))[:2]].mean() - 0.06 * ewp):, x] = 0
g = cv2.cvtColor(p6, cv2.COLOR_BGR2GRAY).astype(np.float32)
skin = np.median(g[(cv2.dilate(band, np.ones((41, 41), np.uint8)) > 0) & (band == 0)])
m6 = ((g < skin * 0.6) & (band > 0)).astype(np.uint8)
m6 = cv2.morphologyEx(m6, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
m6 = cv2.morphologyEx(m6, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
n, lab, st, _ = cv2.connectedComponentsWithStats(m6)
m6 = (lab == 1 + np.argmax(st[1:, cv2.CC_STAT_AREA])).astype(np.uint8)
ys_, xs_ = np.nonzero(m6)
xa, xb = xs_.min(), min(xs_.max(), int(max(P6L[300][0], P6L[276][0]) - 0.02 * ewp))
cols = np.arange(xa, xb + 1); top = np.full(len(cols), np.nan); bot = np.full(len(cols), np.nan)
for i, x in enumerate(cols):
    yy = np.nonzero(m6[:, x])[0]
    if len(yy): top[i], bot[i] = yy.min(), yy.max()
ok = ~np.isnan(top); top = np.interp(cols, cols[ok], top[ok]); bot = np.interp(cols, cols[ok], bot[ok])
top = uniform_filter1d(median_filter(top, 25), 9); bot = uniform_filter1d(median_filter(bot, 41), 9)
bot = np.minimum(bot, top + 1.0 * median_filter(bot - top, 121))
poly6 = np.vstack([np.c_[cols, top], np.c_[cols[::-1], bot[::-1]]])
M = np.load('makeup/p6_to_render_M.npy')
polyR = np.c_[poly6, np.ones(len(poly6))] @ M.T
d = int(sys.argv[1]) if len(sys.argv) > 1 else 0
if d:
    R = cv2.imread('ue/fit/render_eyetest/0057.png'); mk = np.zeros(R.shape[:2], np.uint8)
    cv2.fillPoly(mk, [polyR.astype(np.int32)], 255); mk = cv2.dilate(mk, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * d + 1, 2 * d + 1)))
    polyR = max(cv2.findContours(mk, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[0], key=cv2.contourArea)[:, 0, :].astype(float)
RL = np.array(json.load(open('makeup/render0057_landmarks.json')))
json.dump({"poly_render_px": polyR.round(2).tolist(), "render_landmarks": {str(i): RL[i].tolist() for i in (33, 133, 362, 263, 168, 6, 159, 386)},
           "uv_landmarks_2048": {str(i): v for i, v in zip((33, 133, 362, 263, 168, 6, 159, 386), np.array(json.load(open('keenface/alb_landmarks.json')))[[33, 133, 362, 263, 168, 6, 159, 386]].tolist())}},
          open('makeup/p6_brow_render_poly.json', 'w'))
R = cv2.imread('ue/fit/render_eyetest/0057.png'); cv2.polylines(R, [polyR.astype(np.int32)], True, (60, 255, 60), 1)
cv2.imwrite('makeup/review/p6_brow_on_render.png', cv2.resize(R[440:620, 300:880], None, fx=2, fy=2))
print("poly pts", len(polyR))

"""Transfer the p6 brow itself into the face UV: segment the unoccluded p6 brow (image right) by darkness inside the
brow band, carry the mask and the brow colour into UV with a thin-plate spline fitted on MediaPipe landmarks
(p6 -> UV, eyes, brows, forehead, nose bridge), and mirror it to the other side (the UV is symmetric).
Outputs: brow mask (hairs grow here), look texture with a soft shadow, and a check image.
Usage: brow_from_p6.py <bc_without_brows.png> <out_bc.png> <out_mask.png> <check.png>"""
import json, sys
import cv2, numpy as np
from scipy.interpolate import RBFInterpolator
bc = cv2.imread(sys.argv[1]); H, W = bc.shape[:2]; s = W / 2048
UVL = np.array(json.load(open('keenface/alb_landmarks.json'))) * s
P6L = np.array(json.load(open('makeup/p6_landmarks.json')))
p6 = cv2.imread('beauty/depesa_p6.png'); h6, w6 = p6.shape[:2]
# 1) segment the image-right brow in p6
up, lo = [336, 296, 334, 293, 300], [285, 295, 282, 283, 276]
pts = np.vstack([P6L[up], P6L[lo]]); c = pts.mean(0)
band = np.zeros((h6, w6), np.uint8)
cv2.fillConvexPoly(band, cv2.convexHull(((pts - c) * np.array([1.25, 2.0]) + c).astype(np.int32)), 255)
# keep out the lashes: nothing below the upper eyelid line + margin
lid = P6L[[386, 385, 387, 384, 388, 466, 263, 362]]
for x in range(w6):
    ys_ = lid[:, 1][np.argsort(np.abs(lid[:, 0] - x))[:2]].mean()
    band[int(ys_ - 0.06 * np.linalg.norm(P6L[263] - P6L[362])):, x] = 0
g = cv2.cvtColor(p6, cv2.COLOR_BGR2GRAY).astype(np.float32)
skin = np.median(g[(cv2.dilate(band, np.ones((41, 41), np.uint8)) > 0) & (band == 0)])
m6 = ((g < skin * 0.6) & (band > 0)).astype(np.uint8)
m6 = cv2.morphologyEx(m6, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
m6 = cv2.morphologyEx(m6, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
n, lab, st, _ = cv2.connectedComponentsWithStats(m6)
m6 = (lab == 1 + np.argmax(st[1:, cv2.CC_STAT_AREA])).astype(np.uint8) * 255
# clean: per column take the brow run, median-smooth its top and bottom edges (removes lash spikes and stray hair),
# and stop where her brow ends (just past landmark 300/276)
ys_, xs_ = np.nonzero(m6)
xa, xb = xs_.min(), min(xs_.max(), int(max(P6L[300][0], P6L[276][0]) - 0.02 * np.linalg.norm(P6L[263] - P6L[362])))
cols = np.arange(xa, xb + 1); top = np.full(len(cols), np.nan); bot = np.full(len(cols), np.nan)
for i, x in enumerate(cols):
    yy = np.nonzero(m6[:, x])[0]
    if len(yy): top[i], bot[i] = yy.min(), yy.max()
ok = ~np.isnan(top)
top = np.interp(cols, cols[ok], top[ok]); bot = np.interp(cols, cols[ok], bot[ok])
from scipy.ndimage import median_filter, uniform_filter1d
top = uniform_filter1d(median_filter(top, 25), 9); bot = uniform_filter1d(median_filter(bot, 41), 9)
th = bot - top; thmed = median_filter(th, 121)
bot = np.minimum(bot, top + 1.0 * thmed)                     # cut what hangs below the brow (lashes)
# audit v22: straight top edge in TWO segments with a sharp break (no hump), body ~0.2 eye widths, tail tapering
# to a point, bottom edge kept low. Built on p6's own measured edges.
ewp = np.linalg.norm(P6L[263] - P6L[362])
hx, ex0 = cols[0], cols[-1]
ex_ = int(hx + (ex0 - hx) * 1.15)                             # tail continues toward the temple
cols = np.arange(hx, ex_ + 1)
px_ = int(hx + 0.64 * (ex_ - hx))                             # break at 64 % (measured on p6, makeup/p6_brow.json)
rise = np.tan(np.radians(8.5)); drop = np.tan(np.radians(18))   # measured on p6
t0 = np.interp(hx, np.arange(len(top)) + hx, top)             # p6 head top
top = np.where(cols <= px_, t0 - (cols - hx) * rise, t0 - (px_ - hx) * rise + (cols - px_) * drop)
thick = np.full(len(cols), 0.23 * ewp)   # p6 body 0.21-0.25 ew (measured)
tail = np.clip((cols - px_) / max(1, ex_ - px_), 0, 1)
thick = thick * (1 - 0.9 * tail ** 0.8)                       # taper to a point
head = np.clip((cols - hx) / (0.12 * (ex_ - hx)), 0, 1)
thick = thick * (0.8 + 0.2 * head)
bot = top + thick
m6 = np.zeros_like(m6)
for x, t, b in zip(cols, top, bot):
    if b > t: m6[int(t):int(b) + 1, x] = 255
# 2) placement as in p6: p6 -> render by a similarity on the eye corners + nose bridge (keeps p6's brow-to-eye
#    distance and brow spacing in eye units), then render -> UV by a thin-plate spline on the same face's
#    landmarks WITHOUT the brow landmarks (those sit on her own high arch and would pull the brow back up)
M = np.load('makeup/p6_to_render_M.npy')
RL = np.array(json.load(open('makeup/render0057_landmarks.json')))
IDX = [33, 133, 362, 263, 159, 145, 386, 374, 385, 387, 384, 388, 160, 158, 157, 161, 9, 8, 168, 6, 151, 10,
       337, 108, 299, 69, 333, 104, 297, 67, 338, 109, 383, 156, 353, 124, 446, 226, 342, 113, 265, 35]
tps = RBFInterpolator(RL[IDX], UVL[IDX], kernel='thin_plate_spline', smoothing=1.0)
cs, _ = cv2.findContours(m6, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
cont = max(cs, key=cv2.contourArea)[:, 0, :].astype(float)
dense = []
for p0, p1 in zip(cont, np.roll(cont, -1, 0)):
    for t in np.linspace(0, 1, 3, endpoint=False):
        dense.append(p0 + (p1 - p0) * t)
dense = np.array(dense)
ren = np.c_[dense, np.ones(len(dense))] @ M.T
ewr = np.linalg.norm(RL[33] - RL[133])
ren[:, 1] -= float(sys.argv[5]) * ewr if len(sys.argv) > 5 else 0.0   # lift above our longer lashes (eye widths)
uvc = tps(ren).astype(np.int32)
mask = np.zeros((H, W), np.uint8); cv2.fillPoly(mask, [uvc], 255)
mask = np.maximum(mask, mask[:, ::-1])
cv2.imwrite(sys.argv[3], mask)
sh = cv2.GaussianBlur(cv2.erode(mask, np.ones((5, 5), np.uint8)).astype(np.float32) / 255, (0, 0), 4 * s) * 0.70   # owner 11-08: holes between hairs; fill must carry the brow body
out = bc.astype(np.float32) * (1 - sh[..., None]) + np.array([28, 33, 42], np.float32) * sh[..., None]
cv2.imwrite(sys.argv[2], np.clip(out, 0, 255).astype(np.uint8))
# check: p6 crop with its traced brow | UV with the transferred brow
c6 = p6.copy(); cv2.drawContours(c6, [cont.astype(np.int32)], -1, (60, 255, 60), 2)
x0, y0 = (pts.min(0) - 120).astype(int); x1, y1 = (pts.max(0) + 160).astype(int)
a = cv2.resize(c6[max(0, y0):y1, x0:x1], (700, 380))
chk = out.astype(np.uint8).copy(); cs2, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE); cv2.drawContours(chk, cs2, -1, (60, 255, 60), 3)
bp = UVL[[300, 336, 276, 285, 263, 362]]; u0, v0 = (bp.min(0) - 200 * s).astype(int); u1, v1 = (bp.max(0) + 200 * s).astype(int)
b = cv2.resize(chk[v0:v1, u0:u1], (700, 380))
cv2.imwrite(sys.argv[4], np.hstack([a, b]))
print("p6 brow px", int((m6 > 0).sum()), "uv brow px", int((mask > 0).sum()))

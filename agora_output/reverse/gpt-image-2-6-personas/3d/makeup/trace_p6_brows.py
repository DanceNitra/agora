"""Trace the p6 brows on p6 aligned to the render (eye corners + nose bridge), then carry the traced outline to
the face UV texture with a thin-plate spline from the render's landmarks to the UV landmarks (same face, so the
warp is well conditioned). Outputs: traced overlay check and a UV brow mask."""
import json, cv2, numpy as np
from scipy.interpolate import RBFInterpolator
R = cv2.imread('ue/fit/render_eyetest/0057.png'); H, W = R.shape[:2]
P6 = cv2.imread('beauty/depesa_p6.png')
M = np.load('makeup/p6_to_render_M.npy')
p6l = np.array(json.load(open('makeup/p6_landmarks.json'))); rl = np.array(json.load(open('makeup/render0057_landmarks.json')))
warp = cv2.warpAffine(P6, M, (W, H))
p6w = (np.c_[p6l, np.ones(len(p6l))] @ M.T)
gray = cv2.cvtColor(warp, cv2.COLOR_BGR2GRAY).astype(np.float32)
masks = []
for up, lo in (([107, 66, 105, 63, 70], [55, 65, 52, 53, 46]), ([336, 296, 334, 293, 300], [285, 295, 282, 283, 276])):
    pts = np.vstack([p6w[up], p6w[lo]]); c = pts.mean(0)
    band = np.zeros((H, W), np.uint8)
    cv2.fillConvexPoly(band, cv2.convexHull(((pts - c) * np.array([1.35, 2.2]) + c).astype(np.int32)), 255)
    skin = np.median(gray[band > 0])
    m = ((gray < skin * 0.62) & (band > 0)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))   # drop thin hair strands
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    if n > 1:
        k = 1 + np.argmax(st[1:, cv2.CC_STAT_AREA]); m = (lab == k).astype(np.uint8)
    masks.append(m)
mask = np.maximum(*masks)
chk = warp.copy(); cs, _ = cv2.findContours(mask * 255, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
cv2.drawContours(chk, cs, -1, (60, 255, 60), 1)
chk2 = R.copy(); cv2.drawContours(chk2, cs, -1, (60, 255, 60), 1)
cv2.imwrite('makeup/p6_brow_trace_check.png', np.hstack([chk[300:780, 180:900], chk2[300:780, 180:900]]))
cv2.imwrite('makeup/p6_brow_trace_render.png', mask * 255)
print("traced px", int(mask.sum()), [int(x.sum()) for x in masks])

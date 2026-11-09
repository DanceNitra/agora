"""Clean brow template from the p6 measurement (makeup/p6_brow.json, unoccluded p6 brow, eye-width units u along
the eye from the inner corner, v up), carried into render pixels through p6's own eye corners and the p6->render
alignment, lifted dy px, sampled. Replaces the dark-pixel outline, which picked up lashes and hair.
Template: head at u0, straight top rising to the break at u=1.05 (p6), straight tail dropping to the tip;
thickness head 0.17 ew, break 0.22 ew, tip 0.02 ew. Usage: brow_template_samples.py <dy_px> [u0] [u_tip] [n]"""
import json, sys
import cv2, numpy as np
dy = float(sys.argv[1]); u0 = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
ut = float(sys.argv[3]) if len(sys.argv) > 3 else 1.55; n = int(sys.argv[4]) if len(sys.argv) > 4 else 7000
P6L = np.array(json.load(open('makeup/p6_landmarks.json'))); M = np.load('makeup/p6_to_render_M.npy')
sides = []
for inner, outer in ((362, 263), (133, 33)):          # owner 11-08: each brow built in the camera view on its own eye
    ei, eo = P6L[inner], P6L[outer]; ew = np.linalg.norm(eo - ei); ex = (eo - ei) / ew; ey = np.array([ex[1], -ex[0]])
    if ey[1] > 0: ey = -ey
    sides.append((ei, ew, ex, ey))
ub, vt0, vtb, vtt = 1.05, 0.33, 0.575, 0.47
top = lambda u: np.where(u <= ub, vt0 + (vtb - vt0) * (u - u0) / (ub - u0), vtb + (vtt - vtb) * (u - ub) / (ut - ub))
def th(u):
    a = 0.10 + (0.15 - 0.10) * np.clip((u - u0) / (0.20 * (ub - u0)), 0, 1)
    a = a + 0.01 * np.clip((u - (ub - 0.25)) / 0.25, 0, 1)
    return np.where(u <= ub, a, 0.16 + (0.015 - 0.16) * (u - ub) / (ut - ub))
us = np.linspace(u0, ut, 200)
poly_e = np.vstack([np.c_[us, top(us)], np.c_[us[::-1], (top(us) - th(us))[::-1]]])
mk = np.zeros((1440, 1080), np.uint8); allp = []; alls = []; polys = []
rng = np.random.default_rng(5)
DYS = [dy, dy + (float(sys.argv[5]) if len(sys.argv) > 5 else 0.0)]   # per-side lift: image-right (362/263), image-left (133/33)
for (ei, ew, ex, ey), dys in zip(sides, DYS):
    poly6 = np.array([ei + ex * u * ew + ey * v * ew for u, v in poly_e])
    polyR = np.c_[poly6, np.ones(len(poly6))] @ M.T; polyR[:, 1] -= dys; polys.append(polyR)
    m1 = np.zeros((1440, 1080), np.uint8); cv2.fillPoly(m1, [polyR.astype(np.int32)], 255); mk |= m1
    ys, xs = np.nonzero(m1); k = rng.choice(len(xs), n, replace=n > len(xs))
    pts = np.c_[xs[k] + rng.random(len(k)), ys[k] + rng.random(len(k))]
    topR = polyR[:200]; ss = (us - u0) / (ut - u0)
    o = np.argsort(topR[:, 0]); s = np.interp(pts[:, 0], topR[o, 0], ss[o])
    allp.append(pts); alls.append(s)
pts = np.vstack(allp); s = np.concatenate(alls)
cv2.imwrite('makeup/brow_template_mask.png', mk)
cv2.imwrite('makeup/brow_template_mask_outer.png', cv2.dilate(mk, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))))
polyR = np.vstack(polys)
json.dump({"pts": pts.round(2).tolist(), "s": np.round(s, 4).tolist(), "break_s": round((ub - u0) / (ut - u0), 4)}, open('makeup/brow_render_samples.json', 'w'))
R = cv2.imread('ue/fit/render_eyetest/0057.png'); [cv2.polylines(R, [p.astype(np.int32)], True, (60, 255, 60), 1) for p in polys]
cv2.imwrite('makeup/review/brow_template_on_render.png', cv2.resize(R[440:620, 300:880], None, fx=2, fy=2))
print(len(pts), "break_s", round((ub - u0) / (ut - u0), 3))

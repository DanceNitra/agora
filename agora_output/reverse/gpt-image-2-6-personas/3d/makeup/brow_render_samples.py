"""Sample points inside the p6 brow outline (render pixels), lifted by dy px, with a tail added past the outer end
(continues the top edge, drops tail_deg, tapers to a point). Writes makeup/brow_render_samples.json.
Usage: brow_render_samples.py <dy_px> [tail_frac] [tail_deg] [n]"""
import json, math, sys
import cv2, numpy as np
dy = float(sys.argv[1]); tf = float(sys.argv[2]) if len(sys.argv) > 2 else 0.28
td = float(sys.argv[3]) if len(sys.argv) > 3 else 20; n = int(sys.argv[4]) if len(sys.argv) > 4 else 16000
J = json.load(open('makeup/p6_brow_render_poly.json'))
poly = np.array(J['poly_render_px'], float); poly[:, 1] -= dy
xo, xi = poly[:, 0].max(), poly[:, 0].min(); L = xo - xi
end = poly[poly[:, 0] > xo - 0.04 * L]; ytop, ybot = end[:, 1].min(), end[:, 1].max()
tip = np.array([xo + tf * L, ytop + tf * L * math.tan(math.radians(td))])
tail = np.array([[xo - 0.02 * L, ytop], tip, [xo - 0.02 * L, ybot]])
mk = np.zeros((1440, 1080), np.uint8)
cv2.fillPoly(mk, [poly.astype(np.int32)], 255); cv2.fillPoly(mk, [tail.astype(np.int32)], 255)
ys, xs = np.nonzero(mk); rng = np.random.default_rng(5); k = rng.choice(len(xs), n, replace=n > len(xs))
pts = np.c_[xs[k] + rng.random(len(k)), ys[k] + rng.random(len(k))]
# position along the brow (0 head .. 1 tip) for hair direction
s = (pts[:, 0] - xi) / ((xo + tf * L) - xi)
json.dump({"pts": pts.round(2).tolist(), "s": s.round(4).tolist(), "break_s": round(float(L / ((xo + tf * L) - xi)), 4)}, open('makeup/brow_render_samples.json', 'w'))
R = cv2.imread('ue/fit/render_eyetest/0057.png')
for c in cv2.findContours(mk, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[0]: cv2.polylines(R, [c], True, (60, 255, 60), 1)
cv2.imwrite('makeup/review/brow_samples_on_render.png', cv2.resize(R[440:620, 300:880], None, fx=2, fy=2))
print(len(pts))

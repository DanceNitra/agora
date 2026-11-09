"""Measure the p6 brow: MediaPipe landmarks + a dark-pixel mask in the brow band, then fit the top edge as a line
(angle vs the eye-corner line), and report head, peak and tail positions in eye-width units.
Usage: p6_brow_measure.py <p6.png> <out_prefix>"""
import sys, json
import cv2, numpy as np
sys.path.insert(0, r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit")
import mp_lm
img = cv2.imread(sys.argv[1]); H, W = img.shape[:2]
P = mp_lm.detect(sys.argv[1])
out = {}
for side, (inner, outer, up, lo) in {
        "img_right": (362, 263, [336, 296, 334, 293, 300], [285, 295, 282, 283, 276]),
        "img_left": (133, 33, [107, 66, 105, 63, 70], [55, 65, 52, 53, 46])}.items():
    ei, eo = P[inner], P[outer]
    ew = np.linalg.norm(eo - ei)
    ex = (eo - ei) / ew; ey = np.array([ex[1], -ex[0]])          # ey points up (image y grows down)
    if ey[1] > 0: ey = -ey
    pts = np.vstack([P[up], P[lo]])
    # band polygon: brow landmarks grown by 0.25 eye widths
    c = pts.mean(0)
    poly = (c + (pts - c) * 1.6).astype(np.int32)
    hull = cv2.convexHull(poly)
    band = np.zeros((H, W), np.uint8); cv2.fillConvexPoly(band, hull, 255)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    skin = np.median(gray[band > 0])
    mask = ((gray < skin * 0.55) & (band > 0)).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(mask)
    k = 1 + np.argmax(st[1:, cv2.CC_STAT_AREA]) if n > 1 else 0
    mask = (lab == k).astype(np.uint8) * 255
    ys, xs = np.nonzero(mask)
    # eye frame coordinates: u along the eye (0 inner corner, 1 outer corner), v up, in eye widths
    rel = np.stack([xs, ys], 1) - ei
    u = rel @ ex / ew; v = rel @ ey / ew
    bins = np.linspace(u.min(), u.max(), 25)
    top, bot = [], []
    for a, b in zip(bins[:-1], bins[1:]):
        s = (u >= a) & (u < b)
        if s.sum() > 3:
            top.append(((a + b) / 2, np.percentile(v[s], 95))); bot.append(((a + b) / 2, np.percentile(v[s], 5)))
    top, bot = np.array(top), np.array(bot)
    pk = top[np.argmax(top[:, 1])]
    rising = top[top[:, 0] <= pk[0]]
    slope = np.polyfit(rising[:, 0], rising[:, 1], 1)[0] if len(rising) > 2 else float("nan")
    resid = np.abs(np.polyval(np.polyfit(rising[:, 0], rising[:, 1], 1), rising[:, 0]) - rising[:, 1]).max() if len(rising) > 2 else float("nan")
    out[side] = {"eye_width_px": round(float(ew), 1), "u_range": [round(float(u.min()), 3), round(float(u.max()), 3)],
                 "peak_u_v": [round(float(pk[0]), 3), round(float(pk[1]), 3)],
                 "top_edge_angle_deg": round(float(np.degrees(np.arctan(slope))), 1),
                 "top_edge_max_line_dev_ew": round(float(resid), 3),
                 "thickness_ew": [round(float(t - b), 3) for (_, t), (_, b) in zip(top[::4], bot[::4])],
                 "top": top.round(3).tolist(), "bottom": bot.round(3).tolist(), "pixels": int(len(xs))}
    vis = img.copy(); vis[mask > 0] = (0, 0, 255)
    cv2.imwrite(sys.argv[2] + "_" + side + ".png", vis[max(0, int(c[1] - 2 * ew)):int(c[1] + 1.5 * ew), max(0, int(c[0] - 2 * ew)):int(c[0] + 2 * ew)])
json.dump(out, open(sys.argv[2] + ".json", "w"), indent=1)
for s, d in out.items():
    print(s, {k: d[k] for k in ("eye_width_px", "u_range", "peak_u_v", "top_edge_angle_deg", "top_edge_max_line_dev_ew", "thickness_ew", "pixels")})

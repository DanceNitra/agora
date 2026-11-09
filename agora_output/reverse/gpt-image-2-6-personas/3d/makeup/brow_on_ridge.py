"""Place the p6 brow on Depesa's own brow bone, in UV. The supraorbital ridge crest comes from the mesh convexity
(head_relief_uv.json); the shape rules come from p6 measured in eye-width units and from brow mapping:
head over the inner eye corner, BREAK above the outer edge of the iris (nose wing -> outer iris line), tail ends
past the outer corner. Straight top edge from head to break, then a short straight drop. The bottom edge follows the
ridge crest. Writes the brow mask (where hairs grow) and the look texture with only a soft fading shadow.
Usage: brow_on_ridge.py <bc_without_brows.png> <out_bc.png> <out_mask.png> <check.png>"""
import json, sys
import cv2, numpy as np
from scipy.interpolate import griddata
bc = cv2.imread(sys.argv[1]); H, W = bc.shape[:2]; s = W / 2048
L = np.array(json.load(open('keenface/alb_landmarks.json'))) * s
R = np.array(json.load(open('makeup/head_relief_uv.json')))
px, py = R[:, 0] * W, (1 - R[:, 1]) * H
side = {"img_left": dict(inner=133, outer=33, iris=[469, 470, 471, 472], wing=129, brow=[70, 63, 105, 66, 107, 46, 53, 52, 65, 55]),
        "img_right": dict(inner=362, outer=263, iris=[474, 475, 476, 477], wing=358, brow=[300, 293, 334, 296, 336, 276, 283, 282, 295, 285])}
mask = np.zeros((H, W), np.uint8); chk = bc.copy()
info = {}
for nm, d in side.items():
    ei, eo = L[d["inner"]], L[d["outer"]]; ew = np.linalg.norm(eo - ei); sgn = np.sign(eo[0] - ei[0])
    iris_out = L[d["iris"]][np.argmax(L[d["iris"]][:, 0] * sgn)]
    # break x: where the line nose-wing -> outer iris edge crosses the brow height
    wing = L[d["wing"]]
    bp = L[d["brow"]]; ytop = bp[:, 1].min()
    t = (ytop - wing[1]) / (iris_out[1] - wing[1]); bx = wing[0] + (iris_out[0] - wing[0]) * t
    hx = ei[0] - sgn * 0.04 * ew; tx = eo[0] + sgn * 0.30 * ew
    xs = np.linspace(min(hx, tx), max(hx, tx), 60)
    # ridge crest per column: max convexity between the eye and 0.9 ew above it
    crest = []
    for x in xs:
        ysamp = np.linspace(ei[1] - 0.95 * ew, ei[1] - 0.15 * ew, 80)
        cv = griddata((px, py), R[:, 2], (np.full_like(ysamp, x), ysamp), method='linear')
        cv = np.convolve(np.nan_to_num(cv, nan=-1e9), np.ones(7) / 7, 'same')
        crest.append(ysamp[int(np.argmax(cv))])
    crest = np.convolve(np.array(crest), np.ones(9) / 9, 'same'); crest[:4] = crest[4]; crest[-4:] = crest[-5]
    cy = lambda x: np.interp(x, xs, crest)
    U = L[d["brow"][:5]]; B = L[d["brow"][5:]]            # her own brow line: upper 70..107, lower 46..55
    if np.sign(U[0][0] - U[-1][0]) != np.sign(ei[0] - eo[0]): U, B = U[::-1], B[::-1]   # index 0 = head (nose side)
    from scipy.interpolate import CubicSpline
    o = np.argsort(U[:, 0]); csu = CubicSpline(U[o, 0], U[o, 1])
    xx = np.linspace(U[:, 0].min(), U[:, 0].max(), 400)
    bx = xx[np.argmin(csu(xx))]                              # BREAK where her natural arch peaks
    th_head, th_break = 0.066 * ew, 0.12 * ew   # owner: head 2 mm narrower (eye width ~29 mm)              # p6: thinner, even brow
    DROP = 0.13 * ew                                         # p6: brow sits lower, close to the eye
    HB = B[0] + [0, DROP]; HT = HB - [0, th_head]
    BT = np.array([bx, csu(bx) - 0.01 * ew + DROP]); BB = BT + [0, th_break]
    TE = np.array([B[-1][0] + sgn * 0.22 * ew, B[-1][1] + 0.2 * DROP - 0.07 * ew])   # tail tapers toward the temple, stays off the lashes   # long thin tail toward the temple
    HM = HB + (HT - HB) * 0.5
    poly = np.array([HT + [sgn * 0.06 * ew, 0], BT, TE, BB, HB + [sgn * 0.04 * ew, 0], HM - [sgn * 0.02 * ew, 0]], np.int32)   # thin, soft head
    cv2.fillPoly(mask, [poly], 255)
    cv2.polylines(chk, [np.c_[xs, crest].astype(np.int32)], False, (255, 200, 0), 2)
    cv2.circle(chk, tuple(iris_out.astype(int)), 6, (0, 255, 255), -1)
    info[nm] = {"eye_width": round(float(ew), 1), "break_from_inner_corner_ew": round(float((bx - ei[0]) * sgn / ew), 2),
                "top_angle_deg": round(float(np.degrees(np.arctan2(HT[1] - BT[1], abs(BT[0] - HT[0])))), 1),
                "break_above_eye_ew": round(float((ei[1] - BT[1]) / ew), 2)}
cv2.imwrite(sys.argv[3], mask)
sh = cv2.GaussianBlur(cv2.erode(mask, np.ones((13, 13), np.uint8)).astype(np.float32) / 255, (0, 0), 9 * s) * 0.35
out = bc.astype(np.float32) * (1 - sh[..., None]) + np.array([30, 34, 42], np.float32) * sh[..., None]
cv2.imwrite(sys.argv[2], np.clip(out, 0, 255).astype(np.uint8))
cs, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE); cv2.drawContours(chk, cs, -1, (60, 255, 60), 3)
bp = L[[70, 300, 107, 336, 46, 276, 33, 263]]; x0, y0 = (bp.min(0) - 160 * s).astype(int); x1, y1 = (bp.max(0) + 160 * s).astype(int)
cv2.imwrite(sys.argv[4], cv2.resize(chk[y0:y1, x0:x1], (1400, int(1400 * (y1 - y0) / (x1 - x0)))))
print(info)

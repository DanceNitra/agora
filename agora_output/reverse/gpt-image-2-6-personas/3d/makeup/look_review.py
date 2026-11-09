"""Look review for Depesa (owner rule 2026-11-08: no self-grading, no trial and error without measurement).

Builds the review packet for one render frame:
  1. a p6 comparison sheet: p6 aligned to the render (eye corners + nose bridge) over the render, close-up and
     full face, written to makeup/review/<tag>_sheet.png;
  2. measurements written to makeup/review/<tag>.json:
     - brow_holes: share of skin-coloured pixels inside each rendered brow body (holes, unfilled patches);
     - brow_to_ridge: in UV, the brow mask's top edge and bottom edge against the supraorbital ridge crest
       of the mesh (head_relief_uv.json), in eye widths, per brow; negative = above the crest;
     - brow_mask_symmetry: mirrored IoU of the brow mask.
The audit itself is done by an independent subagent that sees only the sheet and p6, never my conclusion; it
writes makeup/review/<tag>_audit.md. The SendUserFile hook refuses to send a makeup image without both files.
Usage: look_review.py <render.png> <tag>"""
import json, os, sys
import cv2, numpy as np
from scipy.interpolate import griddata

D = os.path.dirname(os.path.abspath(__file__)); B = os.path.dirname(D)
os.makedirs(os.path.join(D, "review"), exist_ok=True)
render, tag = sys.argv[1], sys.argv[2]
R = cv2.imread(render); H, W = R.shape[:2]
M = np.load(os.path.join(D, "p6_to_render_M.npy"))
P6 = cv2.warpAffine(cv2.imread(os.path.join(B, "beauty", "depesa_p6.png")), M, (W, H))
z = lambda im, x0, y0, x1, y1: cv2.resize(im[y0:y1, x0:x1], None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
close = np.vstack([z(P6, 300, 440, 880, 620), z(R, 300, 440, 880, 620)])
wideR = cv2.resize(R[150:1100, 120:960], (int(840 * 600 / 950), 600)); wideP = cv2.resize(P6[150:1100, 120:960], wideR.shape[1::-1])
wide = np.hstack([wideP, wideR]); wide = cv2.resize(wide, (close.shape[1], int(wide.shape[0] * close.shape[1] / wide.shape[1])))
cv2.putText(close, "TOP: p6 (reference)   BOTTOM: Depesa " + tag, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
cv2.imwrite(os.path.join(D, "review", tag + "_sheet.png"), np.vstack([close, wide]))
out = {"tag": tag, "render": render}

# 1) holes: the brow region is OUR brow mask (UV) carried into the render with a thin-plate spline on the face
#    landmarks; a hole is a pixel inside it brighter than 0.6 x the skin just above the brow (skin shows through).
#    Control: the same rule on p6's own traced brow must come out low.
from scipy.interpolate import RBFInterpolator
mask = cv2.imread(os.path.join(D, "brow_fill_mask.png"), 0); s_ = mask.shape[1] / 2048
UVL = np.array(json.load(open(os.path.join(B, "keenface", "alb_landmarks.json")))) * s_
RL = np.array(json.load(open(os.path.join(D, "render0057_landmarks.json"))))
IDX = [33, 133, 362, 263, 159, 145, 386, 374, 9, 8, 168, 6, 151, 10, 337, 108, 299, 69, 333, 104, 297, 67,
       383, 156, 353, 124, 226, 446, 113, 342, 35, 265, 160, 158, 385, 387]   # no brow landmarks: on the render they track OUR brows
tps = RBFInterpolator(UVL[IDX], RL[IDX], kernel="thin_plate_spline", smoothing=1.0)
reg = np.zeros((H, W), np.uint8)
for c in cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[0]:
    cv2.fillPoly(reg, [tps(c[:, 0, :].astype(float)).astype(np.int32)], 255)
reg = cv2.erode(reg, np.ones((3, 3), np.uint8))
def hole_share(img, region):
    gg = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    above = cv2.dilate(region, np.ones((1, 1), np.uint8)); ring = np.zeros_like(region)
    ring[:-14] = region[14:]; ring = (ring > 0) & (region == 0)            # band just above the brow
    skin = np.median(gg[ring]) if ring.sum() else 180
    r = region > 0
    return round(float((gg[r] > 0.6 * skin).sum() / max(1, r.sum())), 3), (gg > 0.6 * skin) & r
out["brow_holes"], hm = hole_share(R, reg)
p6l = np.c_[np.array(json.load(open(os.path.join(D, "p6_landmarks.json")))), np.ones(478)] @ M.T
reg6 = np.zeros((H, W), np.uint8)
for grp in ([336, 296, 334, 293, 300, 276, 283, 282, 295, 285],):
    cv2.fillConvexPoly(reg6, cv2.convexHull(p6l[grp].astype(np.int32)), 255)
out["control_p6_brow_holes"], _ = hole_share(P6, reg6)
vis = R.copy(); vis[hm] = (0, 0, 255)
cs, _ = cv2.findContours(reg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE); cv2.drawContours(vis, cs, -1, (0, 255, 0), 1)
cv2.imwrite(os.path.join(D, "review", tag + "_holes.png"), z(vis, 300, 440, 880, 620))
# 2) brow mask vs the supraorbital ridge crest, in UV
L = np.array(json.load(open(os.path.join(B, "keenface", "alb_landmarks.json")))) * (mask.shape[1] / 2048)
Rl = np.array(json.load(open(os.path.join(D, "head_relief_uv.json"))))
px, py = Rl[:, 0] * mask.shape[1], (1 - Rl[:, 1]) * mask.shape[0]
ridge = {}
for nm, (inner, outer) in {"img_left": (133, 33), "img_right": (362, 263)}.items():
    ei, eo = L[inner], L[outer]; ew = np.linalg.norm(eo - ei)
    xs = np.linspace(min(ei[0], eo[0]), max(ei[0], eo[0]), 15)
    tops, bots = [], []
    for x in xs:
        col = np.nonzero(mask[:, int(x)] > 127)[0]
        ys = np.linspace(ei[1] - 0.95 * ew, ei[1] - 0.1 * ew, 80)
        cv = griddata((px, py), Rl[:, 2], (np.full_like(ys, x), ys), method="linear")
        crest = ys[int(np.nanargmax(np.convolve(np.nan_to_num(cv, nan=-1e9), np.ones(7) / 7, "same")))]
        if len(col):
            tops.append((col.min() - crest) / ew); bots.append((col.max() - crest) / ew)
    ridge[nm] = {"top_minus_crest_ew_median": round(float(np.median(tops)), 3) if tops else None,
                 "bottom_minus_crest_ew_median": round(float(np.median(bots)), 3) if bots else None}
out["brow_to_ridge"] = ridge
mb = mask > 127
out["brow_mask_symmetry_iou"] = round(float((mb & mb[:, ::-1]).sum() / max(1, (mb | mb[:, ::-1]).sum())), 3)
json.dump(out, open(os.path.join(D, "review", tag + ".json"), "w"), indent=1)
print(json.dumps(out, indent=1))

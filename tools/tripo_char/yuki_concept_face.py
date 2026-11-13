"""Carry the make-up of Yuki's concept picture onto the MetaHuman face texture, landmark for landmark.

    .venv_mp/Scripts/python.exe yuki_concept_face.py <maps_dir> <concept.png> <base_tex_dir> <out_dir>

<maps_dir> comes from yuki_concept_maps.py (front.png, pos.npy, nrm.npy, maps.json). <base_tex_dir> holds the
MetaHuman's own baked base colour (base_face_BC.png, base_body_BC.png, originals.json from ue_yuki_facetex.py export).

Method. MediaPipe finds 468 landmarks in the concept and in the front render of the MetaHuman head. A thin-plate
spline maps render pixels to concept pixels through those pairs, so each feature of the concept lands on the same
feature of this head (eye corners on eye corners, lip line on lip line), whatever the small shape or expression
difference. Each skin texel knows its 3D position, hence its render pixel, hence its concept pixel.
A texel takes the concept colour where the surface faces the camera, lies inside the face outline, and the concept
shows skin there and not hair (colour test in Lab) or the inside of an eye. Where hair covers the concept, the texel
takes the mirrored side if that side is clean (the MetaHuman UV layout is mirror symmetric; measured below), otherwise
a smooth skin tone spread from the clean texels. Outside the face the MetaHuman base colour stays, multiplied by the
gain that matches it to the concept skin along the border. The body gets the same gain.
Writes yuki_face_BC.png, yuki_body_BC.png, originals.json (copied), concept_face.json and check images.
"""
import json
import os
import shutil
import sys
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions, vision

MODEL = r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit\models\face_landmarker.task"
maps, concept_p, based, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4])
out.mkdir(parents=True, exist_ok=True)
cfg = json.loads((maps / "maps.json").read_text())
det = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(base_options=BaseOptions(model_asset_path=MODEL), num_faces=1))


def marks(path):
    im = mp.Image.create_from_file(str(path))
    r = det.detect(im)
    if not r.face_landmarks:
        raise SystemExit(f"no face found in {path}")
    return np.array([[l.x * im.width, l.y * im.height] for l in r.face_landmarks[0]])[:468]


C, R = marks(concept_p), marks(maps / "front.png")
concept = cv2.imread(concept_p, cv2.IMREAD_COLOR)
ch, cw = concept.shape[:2]
RES = cfg["res"]

# thin-plate spline render px -> concept px, lightly smoothed so landmark jitter does not ripple the make-up
s = np.linalg.norm(R[33] - R[263])
# The brows are paint, not shape: the render's brow landmarks sit wherever the texture it wears has brows, so they are
# no anchor. Without them the spline is led by the eyes, the nose and the outline, and the concept's brows land at the
# concept's own height above the eyes (2026-11-13: with them the brows came out 19 % too high).
BROWS_ALL = [70, 63, 105, 66, 107, 55, 65, 52, 53, 46, 336, 296, 334, 293, 300, 276, 283, 282, 295, 285]
# BROW_DROP_IOD (environment, in interocular distances) puts the brows back as anchors, that much lower than the render
# shows them: the correction measured on the finished head in Unreal (v7: brows 0.039 IOD too high above the eyes).
DROP = float(os.environ.get("BROW_DROP_IOD", 0))
Call = C
if DROP:
    R = R.copy()
    R[BROWS_ALL, 1] += DROP * s
else:
    ctl = np.array([i for i in range(len(R)) if i not in BROWS_ALL])
    R, C = R[ctl], C[ctl]
Rn = R / s


def U(d):
    return np.where(d > 0, d * d * np.log(np.maximum(d, 1e-12)), 0.0)


n = len(Rn)
K = U(np.linalg.norm(Rn[:, None] - Rn[None], axis=2)) + 1e-3 * np.eye(n)
Pm = np.hstack([np.ones((n, 1)), Rn])
A = np.zeros((n + 3, n + 3))
A[:n, :n], A[:n, n:], A[n:, :n] = K, Pm, Pm.T
coef = np.linalg.solve(A, np.vstack([C, np.zeros((3, 2))]))
fit = K @ coef[:n] + Pm @ coef[n:] - 1e-3 * coef[:n]
print("TPS residual px mean", round(float(np.linalg.norm(fit - C, axis=1).mean()), 2), flush=True)
C = Call
G = 200
gx, gy = np.meshgrid(np.linspace(0, RES - 1, G), np.linspace(0, RES - 1, G))
Q = np.stack([gx.ravel(), gy.ravel()], 1) / s
grid = (U(np.linalg.norm(Q[:, None] - Rn[None], axis=2)) @ coef[:n] + np.hstack([np.ones((len(Q), 1)), Q]) @ coef[n:]).reshape(G, G, 2).astype(np.float32)

pos, nrm = np.load(maps / "pos.npy"), np.load(maps / "nrm.npy")
S = pos.shape[0]
cov = np.abs(np.linalg.norm(nrm, axis=2) - 1) < 0.2
rx = ((pos[..., 0] - cfg["cx"]) / cfg["ortho"] * RES + RES / 2).astype(np.float32)
ry = (RES / 2 - (pos[..., 2] - cfg["cz"]) / cfg["ortho"] * RES).astype(np.float32)
gsx, gsy = rx / (RES - 1) * (G - 1), ry / (RES - 1) * (G - 1)
cxy = cv2.remap(grid, gsx, gsy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
mx, my = np.ascontiguousarray(cxy[..., 0]), np.ascontiguousarray(cxy[..., 1])

# what the concept shows at each pixel: hair (pink, cool) or not; and the inside of the eyes
lab = cv2.cvtColor(concept, cv2.COLOR_BGR2LAB).astype(np.float32)
L, a, b = lab[..., 0] * 100 / 255, lab[..., 1] - 128, lab[..., 2] - 128
# Hair in the concept: pink and cool (a high, b low), or a dark red-brown strand. Skin highlights have a low a, blush
# has a high b (measured on the picture: fringe a 17 b -2, temple a 19 b 4; cheek highlight a 9 b 6, blush a 20 b 10).
hair = (((a > 12.5) & (b < 6.5)) | ((L < 40) & (a > 14))).astype(np.uint8)
EYE_L = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
EYE_R = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
LIPS = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409, 270, 269, 267, 0, 37, 39, 40, 185]
OVAL = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136,
        172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]
# The concept's fringe crosses one eye and one brow. CLEAN_SIDE names the side of the PICTURE whose eye and brow are
# free of hair ("right" for a_flare_clean.png); that eye, that brow and the lips are never treated as hair, and the
# other eye and brow are taken from the clean side through the mirror, so the make-up is the same on both sides.
import os
CLEAN = os.environ.get("CLEAN_SIDE", "right")
BROW_L = [70, 63, 105, 66, 107, 55, 65, 52, 53, 46]
BROW_R = [336, 296, 334, 293, 300, 276, 283, 282, 295, 285]
eye_c, eye_o, brow_c, brow_o = (EYE_R, EYE_L, BROW_R, BROW_L) if CLEAN == "right" else (EYE_L, EYE_R, BROW_L, BROW_R)


def zone(idx, grow, hull=False):
    m = np.zeros((ch, cw), np.uint8)
    pts = np.round(C[idx]).astype(np.int32)
    cv2.fillPoly(m, [cv2.convexHull(pts) if hull else pts], 1)
    return cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (grow, grow)))


keep = np.maximum.reduce([zone(LIPS, 9), zone(eye_c, 61), zone(brow_c, 13, True)])
keep[(a > 12.5) & (b < 4.5) & (L > 58)] = 0      # light cool pink is hair even beside the eye (the temple lock)
other = np.maximum(zone(eye_o, 91), zone(brow_o, 41, True))
other[keep > 0] = 0
hair[keep > 0] = 0
# shadowed hair between the strands is warm like skin: close the gaps, then keep only what hangs together with the
# hair outside the face outline; an island of cool skin inside the face is not hair
hair = cv2.morphologyEx(hair, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21)))
hair[keep > 0] = 0
face_poly = np.zeros((ch, cw), np.uint8)
cv2.fillPoly(face_poly, [np.round(C[OVAL]).astype(np.int32)], 1)
ncc, cc = cv2.connectedComponents(hair, connectivity=8)
outside = np.unique(cc[(face_poly == 0) & (hair > 0)])
hair = np.isin(cc, outside[outside > 0]).astype(np.uint8)
hair = cv2.dilate(hair, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (19, 19)))
hair[cv2.erode(keep, np.ones((5, 5), np.uint8)) > 0] = 0
# The inside of the eyes is not skin. The mask starts a few pixels under the upper lid line, so the lash line and the
# liner stay, and it reaches a strip below the lower lid line: the concept's bright sclera and its highlight otherwise
# land on the lower lid as a white, crumbly rim (seen in Unreal, reports/yuki_ue_v8).
eye_poly = np.zeros((ch, cw), np.uint8)
for idx in (EYE_L, EYE_R):
    cv2.fillPoly(eye_poly, [np.round(C[idx]).astype(np.int32)], 1)
UP, DOWN = int(os.environ.get("EYE_TOP_PX", 4)), int(os.environ.get("EYE_BELOW_PX", 9))
eyes_in = np.zeros_like(eye_poly)
for dy in range(UP, DOWN + 1):
    eyes_in[dy:] |= eye_poly[:ch - dy]
# the drawn liner: dark pixels in the top band of the eye outline stay, however far they reach into it
band = eye_poly.copy()
band[16:] &= ~eye_poly[:ch - 16]
eyes_in[(band > 0) & (L < 40)] = 0
eye_zone = np.maximum(zone(EYE_L, 61), zone(EYE_R, 61)).astype(np.float32)
lip_zone = zone(LIPS, 15).astype(np.float32)
oval = np.zeros((ch, cw), np.uint8)
cv2.fillPoly(oval, [np.round(C[OVAL]).astype(np.int32)], 1)
oval = cv2.erode(oval, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (41, 41)))
# The forehead between the fringe locks is in hair shadow in the picture and lies under Yuki's own fringe on the model:
# it is filled smoothly from the skin beside it, not projected.
brow_top = int(min(C[BROW_L][:, 1].min(), C[BROW_R][:, 1].min())) - 6
forehead = face_poly.copy()
forehead[brow_top:] = 0
forehead = cv2.dilate(forehead, np.ones((25, 25), np.uint8))
forehead[brow_top:] = 0
# a dark strand or hair shadow inside the face that the colour test missed, and the painted highlight on the nose tip
nose_zone = zone([1, 2, 98, 327, 4], 61, True)
dark = ((L < 30) & (keep == 0) & (nose_zone == 0)).astype(np.uint8)
shine = ((L > 91) & (nose_zone > 0)).astype(np.uint8)
extra = cv2.dilate(np.maximum(dark, shine), np.ones((15, 15), np.uint8))
bad = np.maximum(cv2.GaussianBlur(((hair > 0) | (eyes_in > 0) | (extra > 0) | (forehead > 0)).astype(np.float32), (0, 0), 4),
                 cv2.GaussianBlur(other.astype(np.float32), (0, 0), 16))   # wide, soft edge where the mirrored side takes over
dbg = concept.copy()
dbg[hair > 0] = (0.5 * dbg[hair > 0] + (255 * 0.5, 0, 0)).astype(np.uint8)
dbg[eyes_in > 0] = (0, 255, 255)
dbg[other > 0] = (0.6 * dbg[other > 0] + (0, 0, 255 * 0.4)).astype(np.uint8)
dbg[extra > 0] = (0, 255, 0)
cv2.polylines(dbg, [np.round(C[OVAL]).astype(np.int32)], True, (0, 255, 0), 2)
cv2.imwrite(str(out / "check_concept_mask.jpg"), cv2.resize(dbg, (cw // 2, ch // 2)))

proj = cv2.remap(concept, mx, my, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE).astype(np.float32) / 255
w_bad = cv2.remap(bad, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=1)
w_eye = cv2.remap(eye_zone, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0) > 0.5
w_lip = cv2.remap(lip_zone, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0) > 0.5
w_oval = cv2.remap(oval.astype(np.float32), mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
facing = np.clip((-nrm[..., 1] - 0.30) / 0.30, 0, 1)
facing = facing * facing * (3 - 2 * facing)
region = w_oval * facing * cov                           # where the concept may paint at all
region = np.minimum(region, cv2.GaussianBlur(region, (0, 0), S / 150))
valid = region * (1 - np.clip(w_bad * 2.0, 0, 1))        # ... and shows clean skin or make-up

# mirror symmetry of the UV layout: texel (u, v) and (1-u, v) must be the same point mirrored in X
pm = pos[:, ::-1]
both = cov & cov[:, ::-1]
sym = np.linalg.norm(np.stack([pos[..., 0] + pm[..., 0], pos[..., 1] - pm[..., 1], pos[..., 2] - pm[..., 2]], -1), axis=2)[both]
sym_mm = float(np.median(sym) * 1000)
print("UV mirror symmetry: median error mm", round(sym_mm, 2), "p90", round(float(np.percentile(sym, 90) * 1000), 2), flush=True)


def lin(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055)


P = lin(proj[..., ::-1])                                   # RGB linear
# De-light: the picture is lit (bright nose and cheeks, shaded jaw) and Unreal lights the head again. The broad
# brightness of the skin is divided out and replaced by one level; make-up, blush colour and fine shading stay.
lum0 = P @ np.array([0.2126, 0.7152, 0.0722], np.float32)
sat0 = P.max(2) - P.min(2)
v0 = region * (1 - np.clip(w_bad * 2.0, 0, 1)) > 0.9
sk0 = (v0 & (lum0 > np.percentile(lum0[v0], 30)) & (sat0 < np.percentile(sat0[v0], 70))).astype(np.float32)
kd = S / 18
low = cv2.GaussianBlur(lum0 * sk0, (0, 0), kd) / np.maximum(cv2.GaussianBlur(sk0, (0, 0), kd), 1e-4)
flat = float(np.percentile(lum0[sk0 > 0], 60))
P = P * np.clip(flat / np.maximum(low, 1e-4), 0.7, 1.6)[..., None]
# SKIN_SAT (environment): chroma gain around each texel's own luminance. Unreal's skin shading and a neutral light wash
# the concept's pink out (render cheek 224,202,190 against the concept's 230,178,171 at SKIN_SAT 1).
SAT = float(os.environ.get("SKIN_SAT", 1.0))
if SAT != 1.0:
    lumP = (P @ np.array([0.2126, 0.7152, 0.0722], np.float32))[..., None]
    P = np.clip(lumP + SAT * (P - lumP), 0, 1)
acc, wsum = P * valid[..., None], valid.copy()
if sym_mm < 8.0:    # the layout is symmetric; the conformed head itself is a few millimetres asymmetric
    vm = valid[:, ::-1] * (1 - valid)                      # take the other side only where this side is not clean
    acc += P[:, ::-1] * vm[..., None]
    wsum += vm
# smooth skin for what is still empty: normalised blur of the clean, non make-up texels
lum = P.mean(2)
sat = P.max(2) - P.min(2)
skinlike = (valid > 0.9) & (lum > np.percentile(lum[valid > 0.9], 35)) & (sat < np.percentile(sat[valid > 0.9], 70))
have = np.clip(wsum, 0, 1)
face = acc / np.maximum(wsum, 1e-4)[..., None] * have[..., None]
# TEX_PATCHES (environment, "x,y,r;x,y,r" in texture pixels): spots the masks missed (a strand tip on a cheek, what is
# left of the nose highlight). They are emptied here and filled from the skin around them like any other gap.
if os.environ.get("TEX_PATCHES"):
    pm = np.zeros((S, S), np.uint8)
    for spec in os.environ["TEX_PATCHES"].split(";"):
        px, py, pr = (int(v) for v in spec.split(","))
        cv2.circle(pm, (px, py), pr, 1, -1)
    pm = cv2.GaussianBlur(pm.astype(np.float32), (0, 0), 5)
    have = have * (1 - pm)
    face = face * (1 - pm)[..., None]
# Everything else, inside the face and outside it, is filled from its surroundings, nearest first: normalised blurs of
# growing radius over the clean, non make-up texels. Near the face the fill continues the concept's skin; far away
# (scalp, neck) it settles on the median skin colour.
# Fill sources. Beside the eyes: no liner and no eye shadow, so the gaps there take lid skin. On the lips: nothing.
# Elsewhere everything but the most saturated texels, so blush continues into a gap instead of ending at its edge.
lum_now = face @ np.array([0.2126, 0.7152, 0.0722], np.float32)
sv = sat[valid > 0.9]
ok = np.where(w_eye | w_eye[:, ::-1], (sat < np.percentile(sv, 80)) & (lum_now > 0.55 * flat), sat < np.percentile(sv, 97))
src_w = (have * ok * ~(w_lip | w_lip[:, ::-1]) * cov).astype(np.float32)
src = face * src_w[..., None] / np.maximum(have, 1e-4)[..., None]
glob = np.median(P[skinlike], 0)
fill = np.zeros_like(face)
left = np.ones_like(have)
for k in (S / 300, S / 150, S / 75, S / 35, S / 15, S / 7):
    wk = cv2.GaussianBlur(src_w, (0, 0), k)
    fk = cv2.GaussianBlur(src, (0, 0), k) / np.maximum(wk, 1e-4)[..., None]
    take = left * np.clip(wk * 4, 0, 1)
    fill += fk * take[..., None]
    left = left - take
fill += glob * left[..., None]
face = face + fill * (1 - have[..., None])

base = cv2.imread(str(based / "base_face_BC.png"), cv2.IMREAD_COLOR)
base = cv2.resize(base, (S, S), interpolation=cv2.INTER_AREA)[..., ::-1].astype(np.float32) / 255
Bl = lin(base)
# Outside the face the base keeps only its fine detail (pores, ear folds). Its broad colour, which carries the
# MetaHuman's own blush, liner and scalp shading, is replaced by the fill.
detail = np.clip(Bl / np.maximum(cv2.GaussianBlur(Bl, (0, 0), S / 50), 1e-4), 0.6, 1.35)
outl = region[..., None] * face + (1 - region[..., None]) * np.clip(cv2.GaussianBlur(fill, (0, 0), S / 100) * detail, 0, 1)
# The liner. The concept's black lash line falls on the lid margin, which the open eye hides, so it does not show on the
# model. The MetaHuman's own baked texture carries a cat-eye liner drawn for exactly this UV layout (make-up set in
# ue_yuki_look.py): its darkest texels beside the eyes are taken as a mask and painted over the result.
LINER = float(os.environ.get("LINER", 1.0))
if LINER > 0:
    bl_lum = base @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    la = np.clip((0.30 - bl_lum) / 0.16, 0, 1) * cv2.dilate((w_eye | w_eye[:, ::-1]).astype(np.uint8), np.ones((41, 41), np.uint8))
    la = cv2.GaussianBlur(la.astype(np.float32), (0, 0), 1.2) * LINER
    outl = outl * (1 - la[..., None]) + np.array([0.012, 0.006, 0.007], np.float32) * la[..., None]
    print("LINER texels", int((la > 0.5).sum()), flush=True)
tex = (srgb(outl) * 255 + 0.5).astype(np.uint8)
cv2.imwrite(str(out / "yuki_face_BC.png"), tex[..., ::-1])
body = cv2.imread(str(based / "base_body_BC.png"), cv2.IMREAD_COLOR)[..., ::-1].astype(np.float32) / 255
bl = lin(body)
gain = glob / np.median(bl.reshape(-1, 3), 0)
cv2.imwrite(str(out / "yuki_body_BC.png"), ((srgb(np.clip(bl * gain, 0, 1)) * 255 + 0.5).astype(np.uint8))[..., ::-1])
shutil.copy(based / "originals.json", out / "originals.json")
rep = {"concept": concept_p, "size": S, "uv_mirror_error_mm": round(sym_mm, 2), "body_gain_rgb_linear": [round(float(g), 3) for g in gain],
       "share_region": round(float((region > 0.5).mean()), 4), "share_clean_of_region": round(float(((valid > 0.5) & (region > 0.5)).sum() / max((region > 0.5).sum(), 1)), 3),
       "share_mirrored_of_region": round(float(((valid <= 0.5) & (valid[:, ::-1] > 0.5) & (region > 0.5)).sum() / max((region > 0.5).sum(), 1)), 3),
       "concept_skin_srgb": [round(float(x), 3) for x in srgb(glob)]}
(out / "concept_face.json").write_text(json.dumps(rep, indent=1))
print("CONCEPT FACE", json.dumps(rep), flush=True)
vis = np.zeros((S, S, 3), np.uint8)
vis[..., 1] = (valid * 255).astype(np.uint8)
vis[..., 2] = ((region - valid).clip(0, 1) * 255).astype(np.uint8)
cv2.imwrite(str(out / "check_weights.jpg"), cv2.resize(vis, (1024, 1024)))
cv2.imwrite(str(out / "check_texture.jpg"), cv2.resize(tex[..., ::-1], (1024, 1024)))

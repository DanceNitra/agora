"""Paint the p6 brow fill (brow pomade under the hairs) into the face Basecolor, using the p6 shape measured in
eye-width units (makeup/p6_brow.json, right brow, the unoccluded one): a straight top edge rising from the head to
a peak above the outer eye corner, then a short dropping tail. Placed with Depesa's own UV eye corners.
The shape is built in the p6 photo (eye frame of each p6 eye) and carried to the UV texture with a thin-plate
spline fitted on the MediaPipe landmarks around the eyes, brows and forehead, because the UV is not isotropic.
Usage: brow_fill.py <in_bc.png> <landmarks.json> <out_bc.png> <out_mask.png> <p6_landmarks.json>"""
from scipy.interpolate import RBFInterpolator
import json, sys
import cv2, numpy as np
bc = cv2.imread(sys.argv[1]); H, W = bc.shape[:2]
L = np.array(json.load(open(sys.argv[2]))) * (W / 2048.0)
# shape in eye frame (u along the eye from inner corner, v up), eye-width units, from the p6 measurement
U_TOP = [(-0.06, 0.41), (0.97, 0.57), (1.05, 0.575), (1.42, 0.48)]          # straight rise, flat peak, tail
U_BOT = [(1.42, 0.41), (0.97, 0.455), (0.16, 0.31), (-0.06, 0.315)]
HEAD = [(-0.06, 0.315), (-0.09, 0.36), (-0.06, 0.41)]                       # soft square head
shape = np.array(U_TOP + U_BOT + HEAD)
mask = np.zeros((H, W), np.float32)
# 1) remove the brows painted into the KeenFace skin: dark pixels in a band around the brow landmarks -> inpaint
BIDX = [70, 63, 105, 66, 107, 46, 53, 52, 65, 55, 300, 293, 334, 296, 336, 276, 283, 282, 295, 285]
band = np.zeros((H, W), np.uint8)
for grp in (BIDX[:10], BIDX[10:]):
    hull = cv2.convexHull(L[grp].astype(np.int32)); cv2.fillConvexPoly(band, hull, 255)
band = cv2.dilate(band, np.ones((int(70 * W / 2048),) * 2, np.uint8))
lab = cv2.cvtColor(bc, cv2.COLOR_BGR2LAB)[..., 0].astype(np.float32)
ring = cv2.dilate(band, np.ones((41, 41), np.uint8)) - band
skinL = np.median(lab[ring > 0])
dark = ((lab < skinL - 12) & (band > 0)).astype(np.uint8) * 255
dark = cv2.dilate(dark, np.ones((9, 9), np.uint8))
bc = cv2.inpaint(bc, dark, 25, cv2.INPAINT_TELEA)
bc = np.where(dark[..., None] > 0, cv2.GaussianBlur(bc, (0, 0), 6), bc)
# match the patched skin to the surrounding skin tone (inpaint comes out lighter), with a soft edge
labc = cv2.cvtColor(bc, cv2.COLOR_BGR2LAB).astype(np.float32)
soft = cv2.GaussianBlur(dark.astype(np.float32) / 255, (0, 0), 12)[..., None]
for ch in range(3):
    d = np.median(labc[..., ch][ring > 0]) - np.median(labc[..., ch][dark > 0])
    labc[..., ch] += d * soft[..., 0]
bc = cv2.cvtColor(np.clip(labc, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)
cv2.imwrite(sys.argv[4].replace(".png", "_removed.png"), bc)
P6 = np.array(json.load(open(sys.argv[5])))
IDX = sorted(set([33, 133, 362, 263, 159, 145, 386, 374, 157, 158, 160, 161, 384, 385, 387, 388, 70, 63, 105, 66, 107,
                  46, 53, 52, 65, 55, 300, 293, 334, 296, 336, 276, 283, 282, 295, 285, 9, 8, 168, 6, 151, 108, 337,
                  69, 299, 104, 333, 67, 297, 109, 338, 10, 156, 383, 124, 353, 226, 446]))
# 2) the p6 shape, built on her own brow landmarks so it sits on her brow bone:
#    head where her brow starts, a STRAIGHT rising top edge to a sharp peak above the outer eye corner,
#    then a straight, short dropping tail; bottom edge roughly parallel, thinning toward the tail.
SIDES = {"R": ([107, 66, 105, 63, 70], [55, 65, 52, 53, 46], 133, 33),
         "L": ([336, 296, 334, 293, 300], [285, 295, 282, 283, 276], 362, 263)}
for sd, (up, lo, inner, outer) in [("L", SIDES["L"])]:   # one shape, mirrored to the other side below
    U, B = L[up], L[lo]
    ei, eo = L[inner], L[outer]; ew = np.linalg.norm(eo - ei); ex = (eo - ei) / ew
    th0 = np.linalg.norm(U[0] - B[0])                       # her head thickness
    ANG = np.radians(13.0)                                   # p6: straight top edge rising at a steady angle
    TAIL = np.radians(34.0)                                  # p6: after the break the tail drops at a sharp angle
    HB = B[0] + (B[0] - U[0]) * 0.05                        # head bottom at her brow start
    HT = HB - np.array([0, 0.68 * th0])                     # head top: softer, smaller head
    END = U[4][0]                                            # brow ends where her brow ends
    span = END - HT[0]
    PKx = HT[0] + 0.66 * span                                # the BREAK at two thirds of the length (p6: ~0.70)
    PK = np.array([PKx, HT[1] - abs(PKx - HT[0]) * np.tan(ANG)])
    TE = np.array([END, PK[1] + abs(END - PKx) * np.tan(TAIL)])
    PB = PK + np.array([0, 0.55 * th0])                     # the bottom edge breaks right under the top break
    TB = TE + np.array([-np.sign(span) * 0.04 * th0, 0.06 * th0])  # tail tapers to a point
    HEADC = HT + (HB - HT) * 0.5 - ex * 0.05 * th0
    # rounded head: the front edge bulges a little instead of a square cut
    HC1 = HT + (HB - HT) * 0.25 - ex * 0.06 * th0; HC2 = HT + (HB - HT) * 0.75 - ex * 0.06 * th0
    poly = np.array([HT, PK, TE, TB, PB, HB, HC2, HC1], np.int32)
    m = np.zeros((H, W), np.uint8); cv2.fillPoly(m, [poly], 255)
    uu = ((np.indices((H, W))[::-1].transpose(1, 2, 0) - HT) @ ex) / max(1.0, np.linalg.norm(PK - HT))
    dens = np.clip(0.28 + 0.72 * (np.clip(uu, 0, None) / 0.40) ** 1.3, 0.28, 1.0)   # p6: light brushed-up head, full body
    one = (m / 255.0) * dens
    mask = np.maximum(mask, np.maximum(one, one[:, ::-1]))   # the UV is symmetric about its centre (paired landmarks sum to 2047/2048)
    print(sd, "head thickness px", round(float(th0), 1), "top edge angle deg",
          round(float(np.degrees(np.arctan2(-(PK - HT)[1], abs((PK - HT)[0])))), 1))
mask = cv2.GaussianBlur(mask, (0, 0), W / 2048.0 * 2.2)
# hair-stroke breakup so it reads as filled hairs, not a sticker
rng = np.random.default_rng(3)
noise = cv2.GaussianBlur(rng.random((H, W)).astype(np.float32), (0, 0), 1.0)
mask = mask * (0.82 + 0.18 * (noise - noise.mean()) / (noise.std() + 1e-6) * 0.5)
mask = np.clip(mask, 0, 1)
col = np.array([14, 16, 21], np.float32)          # BGR, near-black warm brown
out = bc.astype(np.float32) * (1 - 0.95 * mask[..., None]) + col * (0.95 * mask[..., None])
cv2.imwrite(sys.argv[3], np.clip(out, 0, 255).astype(np.uint8))
cv2.imwrite(sys.argv[4], (mask * 255).astype(np.uint8))
ys, xs = np.nonzero(mask > 0.3)
crop = out[ys.min() - 60:ys.max() + 60, xs.min() - 60:xs.max() + 60]
cv2.imwrite(sys.argv[4].replace(".png", "_preview.png"), crop.astype(np.uint8))

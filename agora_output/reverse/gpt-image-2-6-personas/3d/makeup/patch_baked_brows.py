"""The MetaHuman build bakes a stale brow area into T_Head_LOD1_BC_VT. Patch the baked texture: in the brow region
(union of every brow mask, dilated), replace the baked pixels by our look texture (same head UV), tone-matched to the
baked skin around it, with a wide feather. Usage: patch_baked_brows.py <baked.png> <look.png> <out.png>"""
import json, sys
import cv2, numpy as np
bk = cv2.imread(sys.argv[1]); H, W = bk.shape[:2]
lk = cv2.resize(cv2.imread(sys.argv[2]), (W, H), interpolation=cv2.INTER_AREA)
L = np.array(json.load(open('keenface/alb_landmarks.json'))) * (W / 2048)
reg = np.zeros((H, W), np.uint8)
for grp in ([70, 63, 105, 66, 107, 46, 53, 52, 65, 55], [300, 293, 334, 296, 336, 276, 283, 282, 295, 285]):
    pts = L[grp]; c = pts.mean(0)
    cv2.fillConvexPoly(reg, cv2.convexHull(((pts - c) * np.array([1.75, 2.6]) + c).astype(np.int32)), 255)
reg = cv2.dilate(reg, np.ones((int(40 * W / 2048),) * 2, np.uint8))
# keep the eyes (baked liner, lids) untouched: cut the region above each eye's upper lid crease
yy = np.arange(H)[:, None] * np.ones((1, W))
for crease, xr in (([225, 224, 223, 222, 221], (0, W // 2)), ([445, 444, 443, 442, 441], (W // 2, W))):
    lim = L[crease][:, 1].min() - 6 * W / 2048
    reg[:, xr[0]:xr[1]][yy[:, xr[0]:xr[1]] > lim] = 0
ring = cv2.dilate(reg, np.ones((31, 31), np.uint8)) - reg
lb = cv2.cvtColor(bk, cv2.COLOR_BGR2LAB).astype(np.float32); ll = cv2.cvtColor(lk, cv2.COLOR_BGR2LAB).astype(np.float32)
for ch in range(3):                                   # bring the look's colour to the baked skin tone
    ll[..., ch] += np.median(lb[..., ch][ring > 0]) - np.median(ll[..., ch][ring > 0])
lk2 = cv2.cvtColor(np.clip(ll, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR).astype(np.float32)
a = cv2.GaussianBlur(cv2.erode(reg, np.ones((41, 41), np.uint8)).astype(np.float32) / 255, (0, 0), 22)[..., None]   # audit v30: no hard patch edge
out = bk.astype(np.float32) * (1 - a) + lk2 * a
cv2.imwrite(sys.argv[3], np.clip(out, 0, 255).astype(np.uint8))
ys, xs = np.nonzero(reg); print("patched px", len(xs))

"""The MetaHuman build bakes a stale lip area into T_Head_LOD1_BC_VT, so a lip look painted in our BaseColor
never reaches the render. Patch the baked texture in the lip region (outer lip contour, dilated) with our look
texture, tone-matched to the baked skin in a ring around the lips, feathered.
Usage: patch_baked_lips.py <baked.png> <look.png> <out.png>"""
import json, sys
import cv2, numpy as np
bk = cv2.imread(sys.argv[1]); H, W = bk.shape[:2]
lk = cv2.resize(cv2.imread(sys.argv[2]), (W, H), interpolation=cv2.INTER_AREA)
L = np.array(json.load(open('keenface/alb_landmarks.json')))[:, :2] * (W / 2048)
OUT = [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291, 375, 321, 405, 314, 17, 84, 181, 91, 146]
mw = np.linalg.norm(L[291] - L[61])
reg = np.zeros((H, W), np.uint8)
cv2.fillPoly(reg, [np.round(L[OUT]).astype(np.int32)], 255)
reg = cv2.dilate(reg, np.ones((int(mw * 0.14),) * 2, np.uint8))
ring = cv2.dilate(reg, np.ones((int(mw * 0.08),) * 2, np.uint8)) - reg
lb = cv2.cvtColor(bk, cv2.COLOR_BGR2LAB).astype(np.float32); ll = cv2.cvtColor(lk, cv2.COLOR_BGR2LAB).astype(np.float32)
for ch in range(3):
    ll[..., ch] += np.median(lb[..., ch][ring > 0]) - np.median(ll[..., ch][ring > 0])
lk2 = cv2.cvtColor(np.clip(ll, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR).astype(np.float32)
k = int(mw * 0.06) | 1
a = cv2.GaussianBlur(cv2.erode(reg, np.ones((k, k), np.uint8)).astype(np.float32) / 255, (0, 0), k / 2)[..., None]
out = bk.astype(np.float32) * (1 - a) + lk2 * a
cv2.imwrite(sys.argv[3], np.clip(out, 0, 255).astype(np.uint8))
print("lip patched px", int((reg > 0).sum()), "mouth_px %.0f" % mw)

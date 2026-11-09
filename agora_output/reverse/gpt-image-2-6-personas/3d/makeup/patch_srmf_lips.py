"""Soft sheen on the lips in the baked SRMF (G = roughness): lower roughness in a soft ellipse on the lower-lip
centre and a smaller one on the upper lip, nothing elsewhere. p6 lower lip shows 0.4 % specular pixels (satin).
Usage: patch_srmf_lips.py <srmf.png> <out.png> <lower_drop 0..1> <upper_drop 0..1>"""
import json, sys
import cv2, numpy as np
s = cv2.imread(sys.argv[1], cv2.IMREAD_UNCHANGED); H, W = s.shape[:2]
L = np.array(json.load(open('keenface/alb_landmarks.json')))[:, :2] * (W / 2048)
mw = np.linalg.norm(L[291] - L[61])
m = np.zeros((H, W), np.float32)
c = (L[14] + L[17]) / 2
cv2.ellipse(m, tuple(np.round(c).astype(int)), (int(mw * float(sys.argv[5] if len(sys.argv) > 5 else 0.24)), int(mw * float(sys.argv[6] if len(sys.argv) > 6 else 0.07))), 0, 0, 360, float(sys.argv[3]), -1)
cu = (L[0] + L[13]) / 2
cv2.ellipse(m, tuple(np.round(cu).astype(int)), (int(mw * 0.16), int(mw * 0.035)), 0, 0, 360, float(sys.argv[4]), -1)
m = cv2.GaussianBlur(m, (0, 0), mw * 0.05)
g = 1 if s.ndim == 3 else None   # OpenCV BGR(A): index 1 = G
scale = 65535.0 if s.dtype == np.uint16 else 255.0
ch = s[..., g].astype(np.float32) / scale
print("roughness at lower lip before %.3f" % float(ch[int(c[1]), int(c[0])]))
ch = np.clip(ch - m, 0.05, 1)
s[..., g] = (ch * scale).astype(s.dtype)
print("roughness at lower lip after %.3f" % float(ch[int(c[1]), int(c[0])]), s.dtype, s.shape)
cv2.imwrite(sys.argv[2], s)

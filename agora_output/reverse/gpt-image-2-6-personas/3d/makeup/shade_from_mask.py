"""Soft brow shadow under the hairs from the UV brow mask: fills the gaps between hairs, fades out at the edges.
Usage: shade_from_mask.py <bc_without_brows.png> <mask.png> <out_bc.png> [opacity]"""
import sys, cv2, numpy as np
bc = cv2.imread(sys.argv[1]); H, W = bc.shape[:2]; s = W / 2048
m = cv2.resize(cv2.imread(sys.argv[2], 0), (W, H)).astype(np.float32) / 255
op = float(sys.argv[4]) if len(sys.argv) > 4 else 0.7
sh = cv2.GaussianBlur(cv2.erode(m, np.ones((5, 5), np.uint8)), (0, 0), 4 * s) * op
out = bc.astype(np.float32) * (1 - sh[..., None]) + np.array([28, 33, 42], np.float32) * sh[..., None]
cv2.imwrite(sys.argv[3], np.clip(out, 0, 255).astype(np.uint8)); print("ok")

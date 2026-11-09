"""UV hit list from Blender (makeup/brow_uv_hits.json) -> 4096 brow mask (makeup/brow_fill_mask.png)."""
import json, cv2, numpy as np
uv = np.array(json.load(open('makeup/brow_uv_hits.json'))); S = 4096; M = np.zeros((S, S), np.uint8)
for u, v in uv: cv2.circle(M, (int(u * S), int((1 - v) * S)), 9, 255, -1)
M = cv2.morphologyEx(M, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25)))
cv2.imwrite('makeup/brow_fill_mask.png', M); print("mask px", int((M > 0).sum()))

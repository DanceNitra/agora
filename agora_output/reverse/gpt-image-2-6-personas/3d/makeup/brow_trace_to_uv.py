"""Carry the hand-traced p6 brow (render frame 57 pixels) to the face UV with a thin-plate spline from the render's
MediaPipe landmarks to the UV landmarks (same face), mirror it (the UV is symmetric), and paint only a SOFT shadow
under the hairs: low opacity, wide feather that fades to nothing. The hairs carry the brow, not the paint.
Usage: brow_trace_to_uv.py <bc_without_brows.png> <out_bc.png> <out_mask.png> <shift_down_px>"""
import json, sys
import cv2, numpy as np
from scipy.interpolate import RBFInterpolator
bc = cv2.imread(sys.argv[1]); H, W = bc.shape[:2]
UVL = np.array(json.load(open('keenface/alb_landmarks.json'))) * (W / 2048)
RL = np.array(json.load(open('makeup/render0057_landmarks.json')))
poly = np.array(json.load(open('makeup/p6_brow_trace.json'))['poly'], float) + [0, float(sys.argv[4])]
IDX = sorted(set([33, 133, 362, 263, 159, 145, 386, 374, 157, 158, 160, 161, 384, 385, 387, 388, 70, 63, 105, 66, 107,
                  46, 53, 52, 65, 55, 300, 293, 334, 296, 336, 276, 283, 282, 295, 285, 9, 8, 168, 6, 151, 108, 337,
                  69, 299, 104, 333, 67, 297, 109, 338, 10, 156, 383, 124, 353, 226, 446, 225, 445, 224, 444, 113, 342]))
tps = RBFInterpolator(RL[IDX], UVL[IDX], kernel='thin_plate_spline', smoothing=0.5)
dense = []
for a, b in zip(poly, np.roll(poly, -1, 0)):
    for t in np.linspace(0, 1, 10, endpoint=False):
        dense.append(a + (b - a) * t)
uvp = tps(np.array(dense)).astype(np.int32)
m = np.zeros((H, W), np.uint8); cv2.fillPoly(m, [uvp], 255)
m = np.maximum(m, m[:, ::-1])                                   # mirror to the other brow
cv2.imwrite(sys.argv[3], m)                                     # hard mask: where the hairs grow
# soft shadow: shrink a little, feather wide so it fades to nothing, 35 % at most
sh = cv2.erode(m, np.ones((15, 15), np.uint8)).astype(np.float32) / 255
sh = cv2.GaussianBlur(sh, (0, 0), W / 2048 * 9) * 0.35
col = np.array([30, 34, 42], np.float32)
out = bc.astype(np.float32) * (1 - sh[..., None]) + col * sh[..., None]
cv2.imwrite(sys.argv[2], np.clip(out, 0, 255).astype(np.uint8))
ys, xs = np.nonzero(m)
print("uv bbox", xs.min(), xs.max(), ys.min(), ys.max())

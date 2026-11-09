"""Align telephoto renders to the p6 frame by MediaPipe landmarks and tile them: python cmp_sheet.py out.png a.png b.png ..."""
import sys, json
import cv2, numpy as np
import mp_lm
from mp_regions import USED
from warp_lib import similarity
ref = np.array(json.load(open("mp_ref_512x768.json")))
S = 2.0
tiles = [cv2.resize(cv2.imread("ref_512x768.png"), None, fx=S, fy=S, interpolation=cv2.INTER_CUBIC)]
for name in sys.argv[2:]:
    p = mp_lm.detect(name)
    s, R, t = similarity(p[USED], ref[USED] * S)
    tiles.append(cv2.warpAffine(cv2.imread(name), np.hstack([s * R.T, t[:, None]]), (int(512 * S), int(768 * S)), flags=cv2.INTER_AREA))
crop = lambda im: im[int(120 * S):int(560 * S), int(70 * S):int(440 * S)]
cv2.imwrite(sys.argv[1], np.hstack([crop(t) for t in tiles]))

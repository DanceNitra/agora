"""Measure lip makeup zones on a face image from its MediaPipe 478 landmarks.

Usage: python lip_measure.py <image> <landmarks.json> <out.json>
Zones: upper lip body, lower lip body, outer rim (liner band), centre of lower lip (gloss/ombre core),
skin ring just outside the lips (overline / contrast reference).
Reports Lab median per zone, rim-vs-body darkening (liner), centre-vs-rim lightness (ombre),
specular fraction on the lower lip (gloss), lip heights relative to mouth width (fullness).
"""
import json
import sys

import cv2
import numpy as np

UP_OUT = [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291]
UP_IN = [291, 308, 415, 310, 311, 312, 13, 82, 81, 80, 191, 78, 61]
LO_OUT = [291, 375, 321, 405, 314, 17, 84, 181, 91, 146, 61]
LO_IN = [61, 78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308, 291]

img = cv2.imread(sys.argv[1], cv2.IMREAD_COLOR)
lm = np.array(json.load(open(sys.argv[2])))[:, :2]
H, W = img.shape[:2]
lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
lab[..., 0] *= 100 / 255
lab[..., 1:] -= 128


def poly(idx):
    m = np.zeros((H, W), np.uint8)
    cv2.fillPoly(m, [np.round(lm[idx]).astype(np.int32)], 1)
    return m


upper = poly(UP_OUT + UP_IN[1:-1])
lower = poly(LO_OUT + LO_IN[1:-1])
lips = np.maximum(upper, lower)
mw = np.linalg.norm(lm[291] - lm[61])
k = max(3, int(mw * 0.05)) | 1
rim = lips - cv2.erode(lips, np.ones((k, k), np.uint8))
core = cv2.erode(lower, np.ones((3 * k, 3 * k), np.uint8))
ring = cv2.dilate(lips, np.ones((3 * k, 3 * k), np.uint8)) - cv2.dilate(lips, np.ones((k, k), np.uint8))


def stat(m):
    v = lab[m > 0]
    return [round(float(x), 1) for x in np.median(v, 0)] if len(v) else None


lo_L = lab[..., 0][lower > 0]
spec = float((lo_L > np.percentile(lo_L, 50) + 25).mean()) if len(lo_L) else None
out = {
    "mouth_width_px": round(float(mw), 1),
    "upper_height_mw": round(float(np.linalg.norm(lm[0] - lm[13]) / mw), 3),
    "lower_height_mw": round(float(np.linalg.norm(lm[17] - lm[14]) / mw), 3),
    "mouth_open_mw": round(float(np.linalg.norm(lm[13] - lm[14]) / mw), 3),
    "lab_upper": stat(upper), "lab_lower": stat(lower), "lab_rim": stat(rim),
    "lab_lower_core": stat(core), "lab_skin_ring": stat(ring),
    "lower_specular_fraction": round(spec, 3) if spec is not None else None,
    "lower_L_p95_minus_median": round(float(np.percentile(lo_L, 95) - np.median(lo_L)), 1),
}
out["liner_dL_rim_minus_body"] = round(out["lab_rim"][0] - (out["lab_upper"][0] + out["lab_lower"][0]) / 2, 1)
out["ombre_dL_core_minus_rim"] = round(out["lab_lower_core"][0] - out["lab_rim"][0], 1)
out["lip_vs_skin_dL"] = round((out["lab_upper"][0] + out["lab_lower"][0]) / 2 - out["lab_skin_ring"][0], 1)
out["lip_chroma"] = round(float(np.hypot(*out["lab_lower"][1:])), 1)
out["lip_hue_deg"] = round(float(np.degrees(np.arctan2(out["lab_lower"][2], out["lab_lower"][1]))), 1)
json.dump(out, open(sys.argv[3], "w"), indent=1)
print(json.dumps(out))

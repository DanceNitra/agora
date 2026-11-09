"""Paint a lip look onto the head BaseColor (UV space), on top of an existing look texture.

Usage: python lip_paint.py <base_BC.png> <lip_look.json> <out_BC.png> [<debug_sheet.png>]
Built from the p6 lip measurement (review/lips_rea/p6.json):
  - ombre: the lower-lip centre is lighter and more saturated than the rim (p6: +4.3 L, chroma 35 vs 27);
  - no hard dark liner (p6 rim L = body L), the edge is a soft deeper band;
  - upper lip deeper than lower (p6: -5.5 L);
  - lower lip tall against the upper (p6: 2.1x).
Look keys (all optional):
  colour [R,G,B]       body colour, applied as a Lab tint that keeps the lip lines
  tint_opacity         0..1
  upper_dL             extra L on the upper lip (negative = deeper)
  rim_colour, rim_opacity, rim_width   deeper soft band inside the outline (width in mouth widths)
  core_colour, core_opacity, core_size centre glow on the lower lip (size in mouth widths)
  overline_lower, overline_upper       push the painted outline out (mouth widths), centre-weighted
  overline_bow                          extra lift at the two cupid's-bow peaks (mouth widths)
"""
import json
import sys

import cv2
import numpy as np

UP_OUT = [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291]
LO_OUT = [291, 375, 321, 405, 314, 17, 84, 181, 91, 146, 61]
UP_IN = [291, 308, 415, 310, 311, 312, 13, 82, 81, 80, 191, 78, 61]
LO_IN = [61, 78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308, 291]
LM_PATH = "C:/Users/Danculus/agora/agora_output/reverse/gpt-image-2-6-personas/3d/keenface/alb_landmarks.json"

base = cv2.imread(sys.argv[1], cv2.IMREAD_COLOR)
look = json.load(open(sys.argv[2]))
H, W = base.shape[:2]
lm = np.array(json.load(open(LM_PATH)))[:, :2] * (W / 2048)
mw = float(np.linalg.norm(lm[291] - lm[61]))
centre = (lm[61] + lm[291]) / 2


def pushed(idx, amount, bow=0.0, peaks=(37, 267)):
    """Outline points pushed away from the mouth centre line, most at the middle, zero at the corners."""
    pts = lm[idx].copy()
    for j, i in enumerate(idx):
        t = abs(pts[j, 0] - centre[0]) / (mw / 2)
        w = max(0.0, 1 - t) ** 0.7
        d = pts[j] - centre
        n = d / (np.linalg.norm(d) + 1e-6)
        extra = bow * mw if i in peaks else 0.0
        pts[j] = pts[j] + n * (amount * mw * w + extra)
    return pts


def fill(pts):
    m = np.zeros((H, W), np.uint8)
    cv2.fillPoly(m, [np.round(pts).astype(np.int32)], 1)
    return m.astype(np.float32)


def soft(m, px):
    k = int(px * 2) | 1
    return cv2.GaussianBlur(m, (k, k), px / 2) if px > 0 else m


ou, ol = look.get("overline_upper", 0.0), look.get("overline_lower", 0.0)
upper = fill(np.vstack([pushed(UP_OUT, ou, look.get("overline_bow", 0.0)), lm[UP_IN[1:-1]]]))
lower = fill(np.vstack([pushed(LO_OUT, ol), lm[LO_IN[1:-1]]]))
full = fill(np.vstack([pushed(UP_OUT, ou, look.get("overline_bow", 0.0)), pushed(LO_OUT, ol)[1:-1]]))
lips_hard = np.maximum(np.maximum(upper, lower), full)
edge_soft = mw * look.get("edge_soft", 0.012)
lips = soft(lips_hard, edge_soft)

lab = cv2.cvtColor(base, cv2.COLOR_BGR2LAB).astype(np.float32)


def tint(lab, colour, mask, opacity, keep_L=0.6):
    tc = cv2.cvtColor(np.uint8([[colour[::-1]]]), cv2.COLOR_BGR2LAB).astype(np.float32)[0, 0]
    tgt = lab.copy()
    tgt[..., 1:] = tc[1:]
    tgt[..., 0] = lab[..., 0] * keep_L + tc[0] * (1 - keep_L)
    a = (mask * opacity)[..., None]
    return lab * (1 - a) + tgt * a


lab = tint(lab, look["colour"], lips, look.get("tint_opacity", 0.8), keep_L=look.get("keep_L", 0.6))
if look.get("upper_dL"):
    lab[..., 0] += soft(upper, edge_soft) * look["upper_dL"] * 2.55
if look.get("rim_opacity"):
    k = max(3, int(mw * look.get("rim_width", 0.06))) | 1
    rim = lips_hard - cv2.erode(lips_hard, np.ones((k, k), np.uint8))
    lab = tint(lab, look["rim_colour"], soft(rim, k * 0.6) * lips, look["rim_opacity"], keep_L=0.5)
if look.get("core_opacity"):
    core = np.zeros((H, W), np.float32)
    c = (lm[14] + lm[17]) / 2
    s = look.get("core_size", 0.22) * mw
    cv2.ellipse(core, tuple(np.round(c).astype(int)), (int(s), int(s * 0.45)), 0, 0, 360, 1.0, -1)
    up_c = (lm[0] + lm[13]) / 2
    cv2.ellipse(core, tuple(np.round(up_c).astype(int)), (int(s * 0.8), int(s * 0.25)), 0, 0, 360, 0.6, -1)
    lab = tint(lab, look["core_colour"], soft(core, s * 0.5) * lips_hard, look["core_opacity"], keep_L=0.55)

out = cv2.cvtColor(np.clip(lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)
cv2.imwrite(sys.argv[3], out)
x0, y0 = np.round(lm[UP_OUT + LO_OUT].min(0) - mw * 0.25).astype(int)
x1, y1 = np.round(lm[UP_OUT + LO_OUT].max(0) + mw * 0.25).astype(int)
if len(sys.argv) > 4:
    crop = np.hstack([base[y0:y1, x0:x1], out[y0:y1, x0:x1]])
    cv2.imwrite(sys.argv[4], crop)
print("LIPPAINT", sys.argv[3], "mouth_px %.0f" % mw, "crop", x0, y0, x1, y1)

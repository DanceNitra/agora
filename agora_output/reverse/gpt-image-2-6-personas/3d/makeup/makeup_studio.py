"""Makeup Studio: paint a makeup look onto the clean MetaHuman-UV skin texture as ordered, masked layers.

Usage: python makeup_studio.py <look.json> <out_prefix>
Inputs: clean albedo (look["base"]), SRMF map (look["srmf"]), UV landmarks (look["landmarks"], MediaPipe 478 points
detected on the albedo, in the coordinates of look["landmarks_size"]).
Outputs: <out_prefix>_BC.png (basecolor with makeup), <out_prefix>_SRMF.png (roughness lowered where the look is glossy),
<out_prefix>_masks.png (debug sheet of every layer mask).
Layer order follows a makeup artist: foundation, concealer, contour, blush, highlight, brows, eyeshadow, eyeliner,
lash line, lip liner, lipstick, gloss. Each layer: colour, opacity, softness (px at 4K), blend, roughness change.
"""
import json
import sys

import cv2
import numpy as np

LOOK = json.load(open(sys.argv[1], encoding="utf-8"))
OUT = sys.argv[2]
base = cv2.imread(LOOK["base"], cv2.IMREAD_COLOR).astype(np.float32) / 255.0
srmf = cv2.imread(LOOK["srmf"], cv2.IMREAD_UNCHANGED).astype(np.float32)
H, W = base.shape[:2]
lm = np.array(json.load(open(LOOK["landmarks"]))) * (W / LOOK["landmarks_size"])

# MediaPipe index groups (image-left eye = "A", image-right eye = "B")
EYE = {
    "A": {"upper": [33, 246, 161, 160, 159, 158, 157, 173, 133], "lower": [33, 7, 163, 144, 145, 153, 154, 155, 133],
          "outer": 33, "inner": 133, "brow_up": [70, 63, 105, 66, 107], "brow_lo": [46, 53, 52, 65, 55]},
    "B": {"upper": [263, 466, 388, 387, 386, 385, 384, 398, 362], "lower": [263, 249, 390, 373, 374, 380, 381, 382, 362],
          "outer": 263, "inner": 362, "brow_up": [300, 293, 334, 296, 336], "brow_lo": [276, 283, 282, 295, 285]},
}
LIPS_OUT = [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291, 375, 321, 405, 314, 17, 84, 181, 91, 146]
LIP_UPPER_OUT = [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291]
LIP_LOWER_MID = [78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308, 291, 375, 321, 405, 314, 17, 84, 181, 91, 146, 61]
CHEEK = {"A": [116, 117, 118, 119, 100, 101, 50, 123], "B": [345, 346, 347, 348, 329, 330, 280, 352]}
HOLLOW = {"A": (234, 61), "B": (454, 291)}  # from cheek side towards the mouth corner, under the cheekbone
NOSE_BRIDGE = [168, 6, 197, 195, 5]
UNDER_EYE = {"A": [7, 163, 144, 145, 153, 154, 155], "B": [249, 390, 373, 374, 380, 381, 382]}


def P(i):
    return lm[i]


def blank():
    return np.zeros((H, W), np.float32)


def soft(m, s):
    if s > 0:
        k = int(s * 3) | 1
        m = cv2.GaussianBlur(m, (k, k), s)
    return np.clip(m, 0, 1)


def poly(m, pts, val=1.0):
    cv2.fillPoly(m, [np.round(np.array(pts)).astype(np.int32)], val)
    return m


def line(m, pts, width, val=1.0):
    cv2.polylines(m, [np.round(np.array(pts)).astype(np.int32)], False, val, int(max(1, width)), cv2.LINE_AA)
    return m


def eye_width(e):
    return np.linalg.norm(P(EYE[e]["outer"]) - P(EYE[e]["inner"]))


LAB = cv2.cvtColor((base * 255).astype(np.uint8), cv2.COLOR_BGR2LAB).astype(np.float32)


def roi_box(idx, pad):
    p = lm[idx]
    x0, y0 = np.maximum(p.min(0) - pad, 0).astype(int)
    x1, y1 = np.minimum(p.max(0) + pad, [W - 1, H - 1]).astype(int)
    return x0, y0, x1, y1


def seg_brows():
    m = blank()
    for e in ("A", "B"):
        idx = EYE[e]["brow_up"] + EYE[e]["brow_lo"]
        x0, y0, x1, y1 = roi_box(idx, 90)
        L = LAB[y0:y1, x0:x1, 0]
        thr = np.median(L) - 14
        hair = (L < thr).astype(np.uint8)
        hair = cv2.morphologyEx(hair, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        n, lab, st, _ = cv2.connectedComponentsWithStats(hair)
        if n > 1:  # keep the largest dark blob: the brow
            k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
            hair = (lab == k).astype(np.uint8)
        hair = cv2.morphologyEx(hair, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
        m[y0:y1, x0:x1] = np.maximum(m[y0:y1, x0:x1], hair.astype(np.float32))
    return m


def seg_lips():
    m = blank()
    x0, y0, x1, y1 = roi_box(LIPS_OUT, 60)
    a = LAB[y0:y1, x0:x1, 1]
    skin_a = np.median(LAB[y0:y1, x0:x1, 1][:20])  # top rows are skin
    lip = (a > skin_a + 7).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(lip)
    if n > 1:
        k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
        lip = (lab == k).astype(np.uint8)
    lip = cv2.morphologyEx(lip, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    cnts, _ = cv2.findContours(lip, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    filled = np.zeros_like(lip)
    cv2.drawContours(filled, cnts, -1, 1, -1)
    m[y0:y1, x0:x1] = filled.astype(np.float32)
    return m


def lash_curve(e):
    """Upper lash line: per column the darkest pixel in a band around the landmark lid line, smoothed."""
    E = EYE[e]
    up = np.array([P(i) for i in E["upper"]])
    xs = np.arange(int(up[:, 0].min()), int(up[:, 0].max()) + 1)
    order = np.argsort(up[:, 0])
    ylid = np.interp(xs, up[order, 0], up[order, 1])
    band = int(eye_width(e) * 0.12)
    ys = []
    for x, y in zip(xs, ylid):
        col = LAB[int(y) - band:int(y) + band, x, 0]
        ys.append(int(y) - band + int(np.argmin(cv2.GaussianBlur(col.reshape(-1, 1), (1, 9), 2).ravel())))
    ys = np.convolve(np.array(ys, float), np.ones(31) / 31, mode="same")
    ys[:15], ys[-15:] = ylid[:15] + (ys[15] - ylid[15]), ylid[-15:] + (ys[-16] - ylid[-16])
    return np.stack([xs, ys], 1)


def mask_for(layer):
    k, m = layer["kind"], blank()
    if k == "brows_seg":
        return soft(seg_brows(), layer.get("soft", 4) * (W / 4096))
    if k in ("lipstick_seg", "gloss_seg"):
        return soft(seg_lips(), layer.get("soft", 4) * (W / 4096))
    if k == "eyeliner_seg":
        for e in ("A", "B"):
            E = EYE[e]
            c = lash_curve(e)
            w = eye_width(e)
            out = P(E["outer"])
            outer_first = np.linalg.norm(c[0] - out) < np.linalg.norm(c[-1] - out)
            c = c if outer_first else c[::-1]
            n = len(c)
            for j in range(0, n - 1, 2):
                t = j / (n - 1)
                thick = w * (layer.get("outer_w", 0.05) * (1 - t) ** 1.5 + layer.get("inner_w", 0.012) * t)
                line(m, [c[j], c[min(j + 2, n - 1)]], thick)
            d = c[0] - c[12]
            d = d / np.linalg.norm(d)
            up = np.array([0.0, -1.0])
            ang = np.deg2rad(layer.get("wing_angle", 18))
            wing = d * np.cos(ang) + up * np.sin(ang)
            wing = wing / np.linalg.norm(wing)
            tip = c[0] + wing * w * layer.get("wing_len", 0.28)
            thick0 = w * layer.get("outer_w", 0.05)
            poly(m, [c[0] + np.array([0, thick0 * 0.5]), c[0] + np.array([0, -thick0 * 0.6]), tip])
        return soft(m, layer.get("soft", 2) * (W / 4096))
    for e in ("A", "B"):
        E = EYE[e]
        up = np.array([P(i) for i in E["upper"]])
        lo = np.array([P(i) for i in E["lower"]])
        w = eye_width(e)
        out, inn = P(E["outer"]), P(E["inner"])
        brow = np.array([P(i) for i in E["brow_lo"]])
        browc = brow.mean(0)
        lidc = up.mean(0)
        to_brow = browc - lidc
        if k == "brows":
            poly(m, [P(i) for i in E["brow_up"]] + [P(i) for i in E["brow_lo"]][::-1])
        elif k == "eyeshadow_lid":  # mobile lid up to the crease (about 45 % of the way to the brow)
            crease = up + to_brow * 0.45
            poly(m, list(up) + list(crease[::-1]))
        elif k == "eyeshadow_outer_v":  # darker outer third, swept up and out
            n = len(up)
            seg = up[: n // 3 + 1]
            crease = seg + to_brow * 0.55
            tip = out + (out - inn) / np.linalg.norm(out - inn) * w * 0.28 + to_brow * 0.35
            poly(m, list(seg) + [tip] + list(crease[::-1]))
        elif k == "lower_smudge":
            seg = lo[: len(lo) * 2 // 3 + 1]
            line(m, seg + np.array([0, w * 0.035]), w * layer.get("width", 0.06))
        elif k == "eyeliner":  # tightline along the upper lash line, thicker to the outer corner, plus a wing
            n = len(up)
            for j in range(n - 1):
                t = j / (n - 1)  # 0 at the outer corner
                thick = w * (layer.get("outer_w", 0.075) * (1 - t) + layer.get("inner_w", 0.02) * t)
                line(m, [up[j], up[j + 1]], thick)
            d = (out - inn) / np.linalg.norm(out - inn)
            upv = to_brow / np.linalg.norm(to_brow)
            ang = np.deg2rad(layer.get("wing_angle", 22))
            wing_dir = d * np.cos(ang) + upv * np.sin(ang)
            tip = out + wing_dir * w * layer.get("wing_len", 0.34)
            base_top = out + upv * w * layer.get("outer_w", 0.075) * 0.9
            poly(m, [out - upv * w * 0.01, base_top, tip])
        elif k == "lash_line_lower":
            line(m, lo[: len(lo) // 2 + 2], w * 0.025)
        elif k == "concealer":
            seg = np.array([P(i) for i in UNDER_EYE[e]])
            line(m, seg + np.array([0, w * 0.22]), w * 0.35)
        elif k == "contour":
            a, b = P(HOLLOW[e][0]), P(HOLLOW[e][1])
            p0 = a + (b - a) * 0.12
            p1 = a + (b - a) * 0.55
            line(m, [p0, p1], w * 0.45)
        elif k == "blush":
            c = np.array([P(i) for i in CHEEK[e]]).mean(0)
            cv2.ellipse(m, tuple(np.round(c).astype(int)), (int(w * 0.55), int(w * 0.32)), -15 if e == "A" else 15, 0, 360, 1.0, -1)
        elif k == "highlight":
            top = np.array([P(i) for i in CHEEK[e][:5]])
            line(m, top + to_brow * -0.05, w * 0.18)
    if k == "highlight":
        line(m, [P(i) for i in NOSE_BRIDGE], eye_width("A") * 0.08)
    if k in ("lipstick", "gloss_lips"):
        poly(m, [P(i) for i in LIPS_OUT])
    if k == "lip_liner":
        line(m, [P(i) for i in LIPS_OUT] + [P(LIPS_OUT[0])], eye_width("A") * layer.get("width", 0.05))
    if k == "gloss_lower_lip":
        poly(m, [P(i) for i in LIP_LOWER_MID])
    if k == "foundation":
        hull = cv2.convexHull(np.round(lm[:468]).astype(np.int32))
        cv2.fillConvexPoly(m, hull, 1.0)
    return soft(m, layer.get("soft", 8) * (W / 4096))


def blend(img, colour, mask, opacity, mode):
    c = np.array(colour[::-1], np.float32) / 255.0  # RGB -> BGR
    a = (mask * opacity)[..., None]
    if mode == "multiply":
        target = img * c
    elif mode == "screen":
        target = 1 - (1 - img) * (1 - c)
    elif mode == "lab_tint":  # move a/b toward the colour and L a little: keeps texture and lip lines
        lab = cv2.cvtColor((np.clip(img, 0, 1) * 255).astype(np.uint8), cv2.COLOR_BGR2LAB).astype(np.float32)
        tc = cv2.cvtColor(np.uint8([[np.array(colour[::-1])]]), cv2.COLOR_BGR2LAB).astype(np.float32)[0, 0]
        lab[..., 1:] = tc[1:]
        lab[..., 0] = lab[..., 0] * 0.6 + tc[0] * 0.4
        target = cv2.cvtColor(np.clip(lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR).astype(np.float32) / 255.0
    elif mode == "color":  # keep the skin's luminance, take the colour's hue and saturation
        lum = img.mean(2, keepdims=True)
        target = np.clip(c * (lum / max(c.mean(), 1e-3)), 0, 1)
    else:
        target = np.broadcast_to(c, img.shape)
    return img * (1 - a) + target * a


img = base.copy()
rough = srmf[..., 1].copy()  # SRMF: G = roughness (0..255)
sheet = []
for layer in LOOK["layers"]:
    if not layer.get("on", True):
        continue
    m = mask_for(layer)
    if layer.get("opacity", 0) > 0:
        img = blend(img, layer["colour"], m, layer["opacity"], layer.get("mode", "normal"))
    if "roughness_delta" in layer:
        rough = np.clip(rough + m * layer["roughness_delta"] * 255.0, 0, 255)
    sheet.append(cv2.resize((m * 255).astype(np.uint8), (512, 512)))
    print("layer", layer["name"], "coverage %.4f" % float(m.mean()))

out_srmf = srmf.copy()
out_srmf[..., 1] = rough
cv2.imwrite(OUT + "_BC.png", np.clip(img * 255, 0, 255).astype(np.uint8))
cv2.imwrite(OUT + "_SRMF.png", out_srmf.astype(srmf.dtype))
rows = [np.hstack(sheet[i:i + 6] + [np.zeros((512, 512), np.uint8)] * (6 - len(sheet[i:i + 6]))) for i in range(0, len(sheet), 6)]
cv2.imwrite(OUT + "_masks.png", np.vstack(rows))
print("done", OUT)

"""Face zones for makeup, as soft masks in MetaHuman head UV space.

Every MetaHuman head shares one UV layout, so MediaPipe landmarks detected once on a MetaHuman albedo
(`uv_landmarks.json`, 478 points in a 2048 px square) place every zone on any MetaHuman.
A zone function takes a `Face` (landmarks scaled to the target texture) and a params dict, and returns
a float32 mask in 0..1 of the texture size. Sizes are in eye widths, so they scale with the face.
Sides: "A" is the image-left eye in UV, "B" the image-right one; makeup zones are painted on both
unless params["sides"] says otherwise.
"""
import json
import os

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
UV_LANDMARKS = os.path.join(HERE, "data", "uv_landmarks.json")

EYE = {
    "A": {"upper": [33, 246, 161, 160, 159, 158, 157, 173, 133], "lower": [33, 7, 163, 144, 145, 153, 154, 155, 133],
          "outer": 33, "inner": 133, "brow_up": [70, 63, 105, 66, 107], "brow_lo": [46, 53, 52, 65, 55],
          "cheek": [116, 117, 118, 119, 100, 101, 50, 123], "hollow": (234, 61), "temple": [54, 21, 162, 127],
          "jaw": [172, 136, 150, 149], "nose_side": [193, 122, 196, 3, 51, 45], "corner": 61},
    "B": {"upper": [263, 466, 388, 387, 386, 385, 384, 398, 362], "lower": [263, 249, 390, 373, 374, 380, 381, 382, 362],
          "outer": 263, "inner": 362, "brow_up": [300, 293, 334, 296, 336], "brow_lo": [276, 283, 282, 295, 285],
          "cheek": [345, 346, 347, 348, 329, 330, 280, 352], "hollow": (454, 291), "temple": [284, 251, 389, 356],
          "jaw": [397, 365, 379, 378], "nose_side": [417, 351, 419, 248, 281, 275], "corner": 291},
}
LIPS_OUT = [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291, 375, 321, 405, 314, 17, 84, 181, 91, 146]
LIPS_IN = [78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95]
NOSE_BRIDGE = [168, 6, 197, 195, 5]
NOSE_TIP = [4, 1]
UNDER_TIP = [2, 94]
FOREHEAD = [10, 151, 9]
CHIN = [152, 175, 199]


class Face:
    def __init__(self, size, landmarks_path=UV_LANDMARKS, src_size=2048):
        self.H = self.W = size
        self.lm = np.array(json.load(open(landmarks_path)))[:, :2] * (size / src_size)

    def P(self, i):
        return self.lm[i]

    def eye_w(self, e):
        return float(np.linalg.norm(self.P(EYE[e]["outer"]) - self.P(EYE[e]["inner"])))

    def blank(self):
        return np.zeros((self.H, self.W), np.float32)


def _poly(m, pts, v=1.0):
    cv2.fillPoly(m, [np.round(np.asarray(pts)).astype(np.int32)], float(v), cv2.LINE_AA)
    return m


def _line(m, pts, width, v=1.0):
    cv2.polylines(m, [np.round(np.asarray(pts)).astype(np.int32)], False, float(v), int(max(1, width)), cv2.LINE_AA)
    return m


def _ellipse(m, c, ax, ay, ang=0.0, v=1.0):
    cv2.ellipse(m, tuple(np.round(c).astype(int)), (int(max(1, ax)), int(max(1, ay))), float(ang), 0, 360, float(v), -1, cv2.LINE_AA)
    return m


def soften(m, px):
    if px > 0.5:
        m = cv2.GaussianBlur(m, (0, 0), px)
    return np.clip(m, 0, 1)


def _sides(p):
    return p.get("sides", "AB")


def _eye_geo(f, e):
    E = EYE[e]
    up = np.array([f.P(i) for i in E["upper"]])
    lo = np.array([f.P(i) for i in E["lower"]])
    out, inn = f.P(E["outer"]), f.P(E["inner"])
    brow = np.array([f.P(i) for i in E["brow_lo"]]).mean(0)
    to_brow = brow - up.mean(0)
    return up, lo, out, inn, to_brow


# ---- base ------------------------------------------------------------------------------------------
def z_foundation(f, p):
    m = f.blank()
    cv2.fillConvexPoly(m, cv2.convexHull(np.round(f.lm[:468]).astype(np.int32)), 1.0)
    return m


def z_conceal_undereye(f, p):
    m = f.blank()
    for e in _sides(p):
        up, lo, out, inn, tb = _eye_geo(f, e)
        w = f.eye_w(e)
        tip = (lo.mean(0) - tb * p.get("depth", 1.1))
        _poly(m, [inn, lo[len(lo) // 2], out, tip])  # inverted triangle under the eye
    return m


def z_conceal_tzone(f, p):
    m = f.blank()
    w = f.eye_w("A")
    _line(m, [f.P(i) for i in FOREHEAD], w * 0.45)
    _line(m, [f.P(i) for i in NOSE_BRIDGE], w * 0.22)
    _ellipse(m, f.P(CHIN[1]), w * 0.35, w * 0.22)
    return m


# ---- sculpt ----------------------------------------------------------------------------------------
def z_contour_cheek(f, p):
    m = f.blank()
    for e in _sides(p):
        a, b = f.P(EYE[e]["hollow"][0]), f.P(EYE[e]["hollow"][1])
        w = f.eye_w(e)
        lift = np.array([0, -w * p.get("lift", 0.55)])  # zone map 11-09: reach 0.5 painted only the face edge
        _line(m, [a + (b - a) * 0.08 + lift, a + (b - a) * p.get("reach", 0.55) + lift * 0.8], w * p.get("width", 0.38))
    return m


def z_contour_temple(f, p):
    m = f.blank()
    for e in _sides(p):
        _line(m, [f.P(i) for i in EYE[e]["temple"]], f.eye_w(e) * p.get("width", 0.5))
    return m


def z_contour_jaw(f, p):
    m = f.blank()
    for e in _sides(p):
        _line(m, [f.P(i) for i in EYE[e]["jaw"]], f.eye_w(e) * p.get("width", 0.35))
    return m


def z_contour_nose(f, p):
    """Two thin lines down the sides of the nose and a shadow under the tip."""
    m = f.blank()
    w = f.eye_w("A")
    for e in _sides(p):
        _line(m, [f.P(i) for i in EYE[e]["nose_side"]], w * p.get("width", 0.08))
    _ellipse(m, f.P(UNDER_TIP[0]), w * 0.2, w * 0.06)
    return m


def z_bronzer(f, p):
    return np.maximum(z_contour_temple(f, {**p, "width": 0.7}), z_contour_cheek(f, {**p, "width": 0.6, "lift": 0.3}))


# ---- colour ----------------------------------------------------------------------------------------
def z_blush(f, p):
    """placement: apple | high (under the eye, toward the nose) | draped (cheekbone to temple) | lifted | nose"""
    m = f.blank()
    pl = p.get("placement", "apple")
    w = f.eye_w("A")
    for e in _sides(p):
        c = np.array([f.P(i) for i in EYE[e]["cheek"]]).mean(0)
        up, lo, out, inn, tb = _eye_geo(f, e)
        ew = f.eye_w(e)
        if pl == "apple":
            _ellipse(m, c + np.array([0, ew * 0.15]), ew * 0.5, ew * 0.38)
        elif pl == "high":
            d = (out - inn) / np.linalg.norm(out - inn)
            # audit 11-09 round 7: at 0.9 the blush ran into the lower lash line and read as a bruise; an artist
            # keeps high blush 3-4 mm (about 0.12 eye widths) below the lashes and toward the outer cheek
            cc = lo.mean(0) - tb * 1.5 + d * ew * 0.25
            _ellipse(m, cc, ew * 0.55, ew * 0.26, -8 if e == "A" else 8)
        elif pl == "draped":
            t = np.array([f.P(i) for i in EYE[e]["temple"]]).mean(0)
            _line(m, [c, t], ew * 0.55)
        elif pl == "lifted":
            t = np.array([f.P(i) for i in EYE[e]["temple"]]).mean(0)
            _line(m, [c + (t - c) * 0.1, c + (t - c) * 0.7], ew * 0.5)
    if pl in ("high", "nose") or p.get("nose", False):
        _line(m, [f.P(195), f.P(5), f.P(4)], w * 0.16, 0.8)
        # across the nose only, at mid-nose height: the old band from cheek point 100 through 197 ran right
        # under both eyes and was the red ring the audit and the layer check found (11-09)
        _line(m, [f.P(EYE["A"]["nose_side"][2]), f.P(5), f.P(EYE["B"]["nose_side"][2])], w * 0.12, 0.5)
    return m


def z_highlight(f, p):
    """spots: any of cheek, nose_bridge, nose_tip, cupid, browbone, inner_corner, chin"""
    m = f.blank()
    w = f.eye_w("A")
    spots = p.get("spots", ["cheek", "nose_bridge"])
    for e in _sides(p):
        up, lo, out, inn, tb = _eye_geo(f, e)
        ew = f.eye_w(e)
        if "cheek" in spots:  # small streak on the cheekbone apex, not the whole cheek
            top = np.array([f.P(i) for i in EYE[e]["cheek"][1:4]])
            c = top.mean(0) - tb * 0.25
            d = top[-1] - top[0]
            _ellipse(m, c, ew * 0.32, ew * 0.08, float(np.degrees(np.arctan2(d[1], d[0]))))
        if "browbone" in spots:
            b = np.array([f.P(i) for i in EYE[e]["brow_lo"]])
            _line(m, b[:3] - tb * 0.18, ew * 0.12)
        if "inner_corner" in spots:
            _ellipse(m, inn, ew * 0.09, ew * 0.07)
    if "nose_bridge" in spots:  # audit 11-09: a 0.07 line read as a hard stripe; wider and fading toward the tip
        _line(m, [f.P(i) for i in NOSE_BRIDGE[1:4]], w * 0.1)
    if "nose_tip" in spots:
        _ellipse(m, f.P(NOSE_TIP[0]), w * 0.06, w * 0.05)
    if "cupid" in spots:
        _ellipse(m, f.P(0) + np.array([0, -w * 0.07]), w * 0.1, w * 0.04)
    if "chin" in spots:
        _ellipse(m, f.P(CHIN[1]), w * 0.12, w * 0.08)
    return m


# ---- eyes ------------------------------------------------------------------------------------------
def z_lid(f, p):
    m = f.blank()
    for e in _sides(p):
        up, lo, out, inn, tb = _eye_geo(f, e)
        crease = up + tb * p.get("height", 0.6)
        _poly(m, list(up) + list(crease[::-1]))
    return m


def z_crease(f, p):
    m = f.blank()
    for e in _sides(p):
        up, lo, out, inn, tb = _eye_geo(f, e)
        _line(m, up[:-2] + tb * p.get("height", 0.5), f.eye_w(e) * p.get("width", 0.18))
    return m


def z_outer_v(f, p):
    m = f.blank()
    for e in _sides(p):
        up, lo, out, inn, tb = _eye_geo(f, e)
        ew = f.eye_w(e)
        seg = up[: len(up) // 3 + 1]
        d = (out - inn) / np.linalg.norm(out - inn)
        tip = out + d * ew * p.get("reach", 0.28) + tb * p.get("lift", 0.35)
        _poly(m, list(seg) + [tip] + list((seg + tb * 0.55)[::-1]))
    return m


def z_lower_lash(f, p):
    """part: outer (outer two thirds) | full"""
    m = f.blank()
    for e in _sides(p):
        up, lo, out, inn, tb = _eye_geo(f, e)
        ew = f.eye_w(e)
        seg = lo[: len(lo) * 2 // 3 + 1] if p.get("part", "outer") == "outer" else lo
        _line(m, seg - tb * 0.08, ew * p.get("width", 0.06))
    return m


def z_aegyo_sal(f, p):
    """The puffy band right under the lower lash line, the Douyin 'tear line'."""
    m = f.blank()
    for e in _sides(p):
        up, lo, out, inn, tb = _eye_geo(f, e)
        ew = f.eye_w(e)
        _line(m, lo[1:-1] - tb * 0.22, ew * p.get("width", 0.16))
    return m


def z_inner_corner(f, p):
    m = f.blank()
    for e in _sides(p):
        up, lo, out, inn, tb = _eye_geo(f, e)
        ew = f.eye_w(e)
        d = (inn - out) / np.linalg.norm(inn - out)
        _ellipse(m, inn + d * ew * 0.02, ew * p.get("size", 0.08), ew * p.get("size", 0.08) * 0.7)
    return m


def z_liner(f, p):
    """Upper liner thickest at the outer corner, with a wing. wing_angle deg (negative = down-turned),
    wing_len and outer_w in eye widths; smudge in eye widths."""
    m = f.blank()
    for e in _sides(p):
        up, lo, out, inn, tb = _eye_geo(f, e)
        ew = f.eye_w(e)
        n = len(up)
        for j in range(n - 1):
            t = j / (n - 1)
            th = ew * (p.get("outer_w", 0.06) * (1 - t) + p.get("inner_w", 0.015) * t)
            _line(m, [up[j], up[j + 1]], th)
        wl = p.get("wing_len", 0.25)
        if wl > 0:
            d = (out - inn) / np.linalg.norm(out - inn)
            upv = tb / np.linalg.norm(tb)
            a = np.deg2rad(p.get("wing_angle", 18))
            tip = out + (d * np.cos(a) + upv * np.sin(a)) * ew * wl
            _poly(m, [out - upv * ew * 0.01, out + upv * ew * p.get("outer_w", 0.06) * 0.9, tip])
        if p.get("lower", False):
            _line(m, lo[: len(lo) // 2 + 1], ew * 0.025)
    return m


# ---- lips ------------------------------------------------------------------------------------------
def _lip_outline(f, over):
    pts = f.lm[LIPS_OUT].copy()
    c = (f.P(61) + f.P(291)) / 2
    mw = np.linalg.norm(f.P(291) - f.P(61))
    for j in range(len(pts)):
        t = abs(pts[j, 0] - c[0]) / (mw / 2)
        d = pts[j] - c
        pts[j] = pts[j] + d / (np.linalg.norm(d) + 1e-6) * over * mw * max(0.0, 1 - t) ** 0.7
    return pts


def z_lips(f, p):
    """Whole lips including the gap between them; overline in mouth widths."""
    return _poly(f.blank(), _lip_outline(f, p.get("overline", 0.0)))


def z_lip_liner(f, p):
    m = f.blank()
    w = np.linalg.norm(f.P(291) - f.P(61))
    pts = _lip_outline(f, p.get("overline", 0.0))
    _line(m, list(pts) + [pts[0]], w * p.get("width", 0.035))
    return m


def z_lip_center(f, p):
    """Ombre core: a soft ellipse on the centre of both lips."""
    m = f.blank()
    mw = np.linalg.norm(f.P(291) - f.P(61))
    _ellipse(m, (f.P(14) + f.P(17)) / 2, mw * p.get("size", 0.22), mw * p.get("size", 0.22) * 0.45)
    _ellipse(m, (f.P(0) + f.P(13)) / 2, mw * p.get("size", 0.22) * 0.8, mw * p.get("size", 0.22) * 0.25, v=0.7)
    return m


def z_lip_gloss(f, p):
    """Gloss highlight band on the lower lip (roughness only by default)."""
    m = f.blank()
    mw = np.linalg.norm(f.P(291) - f.P(61))
    _ellipse(m, (f.P(14) + f.P(17)) / 2, mw * p.get("width", 0.2), mw * p.get("height", 0.05))
    return m


ZONES = {k[2:]: v for k, v in globals().items() if k.startswith("z_")}


def lash_keepout(f):
    """A soft band under each lower lash line where cheek products must not reach (blush, contour)."""
    m = f.blank()
    for e in "AB":
        up, lo, out, inn, tb = _eye_geo(f, e)
        _poly(m, list(up) + list(lo[::-1]))
        _line(m, lo - tb * 0.15, f.eye_w(e) * 0.3)
    return soften(m, 0.1 * f.eye_w("A"))


KEEPOUT = ("blush", "contour_cheek", "contour_temple", "bronzer")


def mask(face, zone, params, soft_ew=None):
    """Zone mask, softened by params['soft'] eye widths (default per zone family)."""
    m = ZONES[zone](face, params)
    s = params.get("soft", 0.08 if zone.startswith(("lip", "liner", "inner")) else 0.25)
    m = soften(m, s * face.eye_w("A"))
    if zone in KEEPOUT:
        m = m * (1 - lash_keepout(face))
    return m

"""Paint a makeup look (ordered layers) onto a MetaHuman head BaseColor and SRMF texture.

A layer: {"zone": name from zones.ZONES, "color": [R,G,B] sRGB 0..255, "opacity": 0..1,
          "blend": tint|multiply|screen|normal|color, "rough": roughness delta (negative = glossier),
          "glitter": 0..1 sparkle density, "params": {zone params, "soft": eye widths}}
Order follows a makeup artist: base, conceal, sculpt, powder, blush, highlight, eyes, liner, lips.
"""
import cv2
import numpy as np

from . import zones as Z


def _blend(img, color, a, mode, keep_l=0.6):
    c = np.array(color[::-1], np.float32) / 255.0  # RGB -> BGR
    a3 = a[..., None]
    if mode == "multiply":
        tgt = img * c
    elif mode == "screen":
        tgt = 1 - (1 - img) * (1 - c)
    elif mode == "tint":  # Lab tint: take the colour's a/b, mix L, keeps skin texture and lip lines
        lab = cv2.cvtColor((np.clip(img, 0, 1) * 255).astype(np.uint8), cv2.COLOR_BGR2LAB).astype(np.float32)
        tc = cv2.cvtColor(np.uint8([[np.array(color[::-1])]]), cv2.COLOR_BGR2LAB).astype(np.float32)[0, 0]
        lab[..., 1:] = tc[1:]
        lab[..., 0] = lab[..., 0] * keep_l + tc[0] * (1 - keep_l)
        tgt = cv2.cvtColor(np.clip(lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR).astype(np.float32) / 255.0
    elif mode == "color":
        lum = img.mean(2, keepdims=True)
        tgt = np.clip(c * (lum / max(float(c.mean()), 1e-3)), 0, 1)
    else:
        tgt = np.broadcast_to(c, img.shape)
    return img * (1 - a3) + tgt * a3


def _sparkle(shape, density, seed):
    rng = np.random.default_rng(seed)
    n = (rng.random(shape) < density * 0.02).astype(np.float32)
    return cv2.GaussianBlur(n, (0, 0), 0.8) * 4.0


# Render calibration, measured 2026-11-09 on Depesa (MH_DepesaKF, closed-mouth frame): the first in-engine pass
# moved blush by +3 a* (target about +10), lid colour by about 1 L, and under-eye brightness by +11 L (too much).
# Light and subsurface scattering in the render damp pigment, so colour layers get a gain per zone family.
RENDER_GAIN = {"blush": 2.6, "lid": 2.2, "crease": 2.0, "outer_v": 2.0, "lower_lash": 1.6, "contour_cheek": 1.8,
               "contour_temple": 1.8, "contour_jaw": 1.6, "contour_nose": 1.6, "bronzer": 1.8,
               "conceal_undereye": 0.45, "aegyo_sal": 0.5, "conceal_tzone": 0.6, "highlight": 0.8}


def paint(bc, srmf, look, face=None, seed=7, gain=None):
    """bc: HxWx3 uint8 BGR; srmf: HxWx3/4 uint8 or None (G = roughness). Returns (bc, srmf, masks)."""
    H, W = bc.shape[:2]
    face = face or Z.Face(W)
    img = bc.astype(np.float32) / 255.0
    rough = None if srmf is None else np.zeros((H, W), np.float32)  # roughness DELTA at BC size
    masks = []
    for i, L in enumerate(look["layers"]):
        if not L.get("on", True):
            continue
        m = Z.mask(face, L["zone"], L.get("params", {}))
        g = (RENDER_GAIN if gain is None else gain).get(L["zone"], 1.0)
        op = min(1.0, float(L.get("opacity", 0.5)) * g)
        if op > 0 and "color" in L:
            img = _blend(img, L["color"], m * op, L.get("blend", "normal"), L.get("keep_l", 0.6))
        if L.get("glitter", 0) > 0:
            sp = np.clip(_sparkle((H, W), L["glitter"], seed + i) * m, 0, 1)
            img = _blend(img, L.get("glitter_color", [255, 245, 250]), sp, "screen")
            if rough is not None:
                rough = rough - sp * 0.5
        if rough is not None and L.get("rough", 0) != 0:
            rough = rough + m * float(L["rough"])
        masks.append((L["zone"], m))
    out_bc = np.clip(img * 255, 0, 255).astype(np.uint8)
    out_srmf = None
    if srmf is not None:
        out_srmf = srmf.copy()
        d = cv2.resize(rough, (srmf.shape[1], srmf.shape[0]), interpolation=cv2.INTER_LINEAR)
        r0 = srmf[..., 1].astype(np.float32) / 255.0
        out_srmf[..., 1] = np.clip(np.clip(r0 + d, 0.05, 1) * 255, 0, 255).astype(np.uint8)
    return out_bc, out_srmf, masks


def face_crop(img, face, pad=0.9):
    """Crop to the face for previews."""
    pts = face.lm[:468]
    x0, y0 = pts.min(0)
    x1, y1 = pts.max(0)
    w = x1 - x0
    x0, x1 = int(max(0, x0 - w * 0.05)), int(min(img.shape[1], x1 + w * 0.05))
    y0, y1 = int(max(0, y0 - w * 0.05)), int(min(img.shape[0], y1 + w * 0.05))
    return img[y0:y1, x0:x1]

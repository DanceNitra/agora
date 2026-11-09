"""Paint a makeup look (ordered layers) onto a MetaHuman head BaseColor and SRMF texture.

A layer: {"zone": name from zones.ZONES, "color": [R,G,B] sRGB 0..255, "opacity": 0..1,
          "blend": tint|multiply|screen|normal|color, "rough": roughness delta (negative = glossier),
          "glitter": 0..1 sparkle density, "params": {zone params, "soft": eye widths}}
Order follows a makeup artist: base, conceal, sculpt, powder, blush, highlight, eyes, liner, lips.
"""
import cv2
import numpy as np

import os

from . import zones as Z
from . import viewmap as VM

_VIEW = {}


def view_face():
    """Landmarks detected on the frontal view of the MetaHuman face (exact UV via viewmap)."""
    if "vm" not in _VIEW:
        _VIEW["vm"] = VM.ViewMap()
        _VIEW["face"] = Z.Face(_VIEW["vm"].view_px, os.path.join(VM.DATA, "view_landmarks.json"), _VIEW["vm"].view_px)
    return _VIEW["vm"], _VIEW["face"]


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
    elif mode == "glow":  # highlight: lightness toward the colour, a tenth of its chroma (screen greyed
        lab = _lab(img)          # and cooled the bridge: audit 11-09, db -6.8)
        tc = _lab(np.array(color[::-1], np.float32).reshape(1, 1, 3) / 255.0)[0, 0]
        lab[..., 0] = tc[0]
        lab[..., 1:] = lab[..., 1:] + (tc[1:] - lab[..., 1:]) * 0.1
        tgt = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
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
# Second pass (audit 11-09): contour, nose contour and the nose highlight line were still invisible; under-eye
# brightness +6.4 L was still the strongest element.
RENDER_GAIN = {"blush": 2.6, "lid": 1.3, "crease": 2.0, "outer_v": 2.4, "lower_lash": 1.6, "contour_cheek": 3.0,
               "contour_temple": 3.0, "contour_jaw": 2.6, "contour_nose": 3.0, "bronzer": 2.6, "liner": 1.2,
               "conceal_undereye": 0.35, "aegyo_sal": 0.4, "conceal_tzone": 1.5, "highlight": 1.8}


def _protect(face, vm, W, keep_brows=None):
    """Lips, eyes and brows are not evened by the base (they keep their own colour). With keep_brows (UV mask of
    the approved brows) only those are protected, so old painted brow strokes around them get the base too."""
    parts = [Z.ZONES["lips"](face, {"overline": 0.01}), Z.ZONES["lid"](face, {"height": 0.35}), _eye_openings(face)]
    if keep_brows is None:
        parts.append(_brows(face))
    m = Z.soften(np.maximum.reduce(parts), 0.06 * face.eye_w("A"))
    m = vm.view_to_uv(m, W) if vm is not None else m
    if keep_brows is not None:
        k = cv2.resize((keep_brows > 127).astype(np.float32), (m.shape[1], m.shape[0]), interpolation=cv2.INTER_LINEAR)
        m = np.maximum(m, cv2.GaussianBlur(k, (0, 0), 2))
    return m


def _brows(face):
    m = face.blank()
    for e in "AB":
        E = Z.EYE[e]
        pts = [face.P(i) for i in E["brow_up"]] + [face.P(i) for i in E["brow_lo"]][::-1]
        Z._poly(m, pts)
    return cv2.dilate(m, np.ones((int(face.eye_w("A") * 0.12),) * 2, np.uint8))


def _eye_openings(face):
    m = face.blank()
    for e in "AB":
        E = Z.EYE[e]
        Z._poly(m, [face.P(i) for i in E["upper"]] + [face.P(i) for i in E["lower"]][::-1])
    return cv2.dilate(m, np.ones((int(face.eye_w("A") * 0.1),) * 2, np.uint8))


def brow_blockout(img, face, vm, keep_brows, W, H):
    """Conceal painted brow strokes the character no longer wears, the way an artist blocks out a brow before
    drawing a new one. The approved brows (keep_brows, a UV mask of the brow fill under the groom) stay
    untouched; every dark stroke in a band around the brows outside that mask is inpainted from the skin around
    it. Found 2026-11-09 by the owner on the four-view check: a second brow line above the outer end of Depesa's
    approved brows, left over from the preset texture, which the base had skipped by protecting the whole area."""
    ew = face.eye_w("A")
    band = cv2.dilate(_brows(face), np.ones((int(ew * 0.3),) * 2, np.uint8))
    band = band * (1 - cv2.dilate(_eye_openings(face) + Z.ZONES["lid"](face, {"height": 0.45}),
                                  np.ones((int(ew * 0.06),) * 2, np.uint8)).clip(0, 1))
    band = (vm.view_to_uv(band, W) > 0.3) if vm is not None else band > 0.3
    band = cv2.resize(band.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST) > 0
    keep = cv2.resize((keep_brows > 127).astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST)
    keep = cv2.dilate(keep, np.ones((5, 5), np.uint8)) > 0
    u8 = (np.clip(img, 0, 1) * 255).astype(np.uint8)
    L = cv2.cvtColor(u8, cv2.COLOR_BGR2LAB)[..., 0]
    bg = cv2.medianBlur(L, 31).astype(np.int16)
    dark = ((np.abs(L.astype(np.int16) - bg) > 4) & band & ~keep).astype(np.uint8)  # dark strokes and pale
    # patches left by an earlier brow removal (a lighter smudge beside the approved brow, check 11-09)
    # strokes only: connected dark areas of real size; pores and freckles stay. The stroke edge fades into the
    # skin, so each stroke is grown well past its threshold edge (a 3 px grow left a visible ghost line)
    n, lab_, st, _ = cv2.connectedComponentsWithStats(dark, connectivity=8)
    big = np.isin(lab_, [i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] >= max(60, W * W // 30000)])
    dark = cv2.dilate(big.astype(np.uint8), np.ones((max(9, W // 120),) * 2, np.uint8))
    dark[keep] = 0
    fixed = cv2.inpaint(u8, dark * 255, 15, cv2.INPAINT_TELEA).astype(np.float32) / 255.0
    a = cv2.GaussianBlur(dark.astype(np.float32), (0, 0), 3)
    a = np.maximum(a, dark.astype(np.float32))
    a[keep] = 0
    return img * (1 - a[..., None]) + fixed * a[..., None], dark


def base_target(bc, skin, sigma):
    """The base colour the whole skin is evened toward: the median of the low frequencies over the skin."""
    low = cv2.GaussianBlur(bc.astype(np.float32), (0, 0), sigma)
    return np.median(low[skin > 0], axis=0)


def _lab(bgr):
    return cv2.cvtColor(np.clip(bgr, 0, 1).astype(np.float32), cv2.COLOR_BGR2LAB)


def skin_likeness(img, sigma):
    """0..1: how much a texel is skin by its colour. Clothing baked into the MetaHuman texture (grey tank-top
    straps) has Lab chroma near 0, skin about 15-30; the base must not paint the straps (check 11-09)."""
    lab = _lab(cv2.GaussianBlur(img, (0, 0), sigma))
    c = np.hypot(lab[..., 1], lab[..., 2])
    w = np.clip((c - 7.0) / 6.0, 0, 1)
    return (w * w * (3 - 2 * w)).astype(np.float32)


def even_skin(img, skin_w, even, target, sigma, tone=None, lift=0.0, even_l=0.15):
    """Foundation: keep the high frequencies (pores, texture), pull the low frequencies toward one colour.
    Colour (Lab a, b) is evened by `even`; lightness only by `even_l`, because a foundation evens redness and
    blotches but must not erase the face's own light and shade (at even_l = even, the under-eye area rose
    +14.7 L against +4 L on the chin and the face went flat; 0.25 still gave +8.6). lift: L units added on every texel alike, so the
    face, ears, neck and body all move together. img float BGR 0..1; target and tone BGR 0..1."""
    low = cv2.GaussianBlur(img, (0, 0), sigma)
    tgt = target if tone is None else target * 0.5 + np.array(tone, np.float32) * 0.5
    lab = _lab(low)
    t = _lab(np.asarray(tgt, np.float32).reshape(1, 1, 3))[0, 0]
    k = np.array([even_l, even, even], np.float32)
    new = lab + (t[None, None, :] - lab) * k
    new[..., 0] += lift
    new_low = cv2.cvtColor(new.astype(np.float32), cv2.COLOR_LAB2BGR)
    return img + (new_low - low) * skin_w[..., None]


def paint(bc, srmf, look, face=None, seed=7, gain=None, body_bc=None, keep_brows=None):
    """bc: HxWx3 uint8 BGR; srmf: HxWx3/4 uint8 or None (G = roughness); keep_brows: UV mask (uint8) of the
    approved brows, everything brow-like outside it is concealed. Returns (bc, srmf, masks)."""
    H, W = bc.shape[:2]
    vm = None
    if face is None:  # default: zones drawn on the frontal view and carried to UV exactly
        vm, face = view_face()
    img = bc.astype(np.float32) / 255.0
    rough = None if srmf is None else np.zeros((H, W), np.float32)  # roughness DELTA at BC size
    masks = []
    body = None if body_bc is None else body_bc.astype(np.float32) / 255.0
    for i, L in enumerate(look["layers"]):
        if not L.get("on", True):
            continue
        if L["zone"] == "foundation" and L.get("params", {}).get("even", 0) > 0 and vm is not None:
            # METHOD.md rule 2: the base covers ALL skin (face, ears, neck to the collarbones on the face texture,
            # and the body texture) with one shared colour transform, so nothing shows an edge or a tone change.
            prm = L["params"]
            sig = W * 0.012
            if keep_brows is not None:
                img, _ = brow_blockout(img, face, vm, keep_brows, W, H)
            skin_mask = cv2.resize(vm.uv_skin.astype(np.float32), (W, H), interpolation=cv2.INTER_NEAREST)
            skin_mask = cv2.GaussianBlur(skin_mask, (0, 0), 2) * (1 - _protect(face, vm, W, keep_brows)) * skin_likeness(img, 3)
            tgt = base_target(img, skin_mask > 0.5, sig)
            tone = None if "color" not in L else np.array(L["color"][::-1], np.float32) / 255.0
            lift = float(prm.get("lift", 0.0))
            img = np.clip(even_skin(img, skin_mask, float(prm["even"]), tgt, sig, tone, lift), 0, 1)
            if body is not None:
                bw = (body.max(2) > 0.02).astype(np.float32) * skin_likeness(body, 3)
                body = np.clip(even_skin(body, cv2.GaussianBlur(bw, (0, 0), 2), float(prm["even"]), tgt,
                                         body.shape[1] * 0.012, tone, lift), 0, 1)
            if "rough" in L:
                rough = rough + skin_mask * float(L["rough"]) if rough is not None else rough
            continue
        m = Z.mask(face, L["zone"], L.get("params", {}))
        if vm is not None:
            m = vm.view_to_uv(m, W)
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
    if body is not None:
        masks.append(("body", np.clip(body * 255, 0, 255).astype(np.uint8)))
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


def preview_view(base_view, look, gain=None, seed=7):
    """Paint a look directly on the frontal view (no UV round trip): the fast path for comparing many looks."""
    vm, face = view_face()
    img = base_view.astype(np.float32) / 255.0
    valid = np.isfinite(vm.view_uv[..., 0]).astype(np.float32)
    for i, L in enumerate(look["layers"]):
        if not L.get("on", True) or "color" not in L:
            continue
        key = (L["zone"], repr(sorted(L.get("params", {}).items())))
        m = _MASKS.get(key)
        if m is None:
            m = _MASKS[key] = Z.mask(face, L["zone"], L.get("params", {})) * valid
        g = (RENDER_GAIN if gain is None else gain).get(L["zone"], 1.0)
        op = min(1.0, float(L.get("opacity", 0.5)) * g)
        if op > 0:
            img = _blend(img, L["color"], m * op, L.get("blend", "normal"), L.get("keep_l", 0.6))
    return np.clip(img * 255, 0, 255).astype(np.uint8)


_MASKS = {}

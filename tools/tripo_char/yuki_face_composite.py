"""Composite Yuki's concept-painted face (baked from the Tripo head onto MetaHuman UVs) into the MetaHuman's own baked
base colour, and bring the rest of the head and the body to the same skin tone.

    python yuki_face_composite.py <face_bake_dir> <face_tex_dir>

Inputs: <face_bake_dir>/tripo_on_mh.png (RGBA), height_mask.png; <face_tex_dir>/base_face_BC.png, base_body_BC.png.
Weight = bake alpha x height mask, feathered, with the dark garment texels of the Tripo bust removed. The skin gain is
the per-channel ratio of medians, Tripo skin over MetaHuman skin, taken where the weight is full and the texel is not
make-up (bright, low saturation spread), computed in linear light. Writes yuki_face_BC.png, yuki_body_BC.png and
composite.json with the measured gain.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

bake, texd = Path(sys.argv[1]), Path(sys.argv[2])
Image.MAX_IMAGE_PIXELS = None
base = Image.open(texd / "base_face_BC.png").convert("RGB")
W, H = base.size
tri = Image.open(bake / "tripo_on_mh.png").convert("RGBA").resize((W, H), Image.LANCZOS)
hm = Image.open(bake / "height_mask.png").convert("L").resize((W, H), Image.BILINEAR)
B = np.asarray(base, dtype=np.float32) / 255
T = np.asarray(tri, dtype=np.float32) / 255
w = T[..., 3] * (np.asarray(hm, dtype=np.float32) / 255)
lum = T[..., :3].mean(2)
w = np.where(lum < 0.25, np.minimum(w, np.clip((lum - 0.05) / 0.2, 0, 1)) if False else w, w)
# feather the edge of the weight so the seam on the neck has no line
wi = Image.fromarray((w * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(W / 180))
w = np.minimum(w, np.asarray(wi, dtype=np.float32) / 255)


def lin(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055)


Tl, Bl = lin(T[..., :3]), lin(B)
sat = T[..., :3].max(2) - T[..., :3].min(2)
skin = (w > 0.98) & (lum > 0.65) & (sat < 0.35) & (T[..., 0] > T[..., 2])
gain = np.median(Tl[skin], 0) / np.median(Bl[skin], 0)
out = srgb(w[..., None] * Tl + (1 - w[..., None]) * np.clip(Bl * gain, 0, 1))
Image.fromarray((out * 255 + 0.5).astype(np.uint8)).save(texd / "yuki_face_BC.png")
body = Image.open(texd / "base_body_BC.png").convert("RGB")
Bo = lin(np.asarray(body, dtype=np.float32) / 255)
Image.fromarray((srgb(np.clip(Bo * gain, 0, 1)) * 255 + 0.5).astype(np.uint8)).save(texd / "yuki_body_BC.png")
rep = {"size": [W, H], "skin_texels": int(skin.sum()), "gain_rgb_linear": [round(float(g), 3) for g in gain],
       "tripo_skin_srgb": [round(float(x), 3) for x in srgb(np.median(Tl[skin], 0))],
       "mh_skin_srgb": [round(float(x), 3) for x in srgb(np.median(Bl[skin], 0))], "weight_full_share": round(float((w > 0.98).mean()), 3)}
(texd / "composite.json").write_text(json.dumps(rep, indent=1))
print("COMPOSITE", json.dumps(rep))
prev = [Image.open(texd / n).convert("RGB").resize((700, 700)) for n in ("base_face_BC.png", "yuki_face_BC.png")]
s = Image.new("RGB", (1400, 700))
s.paste(prev[0], (0, 0)); s.paste(prev[1], (700, 0))
s.save(texd / "before_after.jpg", quality=90)

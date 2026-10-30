"""Overlay the robot silhouette of a reference view and a render, aligned by bounding box.

Usage: python silhouette_overlay.py <reference.png> <render.png> <out.png>
Prints IoU and the bounding-box ratios. Red = only in the reference, cyan = only in the render.
Needs numpy and Pillow (ComfyUI venv).
"""
import sys

import numpy as np
from PIL import Image


def mask(path):
    """Robot silhouette: the alpha channel when the render has one, else a colour mask with holes filled."""
    img = Image.open(path)
    if img.mode == "RGBA":
        al = np.asarray(img)[..., 3]
        if al.min() < 250:
            return al > 127
    a = np.asarray(img.convert("RGB")).astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    orange = (r > 150) & (r - b > 110) & (g < 150)
    dark = (r < 80) & (g < 80) & (b < 80)
    metal = (abs(r - g) < 18) & (abs(g - b) < 18) & (r < 170) & (r > 60)
    m = orange | dark | metal
    from PIL import ImageFilter
    m = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.MinFilter(7))) > 127
    return m


def crop(m):
    ys, xs = np.nonzero(m)
    return m[ys.min():ys.max() + 1, xs.min():xs.max() + 1], (xs.max() - xs.min() + 1, ys.max() - ys.min() + 1)


ref, (rw, rh) = crop(mask(sys.argv[1]))
ren, (nw, nh) = crop(mask(sys.argv[2]))
H = 800
W = int(H * rw / rh)
R = np.asarray(Image.fromarray(ref.astype(np.uint8) * 255).resize((W, H))) > 127
N = np.asarray(Image.fromarray(ren.astype(np.uint8) * 255).resize((W, H))) > 127
out = np.zeros((H, W, 3), np.uint8)
out[R & N] = (235, 235, 235)
out[R & ~N] = (230, 40, 40)
out[~R & N] = (40, 210, 230)
Image.fromarray(out).save(sys.argv[3])
iou = (R & N).sum() / max((R | N).sum(), 1)
print(f"IoU {iou:.3f}  ref aspect {rw / rh:.3f}  render aspect {nw / nh:.3f}  ref-only {(R & ~N).sum() / R.sum():.1%}  render-only {(~R & N).sum() / N.sum():.1%}")

"""Mascara clumps on the MetaHuman lash card coverage atlas: each hair group is squeezed toward its centre with
growing strength along the hair (root -> tip), and thickened, so neighbouring hairs merge into spikes.
Usage: clump_lashes.py <in.png> <out.png> <squeeze 0..1> <thicken px> <root: top|bottom>"""
import sys
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

src, dst, sq, th, root = sys.argv[1], sys.argv[2], float(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
a = np.asarray(Image.open(src).convert("L")).astype(np.float32) / 255.0
grp = ndimage.binary_dilation(a > 0.08, structure=np.ones((9, 25)))  # join hairs of one card into a group
lab, n = ndimage.label(grp)
out = np.zeros_like(a)
for i, sl in enumerate(ndimage.find_objects(lab), 1):
    ys, xs = sl
    m = (lab[sl] == i)
    cell = a[sl] * m
    h, w = cell.shape
    cols = np.nonzero(cell.sum(0) > 0)[0]
    if len(cols) == 0:
        continue
    cx = (cell.sum(0) * np.arange(w)).sum() / cell.sum()
    res = np.zeros_like(cell)
    for y in range(h):
        t = y / max(1, h - 1)
        if root == "bottom":
            t = 1 - t
        k = 1 - sq * t ** 0.8  # squeeze grows toward the tip
        row = cell[y]
        xs_new = cx + (np.arange(w) - cx) * k
        np.maximum.at(res[y], np.clip(np.round(xs_new).astype(int), 0, w - 1), row)
    out[sl] = np.maximum(out[sl], res)
img = Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8))
if th > 0:
    img = img.filter(ImageFilter.MaxFilter(2 * th + 1))
img = img.filter(ImageFilter.GaussianBlur(0.6))
img.save(dst)
print("groups", n, "->", dst)

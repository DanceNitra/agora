"""lutlab: measure a colour grade from a before/after pair and rebuild it as our own .cube.

Two models, on purpose:
  lattice  A free 3D lattice (17^3) fitted by smoothed least squares. It is the
           MEASURING INSTRUMENT: it fits almost anything, explains nothing, and is
           never shipped.
  param    Our own grade engine, 35 named parameters a colourist would recognise
           (CDL slope/offset/power, a monotone luminance curve, split toning,
           six hue sectors, global saturation). It is the REBUILD: every LUT we
           ship is generated from these parameters, so it is ours.

If param scores close to lattice on held-out pixels, the parameters explain the
look. If not, the gap is reported, never hidden.

Colour space: display-referred sRGB / Rec.709 gamma in, same out (the vendor's
FAQ says their LUTs expect Rec.709 footage).
"""
from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass

import numpy as np
from scipy import sparse
from scipy.optimize import least_squares
from scipy.sparse.linalg import spsolve

# ---------------------------------------------------------------- colour math
_M = np.array([[0.4124564, 0.3575761, 0.1804375],
               [0.2126729, 0.7151522, 0.0721750],
               [0.0193339, 0.1191920, 0.9503041]])
_MI = np.linalg.inv(_M)
_WP = np.array([0.95047, 1.0, 1.08883])


def srgb_to_lin(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def rgb_to_lab(rgb):
    xyz = srgb_to_lin(rgb) @ _M.T / _WP
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    return np.stack([116 * f[:, 1] - 16, 500 * (f[:, 0] - f[:, 1]), 200 * (f[:, 1] - f[:, 2])], 1)


def lab_to_rgb(lab):
    fy = (lab[:, 0] + 16) / 116
    fx = fy + lab[:, 1] / 500
    fz = fy - lab[:, 2] / 200
    f = np.stack([fx, fy, fz], 1)
    xyz = np.where(f ** 3 > 216 / 24389, f ** 3, (116 * f - 16) / (24389 / 27)) * _WP
    return lin_to_srgb(xyz @ _MI.T)


def delta_e2000(lab1, lab2):
    from skimage.color import deltaE_ciede2000
    return deltaE_ciede2000(lab1, lab2)


# ---------------------------------------------------------------- lattice (instrument)
def _trilinear(rgb, n):
    g = np.clip(rgb, 0, 1) * (n - 1)
    i0 = np.minimum(np.floor(g).astype(int), n - 2)
    t = g - i0
    rows, cols, vals = [], [], []
    idx = np.arange(len(rgb))
    for dr in (0, 1):
        for dg in (0, 1):
            for db in (0, 1):
                w = ((t[:, 0] if dr else 1 - t[:, 0]) * (t[:, 1] if dg else 1 - t[:, 1])
                     * (t[:, 2] if db else 1 - t[:, 2]))
                c = ((i0[:, 0] + dr) * n + (i0[:, 1] + dg)) * n + (i0[:, 2] + db)
                rows.append(idx); cols.append(c); vals.append(w)
    return sparse.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))),
                             shape=(len(rgb), n ** 3))


def _laplacian(n):
    ops = []
    N = n ** 3
    ids = np.arange(N).reshape(n, n, n)
    for ax in range(3):
        a = np.moveaxis(ids, ax, 0)
        lo, mid, hi = a[:-2].ravel(), a[1:-1].ravel(), a[2:].ravel()
        m = len(mid)
        r = np.repeat(np.arange(m), 3)
        c = np.stack([lo, mid, hi], 1).ravel()
        v = np.tile([1.0, -2.0, 1.0], m)
        ops.append(sparse.csr_matrix((v, (r, c)), shape=(m, N)))
    return sparse.vstack(ops)


def fit_lattice(src, dst, n=17, lam=0.3):
    A = _trilinear(src, n)
    L = _laplacian(n)
    lhs = (A.T @ A + lam * len(src) / n ** 3 * (L.T @ L)).tocsc()
    out = np.stack([spsolve(lhs, A.T @ dst[:, k]) for k in range(3)], 1)
    return out.reshape(n, n, n, 3)


def apply_lattice(lut, rgb):
    n = lut.shape[0]
    return np.clip(_trilinear(rgb, n) @ lut.reshape(-1, 3), 0, 1)


# ---------------------------------------------------------------- param (rebuild)
NAMES = (["slope_r", "slope_g", "slope_b", "offset_r", "offset_g", "offset_b",
          "power_r", "power_g", "power_b", "black_lift"]
         + [f"curve_{i}" for i in range(8)]
         + ["shadow_a", "shadow_b", "high_a", "high_b"]
         + [f"sat_{h}" for h in ("red", "yellow", "green", "cyan", "blue", "magenta")]
         + [f"hue_{h}" for h in ("red", "yellow", "green", "cyan", "blue", "magenta")]
         + ["saturation"])
P = len(NAMES)
_SECTOR_CENTRES = np.deg2rad([30, 90, 150, 210, 270, 330])  # in Lab hue angle, roughly R Y G C B M
_KNOTS = np.linspace(0, 100, 9)


def _softplus(x):
    return np.log1p(np.exp(-np.abs(x))) + np.maximum(x, 0)


def _inv_softplus(y):
    return y + np.log(-np.expm1(-y))


def identity_params():
    p = np.zeros(P)
    p[0:3] = 1.0
    p[6:9] = 1.0
    p[10:18] = _inv_softplus(12.5)
    return p


def apply_param(p, rgb):
    p = np.asarray(p, float)
    c = np.clip(rgb * p[0:3] + p[3:6], 0, 1) ** np.maximum(p[6:9], 0.05)
    lab = rgb_to_lab(c)
    L, a, b = lab[:, 0], lab[:, 1], lab[:, 2]
    outs = p[9] + np.concatenate([[0], np.cumsum(_softplus(p[10:18]))])
    L2 = np.interp(L, _KNOTS, outs)
    t = np.clip(L / 100, 0, 1)
    ws = (1 - t) ** 2
    wh = t ** 2
    a = a + p[18] * ws + p[20] * wh
    b = b + p[19] * ws + p[21] * wh
    ch = np.hypot(a, b)
    h = np.arctan2(b, a)
    d = (h[:, None] - _SECTOR_CENTRES[None, :] + np.pi) % (2 * np.pi) - np.pi
    w = 0.5 * (1 + np.cos(np.clip(3 * d, -np.pi, np.pi)))
    sat = np.exp(w @ p[22:28] + p[34])
    h2 = h + w @ np.deg2rad(p[28:34]) * np.clip(ch / 20, 0, 1)
    ch2 = ch * sat
    return np.stack([L2, ch2 * np.cos(h2), ch2 * np.sin(h2)], 1)  # Lab


def fit_param(src, dst_lab, p0=None, reg=0.02):
    p0 = identity_params() if p0 is None else p0
    prior = identity_params()
    scale = np.ones(P)
    scale[28:34] = 30.0
    scale[18:22] = 10.0

    def resid(p):
        r = (apply_param(p, src) - dst_lab).ravel() / math.sqrt(len(src))
        return np.concatenate([r, reg * (p - prior) / scale])

    res = least_squares(resid, p0, method="trf", x_scale="jac", max_nfev=400)
    return res.x


# ---------------------------------------------------------------- rules readout
def describe(p):
    """Turn parameters into the sentences a colourist would write."""
    p = np.asarray(p)
    grey = np.linspace(0, 1, 11)[:, None].repeat(3, 1)
    lab = apply_param(p, grey)
    out = {
        "black_L": round(float(lab[0, 0]), 1),
        "white_L": round(float(lab[-1, 0]), 1),
        "mid_L_at_50": round(float(np.interp(50, rgb_to_lab(grey)[:, 0], lab[:, 0])), 1),
        "shadow_tint_ab": [round(float(x), 1) for x in lab[1, 1:]],
        "mid_tint_ab": [round(float(x), 1) for x in lab[5, 1:]],
        "high_tint_ab": [round(float(x), 1) for x in lab[9, 1:]],
        "saturation_x": round(float(math.exp(p[34])), 2),
        "sector_sat_x": {n[4:]: round(float(math.exp(p[34] + v)), 2) for n, v in zip(NAMES[22:28], p[22:28])},
        "sector_hue_deg": {n[4:]: round(float(v), 1) for n, v in zip(NAMES[28:34], p[28:34])},
    }
    gin = rgb_to_lab(grey)[:, 0]
    slope = np.gradient(lab[:, 0], gin)
    out["contrast_mid"] = round(float(slope[5]), 2)
    return out


def tint_words(ab):
    a, b = ab
    if math.hypot(a, b) < 1.5:
        return "neutral"
    ang = math.degrees(math.atan2(b, a)) % 360
    names = [(0, "magenta-red"), (40, "red-orange"), (70, "orange"), (95, "yellow"),
             (130, "olive-green"), (165, "green"), (200, "teal"), (235, "cyan-blue"),
             (270, "blue"), (310, "violet"), (345, "magenta-red")]
    return min(names, key=lambda kv: min(abs(ang - kv[0]), 360 - abs(ang - kv[0])))[1]


# ---------------------------------------------------------------- .cube
def write_cube(path, fn_rgb, title, size=33):
    g = np.linspace(0, 1, size)
    b, gg, r = np.meshgrid(g, g, g, indexing="ij")  # red varies fastest
    rgb = np.stack([r.ravel(), gg.ravel(), b.ravel()], 1)
    out = np.clip(fn_rgb(rgb), 0, 1)
    with open(path, "w", newline="\n") as f:
        f.write(f'TITLE "{title}"\nLUT_3D_SIZE {size}\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n')
        for row in out:
            f.write(f"{row[0]:.6f} {row[1]:.6f} {row[2]:.6f}\n")


def read_cube(path):
    size, rows = None, []
    for line in open(path):
        s = line.split()
        if not s or s[0].startswith("#"):
            continue
        if s[0] == "LUT_3D_SIZE":
            size = int(s[1])
        elif s[0][0].isdigit() or s[0][0] in "-.":
            rows.append([float(x) for x in s[:3]])
    lut = np.array(rows).reshape(size, size, size, 3)  # [b][g][r]
    return np.transpose(lut, (2, 1, 0, 3))  # -> [r][g][b]


def param_to_rgb(p):
    return lambda rgb: lab_to_rgb(apply_param(p, rgb))


if __name__ == "__main__":
    print(json.dumps({"params": P, "names": NAMES}, indent=1))
    sys.exit(0)

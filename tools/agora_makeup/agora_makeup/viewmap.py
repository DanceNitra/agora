"""Exact mapping between a frontal view of the MetaHuman face and its UV texture.

Built from the face mesh exported by Unreal (data/face_mesh.bin: positions, triangles, per-corner UV0 with
the seams kept).
  view_uv  : for every pixel of a frontal orthographic view, the UV it shows (or nan).
  uv_view  : for every texel, the view pixel it lands on, ONLY where that surface point is the one visible
             from the front (depth test); everywhere else nan.
Zones are drawn on the frontal view, where the face is not distorted, and carried to the texture.
Texels the front view cannot see (sides of the face, under the chin, inside folds) are filled smoothly
from their neighbours (push-pull), so every layer runs out to nothing instead of stopping at an edge.

Defects this version removes, all seen in Unreal renders on 2026-11-09:
- per-vertex UVs stretched seam triangles across the texture: speckles on the forehead and cheeks;
- no depth test: the neck under the chin took the chin's makeup;
- untouched texels beside painted ones: hard edges where a makeup artist blends to nothing.
"""
import os
import struct

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")


def load_mesh(path=os.path.join(DATA, "face_mesh.bin")):
    b = open(path, "rb").read()
    nv, nt, nu = struct.unpack_from("<iii", b, 0)
    o = 12
    P = np.frombuffer(b, "<f4", 3 * nv, o).reshape(nv, 3); o += 12 * nv
    T = np.frombuffer(b, "<i4", 3 * nt, o).reshape(nt, 3); o += 12 * nt
    if nu < 0:  # per-corner UVs
        C = np.frombuffer(b, "<f4", 6 * nt, o).reshape(nt, 3, 2)
    else:
        U = np.frombuffer(b, "<f4", 2 * nu, o).reshape(nu, 2)
        C = U[T]
    return P.astype(np.float64), T, C.astype(np.float64)


def _raster(tri_xy, attrs, depth, W, H, zbuf=None):
    """Rasterize triangles (pixel coords) with per-corner attributes; larger depth wins."""
    A = attrs.shape[2]
    out = np.full((H, W, A), np.nan, np.float32)
    zb = np.full((H, W), -np.inf, np.float32) if zbuf is None else zbuf
    for t in range(len(tri_xy)):
        p = tri_xy[t]
        x0, y0 = np.floor(p.min(0)).astype(int)
        x1, y1 = np.ceil(p.max(0)).astype(int)
        x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, W - 1), min(y1, H - 1)
        if x1 < x0 or y1 < y0:
            continue
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        (ax, ay), (bx, by), (cx, cy) = p
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-12:
            continue
        w0 = ((by - cy) * (xs - cx) + (cx - bx) * (ys - cy)) / den
        w1 = ((cy - ay) * (xs - cx) + (ax - cx) * (ys - cy)) / den
        w2 = 1 - w0 - w1
        ins = (w0 >= -1e-3) & (w1 >= -1e-3) & (w2 >= -1e-3)
        if not ins.any():
            continue
        z = w0 * depth[t, 0] + w1 * depth[t, 1] + w2 * depth[t, 2]
        sub = zb[y0:y1 + 1, x0:x1 + 1]
        win = ins & (z > sub)
        if not win.any():
            continue
        sub[win] = z[win]
        a = attrs[t]
        val = w0[..., None] * a[0] + w1[..., None] * a[1] + w2[..., None] * a[2]
        out[y0:y1 + 1, x0:x1 + 1][win] = val[win]
    return out, zb


def push_pull(img, valid, levels=9):
    """Fill invalid pixels from valid neighbours across scales (smooth, no edges)."""
    if valid.all():
        return img
    stack = []
    v = valid.astype(np.float32)
    x = np.where(valid[..., None] if img.ndim == 3 else valid, img, 0).astype(np.float32)
    for _ in range(levels):
        stack.append((x, v))
        if min(x.shape[:2]) < 8:
            break
        v2 = cv2.pyrDown(v)
        x2 = cv2.pyrDown(x * (v[..., None] if x.ndim == 3 else v))
        x = x2 / np.maximum(v2[..., None] if x2.ndim == 3 else v2, 1e-6)
        v = np.minimum(v2 * 4, 1.0)
    for x_hi, v_hi in reversed(stack[:-1]):
        up = cv2.resize(x, (x_hi.shape[1], x_hi.shape[0]), interpolation=cv2.INTER_LINEAR)
        w = v_hi[..., None] if x_hi.ndim == 3 else v_hi
        x = x_hi * w + up * (1 - w)
    return x


def build(view_px=1024, uv_px=1024, out=os.path.join(DATA, "viewmap.npz")):
    P, T, C = load_mesh()
    fwd = P[:, 1]                                       # Unreal face component: X lateral, Y forward, Z up
    bad_uv = (C < 0).any((1, 2)) | (C > 1).any((1, 2))
    Tf, Cf = T[~bad_uv], C[~bad_uv]
    front = fwd > np.percentile(fwd, 30)
    fz = front & (P[:, 2] > np.percentile(P[front][:, 2], 1))
    lo, hi = P[fz][:, [0, 2]].min(0), P[fz][:, [0, 2]].max(0)
    s = (view_px * 0.94) / (hi - lo).max()
    vx = (P[:, 0] - (lo[0] + hi[0]) / 2) * s + view_px / 2
    vy = view_px / 2 - (P[:, 2] - (lo[1] + hi[1]) / 2) * s
    V = np.stack([vx, vy], 1)
    # MetaHuman triangles wind clockwise seen from outside: the cross product points INTO the head
    # (measured: 99 % of the nose-tip triangles had a negative forward normal), so it is negated
    n = -np.cross(P[Tf][:, 1] - P[Tf][:, 0], P[Tf][:, 2] - P[Tf][:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    facing = n[:, 1] > 0.02                              # triangles that face the front camera
    L = np.array([0.25, 0.85, 0.45]) / np.linalg.norm([0.25, 0.85, 0.45])
    shade = np.clip(n @ L, 0.15, 1.0)
    attrs = np.concatenate([Cf, np.repeat(shade[:, None, None], 3, 1)], 2)
    # view: nearest front-facing surface per pixel
    view, zbuf = _raster(V[Tf][facing], attrs[facing], fwd[Tf][facing], view_px, view_px)
    # uv: view position + the texel's own depth; keep it only where it IS the visible surface
    a2 = np.concatenate([V[Tf].astype(np.float32), fwd[Tf][..., None].astype(np.float32)], 2)
    uvr, _ = _raster(Cf * uv_px, a2, np.zeros((len(Tf), 3)), uv_px, uv_px)
    vxs, vys, dep = uvr[..., 0], uvr[..., 1], uvr[..., 2]
    ok = np.isfinite(vxs)
    ix = np.clip(np.nan_to_num(vxs).astype(int), 0, view_px - 1)
    iy = np.clip(np.nan_to_num(vys).astype(int), 0, view_px - 1)
    vis = ok & np.isfinite(zbuf[iy, ix]) & (dep >= zbuf[iy, ix] - 0.15)   # 1.5 mm tolerance
    # per-texel 3D position and normal (vertex normals, area weighted), for the projection that every texel
    # takes from its own place in 3D (METHOD.md rule 1)
    vn = np.zeros_like(P)
    fn = -np.cross(P[T][:, 1] - P[T][:, 0], P[T][:, 2] - P[T][:, 0])
    for k in range(3):
        np.add.at(vn, T[:, k], fn)
    vn /= np.linalg.norm(vn, axis=1, keepdims=True) + 1e-12
    a3 = np.concatenate([V[Tf].astype(np.float32), vn[Tf].astype(np.float32)], 2)
    tex, _ = _raster(Cf * uv_px, a3, np.zeros((len(Tf), 3)), uv_px, uv_px)
    skin = np.isfinite(tex[..., 0]).astype(np.uint8)
    # soft visibility from the front: 1 where the texel is the surface the front view sees, fading to 0 for
    # surfaces 2 mm or more behind it (back of the head, inside of folds); the check found back-of-head
    # triangles with forward normals taking eye makeup
    zb = np.where(np.isfinite(zbuf), zbuf, np.inf)[iy, ix]
    behind = np.where(ok, zb - dep, np.inf)
    vis_w = np.clip(1 - (behind - 0.05) / 0.2, 0, 1).astype(np.float32)
    vis_w[~ok] = np.nan
    np.savez_compressed(out, view_uv=view[..., :2], view_shade=view[..., 2], uv_view=tex[..., :2],
                        uv_normal=tex[..., 2:5], uv_vis=vis_w, uv_skin=skin, view_px=view_px, uv_px=uv_px)
    return {"view_px": view_px, "uv_px": uv_px, "uv_visible": float(vis.mean()), "uv_surface": float(ok.mean()),
            "dropped_bad_uv_tris": int(bad_uv.sum())}


class ViewMap:
    def __init__(self, path=os.path.join(DATA, "viewmap.npz")):
        d = np.load(path)
        self.view_uv, self.shade, self.uv_view = d["view_uv"], d["view_shade"], d["uv_view"]
        self.uv_skin = d["uv_skin"]
        self.uv_normal = d["uv_normal"]
        self.uv_vis = d["uv_vis"]
        self.view_px, self.uv_px = int(d["view_px"]), int(d["uv_px"])
        self._cache = {}

    def frontal(self, tex_bgr):
        """Sample a UV texture into the frontal view, lit by the stored shading (landmarks, previews, checks)."""
        Ht, Wt = tex_bgr.shape[:2]
        uv = np.nan_to_num(self.view_uv, nan=-1.0)
        img = cv2.remap(tex_bgr, (uv[..., 0] * Wt).astype(np.float32), (uv[..., 1] * Ht).astype(np.float32),
                        cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        sh = np.nan_to_num(self.shade, nan=0.0)[..., None]
        return np.clip(img.astype(np.float32) * (0.75 + 0.6 * sh), 0, 255).astype(np.uint8)

    def _maps(self, tex_px):
        if tex_px not in self._cache:
            r = lambda a, i=cv2.INTER_LINEAR: a if self.uv_px == tex_px else cv2.resize(a, (tex_px, tex_px), interpolation=i)
            skin = r(self.uv_skin, cv2.INTER_NEAREST).astype(bool)
            m = push_pull(np.nan_to_num(self.uv_view), np.isfinite(self.uv_view[..., 0]))   # close raster gaps only
            ny = push_pull(np.nan_to_num(self.uv_normal[..., 1]), np.isfinite(self.uv_normal[..., 1]))
            # facing weight: full on surfaces that face the front, fading to 0 at grazing (sides, under chin)
            w = np.clip((ny - 0.08) / (0.45 - 0.08), 0, 1)
            w = w * w * (3 - 2 * w)
            vis = push_pull(np.nan_to_num(self.uv_vis), np.isfinite(self.uv_vis))
            w = w * cv2.GaussianBlur(vis, (0, 0), 1.5)
            self._cache[tex_px] = (r(m).astype(np.float32), r(w).astype(np.float32), skin)
        return self._cache[tex_px]

    def view_to_uv(self, mask_view, tex_px):
        """Every texel takes the zone value at its own 3D position seen from the front, weighted by how much it
        faces the front. No holes, no copying from the chin onto the neck, no hard edges."""
        m, w, skin = self._maps(tex_px)
        out = cv2.remap(mask_view.astype(np.float32), m[..., 0], m[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        return out * w * skin

"""Offline check of a painted face texture on the 3D face mesh, before any Unreal render (METHOD.md rule 4).

  python check.py <base_BC.png> <look_id> <out.png>

Renders the face mesh with the texture (flat, with a simple shading term) from the front, 40 degrees to
each side, and from below (neck and under-chin), before and after the look, in one sheet. Looks for holes,
speckles, hard edges and neck spill are made by eye on this sheet and by the edge measure printed:
the largest jump in the painted-minus-base difference between neighbouring texels on the skin.
"""
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cli  # noqa: E402
from agora_makeup import paint, viewmap  # noqa: E402

P, T, C = viewmap.load_mesh()


def render(tex, yaw, pitch, px=520):
    a, b = np.radians(yaw), np.radians(pitch)
    Ry = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    Rx = np.array([[1, 0, 0], [0, np.cos(b), -np.sin(b)], [0, np.sin(b), np.cos(b)]])
    c = P.mean(0)
    Q = (P - c) @ (Rx @ Ry).T
    fz = Q[:, 2] > np.percentile(Q[:, 2], 2)
    lo, hi = Q[fz][:, [0, 2]].min(0), Q[fz][:, [0, 2]].max(0)
    s = px * 0.94 / (hi - lo).max()
    V = np.stack([(Q[:, 0] - (lo[0] + hi[0]) / 2) * s + px / 2, px / 2 - (Q[:, 2] - (lo[1] + hi[1]) / 2) * s], 1)
    n = -np.cross(Q[T][:, 1] - Q[T][:, 0], Q[T][:, 2] - Q[T][:, 0])  # MetaHuman winding, see viewmap
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    keep = n[:, 1] > 0
    L = np.array([0.3, 0.85, 0.4]) / np.linalg.norm([0.3, 0.85, 0.4])
    sh = np.clip(n @ L, 0.2, 1)
    att = np.concatenate([C, np.repeat(sh[:, None, None], 3, 1)], 2)
    img, _ = viewmap._raster(V[T][keep], att[keep], Q[:, 1][T][keep], px, px)
    uv = np.nan_to_num(img[..., :2], nan=-1)
    H, W = tex.shape[:2]
    col = cv2.remap(tex, (uv[..., 0] * W).astype(np.float32), (uv[..., 1] * H).astype(np.float32), cv2.INTER_LINEAR)
    shade = np.nan_to_num(img[..., 2], nan=0)[..., None]
    return np.clip(col.astype(np.float32) * (0.55 + 0.6 * shade), 0, 255).astype(np.uint8)


def main():
    base = cv2.imread(sys.argv[1])
    look = cli.find(sys.argv[2])
    out, _, _ = paint.paint(base, None, look)
    views = [(0, 0), (40, 0), (-40, 0), (0, -35)]
    rows = [np.hstack([render(t, y, p) for y, p in views]) for t in (base, out)]
    sheet = np.vstack(rows)
    cv2.putText(sheet, "before", (8, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    cv2.putText(sheet, sys.argv[2], (8, 546), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    cv2.imwrite(sys.argv[3], sheet)
    vm, _ = paint.view_face()
    skin = cv2.resize(vm.uv_skin, (base.shape[1], base.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
    skin = cv2.erode(skin.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    d = np.abs(out.astype(np.float32) - base.astype(np.float32)).mean(2)
    g = np.maximum(np.abs(np.diff(d, axis=0))[:, :-1], np.abs(np.diff(d, axis=1))[:-1, :])
    print("edge jump p99.9 %.1f max %.1f (0..255) over skin" % (np.percentile(g[skin[:-1, :-1]], 99.9), g[skin[:-1, :-1]].max()))
    cv2.imwrite(os.path.splitext(sys.argv[3])[0] + "_tex.png", out)


if __name__ == "__main__":
    main()

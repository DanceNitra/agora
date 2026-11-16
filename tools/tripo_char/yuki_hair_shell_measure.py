"""Headless Blender (blender_headless.sh): measures how the hair sits on the back of the head, so a lumpy or deformed
back reads as numbers, not as an impression.

    ./blender_headless.sh yuki_hair_shell_measure.py -- <strands.abc> <head.fbx> <out_dir> [label]

Rays from the middle of the skull (the centre of the head mesh above the ear line) go out in a grid of directions over
the back half and the top of the head: azimuth -100 to +100 degrees around the back (0 = straight back), elevation -30
to +80 degrees. Per direction: the scalp radius (head mesh) and the outer hair radius (95th percentile of the strand
points in that direction). Thickness = hair minus scalp. Writes <out_dir>/shell_<label>.json (thickness map, mean,
spread, the largest bump against the local mean of its neighbours, left-right difference) and shell_<label>.png
(the thickness map as an image, back seen from behind, left of the picture = Yuki's right)."""
import json, math, sys
from pathlib import Path

import bpy
import numpy as np

abc, head, out = sys.argv[sys.argv.index("--") + 1:][:3]
label = (sys.argv[sys.argv.index("--") + 1:] + ["x", "x", "x", "hair"])[3]
out = Path(out).resolve()
out.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.alembic_import(filepath=str(Path(abc).resolve()))
P = []
for o in bpy.data.objects:
    if o.type == "CURVES":
        mw = np.array(o.matrix_world)
        pts = np.array([p.position for p in o.data.points], float) if hasattr(o.data, "points") else np.zeros((0, 3))
        if len(pts):
            P.append(pts @ mw[:3, :3].T + mw[:3, 3])
    elif o.type == "CURVE":
        mw = np.array(o.matrix_world)
        for sp in o.data.splines:
            pts = np.array([tuple(p.co)[:3] for p in sp.points], float)
            P.append(pts @ mw[:3, :3].T + mw[:3, 3])
P = np.concatenate(P)
pre = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(Path(head).resolve()))
from mathutils import Vector
from mathutils.bvhtree import BVHTree
verts, polys = [], []
for o in bpy.data.objects:
    if o not in pre and o.type == "MESH":
        off = len(verts)
        verts += [tuple(o.matrix_world @ v.co) for v in o.data.vertices]
        polys += [tuple(off + i for i in p.vertices) for p in o.data.polygons]
H = np.array(verts)
bvh = BVHTree.FromPolygons([Vector(v) for v in verts], polys)
# The hair file and the head share Blender's metres (the strand builder fits the hair onto this head).
top = H[:, 2].max()
skull = H[H[:, 2] > top - 0.12]
c = np.array([(skull[:, 0].max() + skull[:, 0].min()) / 2, (skull[:, 1].max() + skull[:, 1].min()) / 2, top - 0.095])
# The back is the side the long hair hangs on: the mean depth of the strand points below the chin.
low = P[P[:, 2] < c[2] - 0.15]
back_sign = 1.0 if low[:, 1].mean() > c[1] else -1.0
AZ, EL = np.arange(-100, 101, 5), np.arange(-30, 81, 5)


def polar(X):
    d = X - c
    r = np.linalg.norm(d, axis=1)
    az = np.degrees(np.arctan2(d[:, 0], back_sign * d[:, 1]))
    el = np.degrees(np.arcsin(np.clip(d[:, 2] / np.maximum(r, 1e-9), -1, 1)))
    return r, az, el


rp, azp, elp = polar(P)
T = np.full((len(EL), len(AZ)), np.nan)
S_ = np.full_like(T, np.nan)
for i, e in enumerate(EL):
    for j, a in enumerate(AZ):
        er, ar = math.radians(e), math.radians(a)
        d = Vector((math.cos(er) * math.sin(ar), back_sign * math.cos(er) * math.cos(ar), math.sin(er)))
        hit = bvh.ray_cast(Vector(c), d, 0.5)
        mp = (np.abs(azp - a) < 3.5) & (np.abs(elp - e) < 3.5)
        if hit[0] is None or mp.sum() < 20:
            continue
        S_[i, j] = (hit[0] - Vector(c)).length
        T[i, j] = np.percentile(rp[mp], 95) - S_[i, j]
k = np.ones((3, 3)) / 9
pad = np.pad(T, 1, mode="edge")
local = np.array([[np.nanmean(pad[i:i + 3, j:j + 3]) for j in range(T.shape[1])] for i in range(T.shape[0])])
bump = T - local
lr = T - T[:, ::-1]
i0, j0 = np.unravel_index(np.nanargmax(np.abs(bump)), bump.shape)
rep = dict(label=label, points=int(len(P)), centre=c.round(4).tolist(), mean_mm=round(float(np.nanmean(T)) * 1000, 1),
           spread_mm=round(float(np.nanstd(T)) * 1000, 1), max_mm=round(float(np.nanmax(T)) * 1000, 1),
           min_mm=round(float(np.nanmin(T)) * 1000, 1),
           worst_bump_mm=round(float(bump[i0, j0]) * 1000, 1), worst_bump_at=dict(az=int(AZ[j0]), el=int(EL[i0])),
           bump_rms_mm=round(float(np.sqrt(np.nanmean(bump ** 2))) * 1000, 1),
           left_right_rms_mm=round(float(np.sqrt(np.nanmean(lr ** 2)) / 2) * 1000, 1),
           thickness_mm=(np.round(T * 1000, 1)).tolist(), az=AZ.tolist(), el=EL.tolist())
json.dump(rep, open(out / f"shell_{label}.json", "w"), indent=1)
img = np.nan_to_num(T, nan=0) * 1000
img = np.clip(img / 80.0, 0, 1)
rgb = np.stack([img, 1 - np.abs(img - 0.5) * 2, 1 - img], -1)
rgb = np.repeat(np.repeat(rgb[::-1], 12, 0), 12, 1)
ib = bpy.data.images.new("shell", rgb.shape[1], rgb.shape[0])
ib.pixels = np.concatenate([rgb[::-1], np.ones(rgb.shape[:2] + (1,))], -1).ravel().tolist()
ib.filepath_raw = str(out / f"shell_{label}.png")
ib.file_format = "PNG"
ib.save()
print("SHELL", json.dumps({k: v for k, v in rep.items() if k not in ("thickness_mm", "az", "el")}), flush=True)

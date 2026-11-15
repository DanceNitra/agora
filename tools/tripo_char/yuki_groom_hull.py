"""Outer hull of Yuki's strand groom as a radius per direction around the head, for cutting the Tripo ears: only
what sticks out of our own hair is kept (owner, 2026-11-14: hair pieces under the ears showed from behind).

    ./blender_headless.sh yuki_groom_hull.py -- <groom.abc> <mh_head.fbx> <out.npz>

Writes centre (the MetaHuman head's bounding-box centre), the elevation and azimuth bin edges (STEP degrees) and the
largest strand-point radius in each bin (0 where no strand passes), plus the head's own radius per bin."""
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

abc, head_p, outp = sys.argv[-3], sys.argv[-2], sys.argv[-1]
STEP = 3.0
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(Path(head_p).resolve()))
hm = max((o for o in bpy.data.objects if o.type == "MESH"), key=lambda o: len(o.data.vertices))
bpy.context.view_layer.update()
HV = np.array([(hm.matrix_world @ v.co)[:] for v in hm.data.vertices])
c = (HV.min(0) + HV.max(0)) / 2
before = set(bpy.data.objects)
bpy.ops.wm.alembic_import(filepath=str(Path(abc).resolve()))
new = [o for o in bpy.data.objects if o not in before]
pts = []
for o in new:
    dg = bpy.context.evaluated_depsgraph_get()
    oe = o.evaluated_get(dg)
    if o.type == "CURVES":
        P = np.zeros(len(oe.data.points) * 3)
        oe.data.points.foreach_get("position", P)
        P = P.reshape(-1, 3)
        M = np.array(o.matrix_world)
        pts.append(P @ M[:3, :3].T + M[:3, 3])
    elif o.type == "CURVE":
        for sp in oe.data.splines:
            for p in sp.points:
                pts.append(np.array([(o.matrix_world @ Vector(p.co[:3]))[:]]))
P = np.vstack(pts)
print("GROOM points", len(P), "bbox", P.min(0).round(3), P.max(0).round(3), "head bbox", HV.min(0).round(3), HV.max(0).round(3))
d = P - c
r = np.linalg.norm(d, axis=1)
el = np.degrees(np.arcsin(np.clip(d[:, 2] / np.maximum(r, 1e-9), -1, 1)))
az = np.degrees(np.arctan2(d[:, 1], d[:, 0]))
ne, na = int(180 / STEP), int(360 / STEP)
ie = np.clip(((el + 90) / STEP).astype(int), 0, ne - 1)
ia = np.clip(((az + 180) / STEP).astype(int), 0, na - 1)
hull = np.zeros((ne, na))
np.maximum.at(hull, (ie, ia), r)
bvh = BVHTree.FromPolygons([Vector(v) for v in HV], [tuple(q.vertices) for q in hm.data.polygons])
head_r = np.zeros((ne, na))
for i in range(ne):
    for j in range(na):
        e_, a_ = math.radians(-90 + (i + 0.5) * STEP), math.radians(-180 + (j + 0.5) * STEP)
        dirv = Vector((math.cos(e_) * math.cos(a_), math.cos(e_) * math.sin(a_), math.sin(e_)))
        h = bvh.ray_cast(Vector(c) + dirv * 0.4, -dirv, 0.4)
        head_r[i, j] = 0.4 - h[3] if h[0] is not None else 0
np.savez(outp, centre=c, step=STEP, hull=hull, head=head_r)
thick = (hull - head_r)[(hull > 0) & (head_r > 0)]
print("HULL saved", outp, "hair thickness over the head cm p10/50/90", np.round(np.percentile(thick, [10, 50, 90]) * 100, 2))

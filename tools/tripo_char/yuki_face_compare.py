"""Render the conformed MetaHuman head beside Yuki's Tripo face and measure the fit.

    ./blender_headless.sh yuki_face_compare.py -- <mh_head.fbx> <yuki_head.fbx> <out_dir>

The head is aligned to the face patch by rigid ICP with uniform scale (the head-only conform does not keep the
patch's position). Distances are from patch vertices to the MetaHuman surface after alignment. Renders: front and
three-quarter views of the MetaHuman head in plain clay, and the patch from the same front camera.
"""
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

mh_p, patch_p, out = sys.argv[-3], sys.argv[-2], Path(sys.argv[-1]).resolve()
out.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)


def load(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(Path(path).resolve()))
    new = [o for o in bpy.data.objects if o not in before]
    m = max((o for o in new if o.type == "MESH"), key=lambda o: len(o.data.vertices))
    for o in new:
        if o.type == "MESH" and o is not m:
            o.hide_render = True
    for md in list(m.modifiers):
        m.modifiers.remove(md)
    bpy.context.view_layer.update()
    mw = m.matrix_world.copy()
    m.parent = None
    m.matrix_world = Matrix.Identity(4)
    m.data.transform(mw)
    for o in new:
        if o.type != "MESH":
            bpy.data.objects.remove(o)
    return m


mh = load(mh_p)
pa = load(patch_p)
M = np.array([v.co[:] for v in mh.data.vertices])
Q = np.array([v.co[:] for v in pa.data.vertices])


def bvh_of(o):
    return BVHTree.FromPolygons([v.co.copy() for v in o.data.vertices], [tuple(p.vertices) for p in o.data.polygons])


# initial guess: MetaHuman faces -Y like the patch; move the head's front-most face point onto the patch's front
mf = M[np.argmin(M[:, 1])]
qf = Q[np.argmin(Q[:, 1])]
mh.data.transform(Matrix.Translation(Vector(qf - mf)))
bvh = bvh_of(mh)
hist = []
for it in range(40):
    near = np.array([bvh.find_nearest(Vector(q))[0][:] for q in Q])
    d = np.linalg.norm(near - Q, axis=1)
    keep = d < np.percentile(d, 90)
    A, B = near[keep], Q[keep]          # move the head so A goes onto B
    ca, cb = A.mean(0), B.mean(0)
    U, S, Vt = np.linalg.svd((A - ca).T @ (B - cb))
    R = Vt.T @ U.T
    if np.linalg.det(R) < 0:
        Vt[-1] *= -1
        R = Vt.T @ U.T
    s = float(np.sqrt(((B - cb) ** 2).sum() / ((A - ca) ** 2).sum()))
    s = min(max(s, 0.9), 1.1)
    T = Matrix.Translation(Vector(cb)) @ Matrix.Scale(s, 4) @ Matrix(R.tolist()).to_4x4() @ Matrix.Translation(Vector(-ca))
    mh.data.transform(T)
    bvh = bvh_of(mh)
    hist.append(round(float(np.median(d)) * 1000, 2))
near = np.array([bvh.find_nearest(Vector(q))[0][:] for q in Q])
d = np.linalg.norm(near - Q, axis=1)
z = Q[:, 2] - Q[:, 2].min()
zr = z / max(z.max(), 1e-6)
bands = {"chin_mouth (lower third)": zr < 0.33, "nose_cheeks (middle)": (zr >= 0.33) & (zr < 0.66), "eyes (upper third)": zr >= 0.66}
rep = {"icp_median_mm_by_iter": hist[::5] + hist[-1:], "dist_mm_p50_p90_p99": [round(float(x) * 1000, 1) for x in np.percentile(d, [50, 90, 99])],
       "by_band_p50_p90_mm": {k: [round(float(x) * 1000, 1) for x in np.percentile(d[m], [50, 90])] for k, m in bands.items() if m.any()}}
print("FIT", json.dumps(rep), flush=True)
(out / "fit.json").write_text(json.dumps(rep, indent=1))

scene = bpy.context.scene
try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError:
    scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = scene.render.resolution_y = 900
scene.view_settings.view_transform = "Standard"
world = bpy.data.worlds.new("w")
world.color = (0.55, 0.55, 0.55)
scene.world = world
clay = bpy.data.materials.new("clay")
clay.diffuse_color = (0.85, 0.72, 0.66, 1)
mh.data.materials.clear()
mh.data.materials.append(clay)
for name, rot in (("key", (50, 0, -30)), ("fill", (70, 0, 40))):
    L = bpy.data.objects.new(name, bpy.data.lights.new(name, "SUN"))
    L.data.energy = 3.0 if name == "key" else 1.2
    L.rotation_euler = [math.radians(a) for a in rot]
    scene.collection.objects.link(L)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
cam.data.type = "ORTHO"
cam.data.ortho_scale = 0.24
scene.collection.objects.link(cam)
scene.camera = cam
c = Q.mean(0)
c[2] -= 0.0


def shot(name, yaw_deg, show_patch):
    pa.hide_render = not show_patch
    mh.hide_render = show_patch
    a = math.radians(yaw_deg)
    cam.location = Vector((c[0] + 1.0 * math.sin(a), c[1] - 1.0 * math.cos(a), c[2] + 0.02))
    cam.rotation_euler = (math.pi / 2, 0, a)
    scene.render.filepath = str(out / name)
    bpy.ops.render.render(write_still=True)


shot("mh_front.png", 0, False)
shot("mh_34.png", 35, False)
shot("mh_side.png", 90, False)
shot("patch_front.png", 0, True)
print("DONE", out, flush=True)

"""Front, three-quarter and side renders of a head-only Tripo model, textured and in clay, plus triangle count.

    ./blender_headless.sh head_view.py -- <model.glb> <out_dir>

Tripo exports facing +X; the head is turned to face -Y and framed by its bounding box.
"""
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

src, out = Path(sys.argv[-2]).resolve(), Path(sys.argv[-1]).resolve()
out.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(src))
meshes = [o for o in bpy.data.objects if o.type == "MESH"]
for m in meshes:
    m.data.transform(m.matrix_world)
    m.parent = None
    m.matrix_world = Matrix.Identity(4)
P = np.concatenate([np.array([v.co[:] for v in m.data.vertices]) for m in meshes])
# The face is the side with the nose: the most protruding horizontal direction of the head is the front.
# Only the head counts (the shoulders are the widest part of a bust): the top 30 %, protrusion from its own centre.
mid = P[P[:, 2] > P[:, 2].min() + 0.7 * np.ptp(P[:, 2])]
c = mid.mean(0)
dirs = {"+X": (mid[:, 0] - c[0]).max(), "-X": (c[0] - mid[:, 0]).max(), "+Y": (mid[:, 1] - c[1]).max(), "-Y": (c[1] - mid[:, 1]).max()}
front = max(dirs, key=dirs.get)
# The back of a bald skull can stick out further than the nose (Yuki's head: -X picked, the face is +X).
import os
front = os.environ.get("FRONT", front)
turn = {"+X": -math.pi / 2, "-X": math.pi / 2, "+Y": math.pi, "-Y": 0.0}[front]
for m in meshes:
    m.data.transform(Matrix.Rotation(turn, 4, "Z"))
P = np.concatenate([np.array([v.co[:] for v in m.data.vertices]) for m in meshes])
lo, hi = P.min(0), P.max(0)
c = (lo + hi) / 2
tris = sum(sum(len(p.vertices) - 2 for p in m.data.polygons) for m in meshes)
stats = {"triangles": tris, "vertices": int(len(P)), "size_xyz": [round(float(x), 4) for x in hi - lo], "front_was": front}
print("STATS", json.dumps(stats), flush=True)
(out / "stats.json").write_text(json.dumps(stats, indent=1))

scene = bpy.context.scene
try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError:
    scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = scene.render.resolution_y = 1024
scene.view_settings.view_transform = "Standard"
world = bpy.data.worlds.new("w")
world.color = (0.6, 0.6, 0.6)
scene.world = world
for name, rot, e in (("key", (55, 0, -30), 3.0), ("fill", (65, 0, 45), 1.2)):
    L = bpy.data.objects.new(name, bpy.data.lights.new(name, "SUN"))
    L.data.energy = e
    L.rotation_euler = [math.radians(a) for a in rot]
    scene.collection.objects.link(L)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
cam.data.type = "ORTHO"
cam.data.ortho_scale = float(max(hi[0] - lo[0], hi[2] - lo[2])) * 1.08
scene.collection.objects.link(cam)
scene.camera = cam
orig = [list(m.data.materials) for m in meshes]
clay = bpy.data.materials.new("clay")
clay.diffuse_color = (0.8, 0.8, 0.8, 1)


def shot(name, yaw, use_clay):
    for m, mats in zip(meshes, orig):
        m.data.materials.clear()
        for mat in ([clay] if use_clay else mats):
            m.data.materials.append(mat)
    a = math.radians(yaw)
    cam.location = Vector((c[0] + 3 * math.sin(a), c[1] - 3 * math.cos(a), c[2]))
    cam.rotation_euler = (math.pi / 2, 0, a)
    scene.render.filepath = str(out / name)
    bpy.ops.render.render(write_still=True)


for nm, yaw in (("front", 0), ("q34", 35), ("side", 90)):
    shot(f"{nm}_tex.png", yaw, False)
    shot(f"{nm}_clay.png", yaw, True)
print("DONE", out, flush=True)

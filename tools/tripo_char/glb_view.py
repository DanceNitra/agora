"""Whole-figure and armpit views of a Tripo GLB, textured and clay.

    blender_headless.sh glb_view.py -- <model.glb> <out_dir>
"""
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix

glb, out = str(Path(sys.argv[-2]).resolve()), Path(sys.argv[-1]).resolve()
out.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
mesh = next(o for o in bpy.data.objects if o.type == "MESH")
mesh.data.transform(mesh.matrix_world)
mesh.matrix_world = Matrix.Identity(4)
P = np.array([v.co[:] for v in mesh.data.vertices])
if np.ptp(P[:, 1]) > np.ptp(P[:, 0]):  # arms along Y: turn them onto X
    mesh.data.transform(Matrix.Rotation(-math.pi / 2, 4, "Z"))
    P = np.array([v.co[:] for v in mesh.data.vertices])
lo, hi = P.min(0), P.max(0)
h = hi[2] - lo[2]
mesh.data.transform(Matrix.Translation((-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2])))
print("BOUNDS size", (hi - lo).round(3).tolist(), "verts", len(P), "faces", len(mesh.data.polygons))
scene = bpy.context.scene
try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError:
    scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = scene.render.resolution_y = 900
world = bpy.data.worlds.new("w")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.7, 0.7, 0.7, 1)
scene.world = world
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
sun.data.energy = 3
scene.collection.objects.link(sun)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
cam.data.type = "ORTHO"
scene.collection.objects.link(cam)
scene.camera = cam
clay = bpy.data.materials.new("clay")
clay.use_nodes = True
next(n for n in clay.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"].default_value = (0.6, 0.6, 0.6, 1)
tex = mesh.data.materials[0]
z, a = 0.5 * h, 0.72 * h
VIEWS = [("front", (0, -4, z), (90, 0, 0), 1.1 * h), ("back", (0, 4, z), (90, 0, 180), 1.1 * h),
         ("side", (4, 0, z), (90, 0, 90), 1.1 * h), ("armpit_r", (-0.14 * h, -4, a), (90, 0, 0), 0.3 * h),
         ("armpit_l", (0.14 * h, -4, a), (90, 0, 0), 0.3 * h), ("armpit_r_back", (-0.14 * h, 4, a), (90, 0, 180), 0.3 * h)]
for label, m in (("tex", tex), ("clay", clay)):
    mesh.data.materials[0] = m
    for name, loc, rot, sc in VIEWS:
        cam.location, cam.rotation_euler, cam.data.ortho_scale = loc, tuple(math.radians(x) for x in rot), sc
        sun.rotation_euler = (math.radians(55), 0, math.radians(rot[2] - 25))
        scene.render.filepath = str(out / f"{name}_{label}.png")
        bpy.ops.render.render(write_still=True)
print("done")

"""Close-ups of the right sleeve of the source dressed GLB, textured and clay, to tell source geometry from our faults.

    blender_headless.sh src_view.py -- <dressed.glb> <out_dir>
"""
import math
import sys
from pathlib import Path

import bpy
import numpy as np

glb, out = str(Path(sys.argv[-2]).resolve()), Path(sys.argv[-1]).resolve()
out.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
mesh = next(o for o in bpy.data.objects if o.type == "MESH")
P = np.array([mesh.matrix_world @ v.co for v in mesh.data.vertices])
lo, hi = P.min(0), P.max(0)
h = hi[2] - lo[2]
wide = 0 if (hi[0] - lo[0]) > (hi[1] - lo[1]) else 1  # the axis the arms lie along
print("bounds", lo, hi, "arms along", "xy"[wide])
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
cam.data.ortho_scale = 0.33 * h
scene.collection.objects.link(cam)
scene.camera = cam
clay = bpy.data.materials.new("clay")
clay.use_nodes = True
next(n for n in clay.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"].default_value = (0.6, 0.6, 0.6, 1)
tex = mesh.data.materials[0]
mid = (lo + hi) / 2
arm_z = lo[2] + 0.78 * h
for side in (-1, 1):
    c = mid.copy()
    c[wide] = mid[wide] + side * 0.27 * (hi[wide] - lo[wide])
    c[2] = arm_z
    for vname, d in (("a", 1), ("b", -1)):  # the two horizontal views across the arm
        loc = c.copy()
        loc[1 - wide] += d * 4
        yaw = {(0, 1): 180, (0, -1): 0, (1, 1): 90, (1, -1): -90}[(wide, d)]
        cam.location = tuple(loc)
        cam.rotation_euler = (math.radians(90), 0, math.radians(yaw))
        sun.rotation_euler = (math.radians(55), 0, math.radians(yaw - 25))
        for label, m in (("tex", tex), ("clay", clay)):
            mesh.data.materials[0] = m
            scene.render.filepath = str(out / f"src_arm{'L' if side > 0 else 'R'}_{vname}_{label}.png")
            bpy.ops.render.render(write_still=True)
print("done")

"""Close-up renders of an exported costume FBX, textured and as plain clay, to tell a geometry fault from a texture one.

    blender_headless.sh costume_view.py -- <hero01_costume.fbx> <out_dir>
"""
import math
import sys
from pathlib import Path

import bpy

fbx, out = str(Path(sys.argv[-2]).resolve()), Path(sys.argv[-1]).resolve()
out.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=fbx)
mesh = next(o for o in bpy.data.objects if o.type == "MESH")
scene = bpy.context.scene
try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError:
    scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = scene.render.resolution_y = 900
world = bpy.data.worlds.new("w")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.7, 0.7, 0.7, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 1.0
scene.world = world
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
sun.data.energy = 3
sun.rotation_euler = (math.radians(55), 0, math.radians(-25))
scene.collection.objects.link(sun)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
cam.data.type = "ORTHO"
scene.collection.objects.link(cam)
scene.camera = cam
clay = bpy.data.materials.new("clay")
clay.use_nodes = True
next(n for n in clay.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"].default_value = (0.6, 0.6, 0.6, 1)
tex = mesh.data.materials[0]
# name, camera location, rotation (deg), ortho scale
VIEWS = [("collar_front", (0, -4, 1.52), (90, 0, 0), 0.4), ("collar_left", (4, 0, 1.52), (90, 0, 90), 0.4),
         ("collar_right", (-4, 0, 1.52), (90, 0, -90), 0.4), ("collar_back", (0, 4, 1.52), (90, 0, 180), 0.4),
         ("arm_r_front", (-0.3, -4, 1.3), (90, 0, 0), 0.5), ("arm_l_front", (0.3, -4, 1.3), (90, 0, 0), 0.5),
         ("arm_l_side", (4, 0, 1.3), (90, 0, 90), 0.6), ("arm_r_side", (-4, 0, 1.3), (90, 0, -90), 0.6)]
for label, m in (("tex", tex), ("clay", clay)):
    mesh.data.materials[0] = m
    for name, loc, rot, sc in VIEWS:
        cam.location, cam.rotation_euler, cam.data.ortho_scale = loc, tuple(math.radians(a) for a in rot), sc
        scene.render.filepath = str(out / f"{name}_{label}.png")
        bpy.ops.render.render(write_still=True)
print("done", out)

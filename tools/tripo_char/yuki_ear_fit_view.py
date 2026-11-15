"""Headless Blender (blender_headless.sh): renders how the costume's Tripo ears sit on the wig's ears. Imports the
MetaHuman head, the costume FBX and the wig's ear hulls (yuki_ears.fbx from yuki_hair_strands), shows the hulls as
red wire over the grey costume, and renders front, side, back and three-quarter views of the head top.

    ./blender_headless.sh yuki_ear_fit_view.py -- <costume.fbx> <yuki_ears.fbx> <head.fbx> <out_dir>"""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

costume, ears, head, out = sys.argv[sys.argv.index("--") + 1:][:4]
out = Path(out).resolve()
out.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)


def imp(p):
    pre = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(Path(p).resolve()))
    return [o for o in bpy.data.objects if o not in pre and o.type == "MESH"]


def mat(name, rgb, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = 0.6
    return m


grey, skin, red = mat("grey", (0.55, 0.55, 0.58)), mat("skin", (0.8, 0.62, 0.55)), mat("red", (0.9, 0.05, 0.05))
for o in imp(head):
    o.data.materials.clear()
    o.data.materials.append(skin)
for o in imp(costume):
    o.data.materials.clear()
    o.data.materials.append(grey)
hulls = imp(ears)
for o in hulls:
    o.data.materials.clear()
    o.data.materials.append(red)
    w = o.modifiers.new("wire", "WIREFRAME")
    w.thickness = 0.0008
P = [o.matrix_world @ v.co for o in hulls for v in o.data.vertices]
c = sum(P, Vector()) / len(P)
c.x = 0.0
c.z -= 0.02
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE"
scene.render.resolution_x, scene.render.resolution_y = 900, 700
w_ = bpy.data.worlds.new("w")
w_.use_nodes = True
w_.node_tree.nodes["Background"].inputs["Color"].default_value = (0.9, 0.9, 0.92, 1)
w_.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0
scene.world = w_
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
sun.data.energy = 3.0
sun.rotation_euler = (math.radians(50), 0, math.radians(30))
scene.collection.objects.link(sun)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
cam.data.lens = 85
scene.collection.objects.link(cam)
scene.camera = cam
for name, az, el in (("front", 0, 10), ("side_l", 90, 5), ("back", 180, 10), ("q34", 40, 25), ("side_r", -90, 5)):
    d = 0.75
    a, e = math.radians(az), math.radians(el)
    cam.location = c + Vector((d * math.sin(a) * math.cos(e), -d * math.cos(a) * math.cos(e), d * math.sin(e)))
    cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(out / f"earfit_{name}.png")
    bpy.ops.render.render(write_still=True)
print("EARFIT rendered", out, flush=True)

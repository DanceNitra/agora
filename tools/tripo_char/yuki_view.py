"""Whole figure, face close-ups and the mouth wireframe of a Tripo model (FBX or GLB).

    ./blender_headless.sh yuki_view.py -- <model.fbx|glb> <out_dir>

The face views decide whether a mouth, lips and eyelids can be built on this mesh.
"""
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix

src, out = Path(sys.argv[-2]).resolve(), Path(sys.argv[-1]).resolve()
out.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
if src.suffix.lower() == ".fbx":
    bpy.ops.import_scene.fbx(filepath=str(src))
else:
    bpy.ops.import_scene.gltf(filepath=str(src))
meshes = [o for o in bpy.data.objects if o.type == "MESH"]
for m in meshes:
    m.data.transform(m.matrix_world)
    m.matrix_world = Matrix.Identity(4)
    m.parent = None
P = np.concatenate([np.array([v.co[:] for v in m.data.vertices]) for m in meshes])
if np.ptp(P[:, 1]) > np.ptp(P[:, 2]):   # Y-up import: stand it on Z
    for m in meshes:
        m.data.transform(Matrix.Rotation(math.pi / 2, 4, "X"))
    P = np.concatenate([np.array([v.co[:] for v in m.data.vertices]) for m in meshes])
TURN = float(__import__("os").environ.get("TURN_DEG", "0"))   # yuki P2 faces +X: TURN_DEG=-90
if TURN:
    for m in meshes:
        m.data.transform(Matrix.Rotation(math.radians(TURN), 4, "Z"))
    P = np.concatenate([np.array([v.co[:] for v in m.data.vertices]) for m in meshes])
lo, hi = P.min(0), P.max(0)
h = hi[2] - lo[2]
shift = Matrix.Translation((-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]))
for m in meshes:
    m.data.transform(shift)
print("MESHES", [(m.name, len(m.data.vertices), len(m.data.polygons)) for m in meshes])
print("BOUNDS", (hi - lo).round(3).tolist())
quads = sum(1 for m in meshes for p in m.data.polygons if len(p.vertices) == 4)
print("QUADS", quads, "of", sum(len(m.data.polygons) for m in meshes))

scene = bpy.context.scene
try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError:
    scene.render.engine = "BLENDER_EEVEE"
world = bpy.data.worlds.new("w")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.75, 0.75, 0.75, 1)
scene.world = world
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
sun.data.energy = 3
sun.rotation_euler = (math.radians(55), 0, math.radians(-20))
scene.collection.objects.link(sun)
if __import__("os").environ.get("WARM") == "1":
    # Closer to the concept's light: warm key from the front left, soft warm fill, punchy contrast.
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.95, 0.88, 0.85, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.7
    sun.data.energy = 4.5
    sun.data.color = (1.0, 0.93, 0.86)
    sun.rotation_euler = (math.radians(50), 0, math.radians(-30))
    scene.view_settings.view_transform = "AgX"
    try:
        scene.view_settings.look = "AgX - Punchy"
    except TypeError:
        pass
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
cam.data.type = "ORTHO"
scene.collection.objects.link(cam)
scene.camera = cam

# The face: the front-most point of the top 12 % of the figure, ears excluded by taking the
# median x of that band.
Pc = P - np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]])
band = Pc[(Pc[:, 2] > 0.84 * h) & (Pc[:, 2] < 0.93 * h)]
# The nose tip is the front-most point (smallest y) of the head band; hair hangs behind it.
nose = band[np.argmin(band[:, 1])]
face_x, face_z = float(nose[0]), float(nose[2])
face_z += float(__import__("os").environ.get("FACE_DZ", "0")) * h   # bangs can be the front-most point
ONLY_FACE = __import__("os").environ.get("ONLY_FACE") == "1"
print("FACE at x", round(face_x, 3), "z", round(face_z, 3))

clay = bpy.data.materials.new("clay")
clay.use_nodes = True
next(n for n in clay.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"].default_value = (0.65, 0.6, 0.58, 1)
orig = [[s.material for s in m.material_slots] for m in meshes]

VIEWS = [("full_front", (0, -5, 0.5 * h), (90, 0, 0), 1.08 * h, 900),
         ("full_side", (5, 0, 0.5 * h), (90, 0, 90), 1.08 * h, 900),
         ("full_back", (0, 5, 0.5 * h), (90, 0, 180), 1.08 * h, 900),
         ("face_front", (face_x, -5, face_z), (90, 0, 0), 0.11 * h, 1000),
         ("face_34", (face_x + 3.5, -3.5, face_z), (90, 0, 45), 0.11 * h, 1000),
         ("face_side", (face_x + 5, 0, face_z), (90, 0, 90), 0.11 * h, 1000),
         ("mouth_front", (face_x, -5, face_z - 0.025 * h), (90, 0, 0), 0.045 * h, 1000)]


def set_material(mat_lists):
    for m, mats in zip(meshes, mat_lists):
        for i, s in enumerate(m.material_slots):
            s.material = mats[i] if isinstance(mats, list) else mats


for label, mats in (("tex", orig), ("clay", [clay] * len(meshes))):
    set_material(mats if label == "tex" else [[clay] * len(m.material_slots) for m in meshes])
    for name, loc, rot, sc, res in VIEWS:
        if label == "clay" and name.startswith("full") and name != "full_front":
            continue
        if ONLY_FACE and not name.startswith("face"):
            continue
        cam.location, cam.rotation_euler, cam.data.ortho_scale = loc, tuple(math.radians(x) for x in rot), sc
        scene.render.resolution_x = scene.render.resolution_y = res
        scene.render.filepath = str(out / f"{name}_{label}.png")
        bpy.ops.render.render(write_still=True)

# Wireframe of the mouth: Freestyle-free, a wireframe modifier copy in black over clay.
set_material([[clay] * len(m.material_slots) for m in meshes])
black = bpy.data.materials.new("black")
black.use_nodes = True
next(n for n in black.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"].default_value = (0, 0, 0, 1)
for m in meshes:
    w = m.copy()
    w.data = m.data.copy()
    scene.collection.objects.link(w)
    mod = w.modifiers.new("wire", "WIREFRAME")
    mod.thickness = 0.0006 * h
    mod.use_replace = True
    w.data.materials.clear()
    w.data.materials.append(black)
for name, loc, rot, sc, res in VIEWS:
    if name in ("face_front", "mouth_front", "face_side"):
        cam.location, cam.rotation_euler, cam.data.ortho_scale = loc, tuple(math.radians(x) for x in rot), sc
        scene.render.resolution_x = scene.render.resolution_y = res
        scene.render.filepath = str(out / f"{name}_wire.png")
        bpy.ops.render.render(write_still=True)
print("done")

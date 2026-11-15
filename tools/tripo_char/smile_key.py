"""Add a "smile" shape key to Yuki: lip corners up, slightly back and out, cheeks lifted a little.

  TURN_DEG=-90 ./blender_headless.sh smile_key.py -- <in.glb> <work_dir> <out.glb> <render_dir>

Corner positions come from work_dir/landmarks.json (texture_landmarks.py, same frame). The
displacement falls off smoothly with distance, so the texture's mouth line moves with the geometry.
Renders the face at smile 0 and 0.8 into render_dir for the comparison.
"""
import json
import math
import os
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix

args = sys.argv[sys.argv.index("--") + 1:]
src, work, out_glb, rdir = (Path(a).resolve() for a in args)
rdir.mkdir(parents=True, exist_ok=True)
TURN = float(os.environ.get("TURN_DEG", "0"))
lm = json.loads((work / "landmarks.json").read_text())
cam = json.loads((work / "camera.json").read_text())

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(src))
mesh = next(o for o in bpy.data.objects if o.type == "MESH")
mesh.data.transform(mesh.matrix_world)
mesh.matrix_world = Matrix.Identity(4)
mesh.parent = None
if TURN:
    mesh.data.transform(Matrix.Rotation(math.radians(TURN), 4, "Z"))
n = len(mesh.data.vertices)
co = np.empty(n * 3)
mesh.data.vertices.foreach_get("co", co)
P = co.reshape(-1, 3)
lo, hi = P.min(0), P.max(0)
shift = np.array([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]])
mesh.data.transform(Matrix.Translation(shift))
P = P + shift
h = hi[2] - lo[2]

L, R = np.array(lm["lcorner"]["world"]), np.array(lm["rcorner"]["world"])
C = np.array(lm["lips"]["world"])
mouth_w = np.linalg.norm(R - L)
print("mouth width m", round(mouth_w, 4))

disp = np.zeros_like(P)
for corner, side in ((L, -1), (R, 1)):
    d = np.linalg.norm(P - corner, axis=1)
    r = 0.55 * mouth_w
    w = np.clip(1 - d / r, 0, 1) ** 2 * (3 - 2 * np.clip(1 - d / r, 0, 1))   # smoothstep falloff
    w *= (P[:, 1] < corner[1] + 0.02)                                       # front of the face only
    # Audit 2026-11-13: 0.11/0.06/0.06 "only lifts the corners slightly". Stronger corner pull.
    disp[:, 2] += w * 0.17 * mouth_w      # up
    disp[:, 1] += w * 0.08 * mouth_w      # back into the cheek
    disp[:, 0] += w * side * 0.08 * mouth_w   # out
# Cheeks rise a touch above and outside each corner.
for corner, side in ((L, -1), (R, 1)):
    cheek = corner + np.array([side * 0.45 * mouth_w, -0.1 * mouth_w, 0.55 * mouth_w])
    d = np.linalg.norm(P - cheek, axis=1)
    w = np.clip(1 - d / (0.7 * mouth_w), 0, 1) ** 2
    w *= (P[:, 1] < cheek[1] + 0.02)
    disp[:, 2] += w * 0.07 * mouth_w
    disp[:, 1] -= w * 0.035 * mouth_w
# Smiling eyes: the lower lid rises a little (a squint), from the lid landmarks.
for name in ("lidL", "lidR"):
    if name not in lm:
        continue
    lid = np.array(lm[name]["world"])
    d = np.linalg.norm(P - lid, axis=1)
    w = np.clip(1 - d / (0.45 * mouth_w), 0, 1) ** 2
    w *= (P[:, 1] < lid[1] + 0.01) * (P[:, 2] < lid[2] + 0.002)   # the lid and below, not the eyeball top
    disp[:, 2] += w * 0.045 * mouth_w
print("moved verts", int((np.linalg.norm(disp, axis=1) > 1e-5).sum()))

mesh.shape_key_add(name="Basis")
key = mesh.shape_key_add(name="smile")
key.data.foreach_set("co", (P + disp).astype(np.float32).ravel())

scene = bpy.context.scene
try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError:
    scene.render.engine = "BLENDER_EEVEE"
world = bpy.data.worlds.new("w")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.95, 0.88, 0.85, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.7
scene.world = world
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
sun.data.energy, sun.data.color = 4.5, (1.0, 0.93, 0.86)
sun.rotation_euler = (math.radians(50), 0, math.radians(-30))
scene.collection.objects.link(sun)
scene.view_settings.view_transform = "AgX"
try:
    scene.view_settings.look = "AgX - Punchy"
except TypeError:
    pass
camo = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
camo.data.type = "ORTHO"
camo.data.ortho_scale = 0.11 * h
camo.location = (cam["cx"], -5, cam["cz"] - 0.03 * h)
camo.rotation_euler = (math.radians(90), 0, 0)
scene.collection.objects.link(camo)
scene.camera = camo
scene.render.resolution_x = scene.render.resolution_y = 1000
for v in (0.0, 0.8):
    key.value = v
    scene.render.filepath = str(rdir / f"smile_{int(v * 100):03d}.png")
    bpy.ops.render.render(write_still=True)
key.value = 0.0

# Back to Tripo's frame and export with the morph target.
mesh.data.transform(Matrix.Translation(-shift))
for kb in mesh.data.shape_keys.key_blocks:
    arr = np.empty(n * 3, dtype=np.float32)
    kb.data.foreach_get("co", arr)
    arr = arr.reshape(-1, 3) - shift
    kb.data.foreach_set("co", arr.ravel())
if TURN:
    mesh.data.transform(Matrix.Rotation(math.radians(-TURN), 4, "Z"))
for o in bpy.data.objects:
    o.select_set(o == mesh)
bpy.ops.export_scene.gltf(filepath=str(out_glb), export_format="GLB", use_selection=True,
                          export_morph=True)
print("done", out_glb)

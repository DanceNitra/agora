"""Photo-like views of a Tripo head from several yaw angles, for KeenTools FaceBuilder.

  TURN_DEG=-90 ./blender_headless.sh head_views.py -- <model.glb> <out_dir>

A perspective camera with an 85 mm lens (35 mm film) orbits the head at eye height, so every view
is the same 3D head: the views agree with each other exactly. Soft, even light, no shadows across
the face. Writes 1536 x 1536 PNGs named by angle, plus camera.txt with the lens for FaceBuilder.
"""
import math
import os
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

args = sys.argv[sys.argv.index("--") + 1:]
src, out = Path(args[0]).resolve(), Path(args[1]).resolve()
out.mkdir(parents=True, exist_ok=True)
TURN = float(os.environ.get("TURN_DEG", "0"))
LENS = 85.0
ANGLES = [("02_left45", 45), ("03_left90", 90), ("04_right45", -45), ("05_right90", -90), ("00_front_tripo", 0)]

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
h = hi[2] - lo[2]
shift = np.array([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]])
mesh.data.transform(Matrix.Translation(shift))
P = P + shift
band = P[(P[:, 2] > 0.84 * h) & (P[:, 2] < 0.93 * h)]
nose = band[np.argmin(band[:, 1])]
# Head centre: behind the nose by about half a head depth, at eye height.
# The front-most point of the band was the bangs tip (z 1.627 on Yuki H3.1), about 6 cm above
# the real nose, so the centre goes down by that much.
head = Vector((nose[0], nose[1] + 0.095, nose[2] - 0.05))
print("NOSE", nose.round(3).tolist(), "HEAD", [round(v, 3) for v in head])

scene = bpy.context.scene
try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError:
    scene.render.engine = "BLENDER_EEVEE"
RES = int(os.environ.get("RES", "1536"))
scene.render.resolution_x = scene.render.resolution_y = RES
scene.view_settings.view_transform = "Standard"
world = bpy.data.worlds.new("w")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.78, 0.78, 0.8, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.55
scene.world = world
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
cam.data.lens = LENS
scene.collection.objects.link(cam)
scene.camera = cam
# A soft key that follows the camera, so each view is lit from the front.
key = bpy.data.objects.new("key", bpy.data.lights.new("key", "AREA"))
key.data.energy, key.data.size = 9, 1.2   # 60 W burned the hair and skin to white
scene.collection.objects.link(key)

dist = 0.85   # metres: the head fills about 60 % of the frame at 85 mm
for name, yaw in ANGLES:
    a = math.radians(yaw)
    # Front is -Y. A positive yaw shows her left side: the camera moves toward +X... her left is
    # the viewer's right in the front view, so the camera goes to -X for her left.
    pos = Vector((head.x - math.sin(a) * dist, head.y - math.cos(a) * dist, head.z))
    cam.location = pos
    cam.rotation_euler = (head - pos).to_track_quat("-Z", "Y").to_euler()
    key.location = pos + Vector((0, 0, 0.25))
    key.rotation_euler = (head - key.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(out / f"{name}.png")
    bpy.ops.render.render(write_still=True)
(out / "camera.txt").write_text(
    f"All Tripo views: focal length {LENS} mm (35 mm full frame equivalent), sensor 36 mm, distance "
    f"{dist} m from the head centre, yaw angles " + ", ".join(f"{nm} {yw}" for nm, yw in ANGLES) + ".\n")
print("done")

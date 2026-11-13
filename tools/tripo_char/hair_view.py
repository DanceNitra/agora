"""Front, side and back renders of HairDeck hair GLBs (with the head proxy), one row per file.

    ./blender_headless.sh hair_view.py -- <out_dir> <hair1.glb> [<hair2.glb> ...]

HairDeck writes per-card colours; the renders use them as they come. Camera framing is taken from each file's bounds.
"""
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
out = Path(args[0]).resolve()
out.mkdir(parents=True, exist_ok=True)
for f in args[1:]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(Path(f).resolve()))
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    bpy.context.view_layer.update()
    P = np.concatenate([np.array([o.matrix_world @ v.co for v in o.data.vertices]) for o in meshes])
    lo, hi = P.min(0), P.max(0)
    c = (lo + hi) / 2
    size = float(max(hi - lo))
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = scene.render.resolution_y = 700
    scene.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("w")
    world.color = (0.75, 0.75, 0.75)
    scene.world = world
    for name, rot, e in (("key", (50, 0, -30), 3.0), ("fill", (60, 0, 150), 1.5)):
        L = bpy.data.objects.new(name, bpy.data.lights.new(name, "SUN"))
        L.data.energy = e
        L.rotation_euler = [math.radians(a) for a in rot]
        scene.collection.objects.link(L)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = size * 1.1
    scene.collection.objects.link(cam)
    scene.camera = cam
    # glTF is Y-up and faces +Z; after import Blender has Z up and the model facing -Y
    for tag, yaw in (("front", 0), ("side", 90), ("back", 180)):
        a = math.radians(yaw)
        cam.location = Vector((c[0] + 5 * math.sin(a), c[1] - 5 * math.cos(a), c[2]))
        cam.rotation_euler = (math.pi / 2, 0, a)
        scene.render.filepath = str(out / f"{Path(f).parent.name}_{Path(f).stem}_{tag}.png")
        bpy.ops.render.render(write_still=True)
print("DONE", out, flush=True)

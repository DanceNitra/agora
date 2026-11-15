"""Find face landmarks on a Tripo model's texture: render pixel -> ray -> surface -> UV.

  TURN_DEG=-90 ./blender_headless.sh texture_landmarks.py -- <model.glb> <work_dir> name:px:py ...

Uses work_dir/camera.json from face_project.py render (same framing). Writes landmarks.json with
the UV of each point and saves the base colour texture as base_color.png.
"""
import json
import math
import os
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

args = sys.argv[sys.argv.index("--") + 1:]
src, work = Path(args[0]).resolve(), Path(args[1]).resolve()
points = [(a.split(":")[0], float(a.split(":")[1]), float(a.split(":")[2])) for a in args[2:]]
cam = json.loads((work / "camera.json").read_text())
TURN = float(os.environ.get("TURN_DEG", "0"))

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
mesh.data.transform(Matrix.Translation((-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2])))
mesh.data.update()

me = mesh.data
me.calc_loop_triangles()
uv = me.uv_layers.active.data
bvh_scene = bpy.context.evaluated_depsgraph_get()
s, R = cam["scale"], cam["res"]
out = {}
for name, px, py in points:
    x = cam["cx"] + (px - R / 2) / R * s
    z = cam["cz"] - (py - R / 2) / R * s
    hit, loc, normal, face, obj, _ = bpy.context.scene.ray_cast(bvh_scene, Vector((x, -5, z)), Vector((0, 1, 0)))
    if not hit:
        print("MISS", name)
        continue
    poly = me.polygons[face]
    # Barycentric UV over the polygon's triangles: pick the triangle containing the hit.
    best = None
    for tri in me.loop_triangles:
        if tri.polygon_index != face:
            continue
        a, b, c = (me.vertices[i].co for i in tri.vertices)
        v0, v1, v2 = b - a, c - a, loc - a
        d00, d01, d11 = v0.dot(v0), v0.dot(v1), v1.dot(v1)
        d20, d21 = v2.dot(v0), v2.dot(v1)
        den = d00 * d11 - d01 * d01
        if den == 0:
            continue
        w1 = (d11 * d20 - d01 * d21) / den
        w2 = (d00 * d21 - d01 * d20) / den
        w0 = 1 - w1 - w2
        err = min(w0, w1, w2)
        if best is None or err > best[0]:
            uvs = [uv[li].uv for li in tri.loops]
            best = (err, w0 * uvs[0] + w1 * uvs[1] + w2 * uvs[2])
    out[name] = {"uv": [best[1][0], best[1][1]], "world": list(loc)}
    print("LM", name, [round(t, 4) for t in best[1]])

mat = me.materials[0]
bsdf = next(nd for nd in mat.node_tree.nodes if nd.type == "BSDF_PRINCIPLED")
img = bsdf.inputs["Base Color"].links[0].from_node.image
img.filepath_raw = str(work / "base_color.png")
img.file_format = "PNG"
img.save()
out["texture_size"] = list(img.size)
(work / "landmarks.json").write_text(json.dumps(out, indent=2))
print("done")

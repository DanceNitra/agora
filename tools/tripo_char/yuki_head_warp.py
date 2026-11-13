"""Render the conform target head of Yuki from the front, or warp it in its front plane by a landmark field.

    ./blender_headless.sh yuki_head_warp.py -- render <head_dir> <out_dir>
    ./blender_headless.sh yuki_head_warp.py -- warp   <head_dir> <field.json> <out_dir>

<head_dir> is a folder written by yuki_bald_prep.py (yuki_head.fbx, textures, yuki_head.clean.json). The head faces -Y.
render: writes front.png (orthographic, flat textured) and maps.json (camera), the inputs of yuki_warp_field.py.
warp:   moves every vertex in x and z by a smoothed thin-plate spline through the field's control points. The move
        fades out with depth behind the face (no move from the ears back) and is pinned to zero on a ring around the
        face, so the skull, ears and neck stay. Writes a new head folder in the same layout (yuki_head.fbx, portrait,
        yuki_head.clean.json) plus front.png and maps.json of the warped head, ready for ue_conform_yuki.py.
"""
import json
import math
import shutil
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix

args = sys.argv[sys.argv.index("--") + 1:]
mode, src = args[0], Path(args[1]).resolve()
out = Path(args[-1]).resolve()
out.mkdir(parents=True, exist_ok=True)
RES, ORTHO = 1400, 0.30
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(src / "yuki_head.fbx"))
obj = max((o for o in bpy.data.objects if o.type == "MESH"), key=lambda o: len(o.data.vertices))
bpy.context.view_layer.update()
mw = obj.matrix_world.copy()
obj.parent = None
obj.matrix_world = Matrix.Identity(4)
obj.data.transform(mw)
for o in list(bpy.data.objects):
    if o is not obj:
        bpy.data.objects.remove(o)
me = obj.data
V = np.array([v.co[:] for v in me.vertices])
print("HEAD verts", len(V), "bbox", V.min(0).round(3).tolist(), V.max(0).round(3).tolist(),
      "images", [(i.name, i.size[0]) for i in bpy.data.images], flush=True)
rep = json.loads((src / "yuki_head.clean.json").read_text())

if mode == "warp":
    f = json.loads(Path(args[2]).read_text())
    P, M = np.array(f["points_xz_m"]), np.array(f["moves_xz_m"])
    s = f["iod_m"]
    c = P.mean(0)
    ring_r = np.linalg.norm(P - c, axis=1).max() * 1.45
    ang = np.linspace(0, 2 * np.pi, 28, endpoint=False)
    ring = c + ring_r * np.stack([np.cos(ang), np.sin(ang)], 1)
    Pc, Mc = np.vstack([P, ring]) / s, np.vstack([M, np.zeros((len(ring), 2))])

    def U(d):
        return np.where(d > 0, d * d * np.log(np.maximum(d, 1e-12)), 0.0)

    n = len(Pc)
    LAM = float(f.get("lambda", 0.02))
    K = U(np.linalg.norm(Pc[:, None] - Pc[None], axis=2)) + LAM * np.eye(n)
    Pm = np.hstack([np.ones((n, 1)), Pc])
    A = np.zeros((n + 3, n + 3))
    A[:n, :n], A[:n, n:], A[n:, :n] = K, Pm, Pm.T
    coef = np.linalg.solve(A, np.vstack([Mc, np.zeros((3, 2))]))
    Q = V[:, [0, 2]] / s
    mv = np.zeros((len(V), 2))
    for i in range(0, len(V), 20000):
        q = Q[i:i + 20000]
        mv[i:i + 20000] = U(np.linalg.norm(q[:, None] - Pc[None], axis=2)) @ coef[:n] + np.hstack([np.ones((len(q), 1)), q]) @ coef[n:]
    depth = V[:, 1] - V[:, 1].min()                      # 0 at the nose tip, growing towards the back of the head
    t = np.clip((depth - 0.065) / 0.045, 0, 1)
    w = 1 - t * t * (3 - 2 * t)
    r = np.linalg.norm(V[:, [0, 2]] - c, axis=1) / ring_r
    t2 = np.clip((r - 0.8) / 0.2, 0, 1)
    w *= 1 - t2 * t2 * (3 - 2 * t2)
    mv *= w[:, None]
    V[:, 0] += mv[:, 0]
    V[:, 2] += mv[:, 1]
    me.vertices.foreach_set("co", V.ravel())
    me.update()
    fit = (U(np.linalg.norm(Pc[:len(P), None] - Pc[None], axis=2)) @ coef[:n] + Pm[:len(P)] @ coef[n:])
    print("WARP control residual mm mean", round(float(np.linalg.norm(fit - M, axis=1).mean() * 1000), 3),
          "vertex move mm mean", round(float(np.linalg.norm(mv, axis=1)[w > 0.5].mean() * 1000), 2), "max", round(float(np.linalg.norm(mv, axis=1).max() * 1000), 2), flush=True)
    obj.name = me.name = "yuki_head"
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(out / "yuki_head.fbx"), use_selection=True, object_types={"MESH"},
                             apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE", path_mode="COPY",
                             embed_textures=False, add_leaf_bones=False)
    (out / "yuki_head.clean.json").write_text(json.dumps(rep, indent=2))

scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "FLAT"
scene.display.shading.color_type = "TEXTURE"
scene.view_settings.view_transform = "Standard"
world = bpy.data.worlds.new("w")
world.color = (0.5, 0.5, 0.5)
scene.world = world
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
scene.collection.objects.link(cam)
scene.camera = cam
if mode == "warp":                                       # the portrait the face tracker reads, same camera as the prep
    cu = rep["camera_unreal"]
    cam.data.sensor_fit = "HORIZONTAL"
    cam.data.angle = math.radians(cu["fov_deg"])
    cam.location = (0.0, -cu["location_cm"][1] / 100, cu["location_cm"][2] / 100)
    cam.rotation_euler = (math.pi / 2, 0.0, 0.0)
    scene.render.resolution_x, scene.render.resolution_y = cu["image_px"]
    scene.render.filepath = str(out / cu["portrait"])
    bpy.ops.render.render(write_still=True)
cx, cz = float((V[:, 0].max() + V[:, 0].min()) / 2), float(V[:, 2].max() - 0.12)
cam.data.type = "ORTHO"
cam.data.ortho_scale = ORTHO
cam.location = (cx, -2.0, cz)
cam.rotation_euler = (math.pi / 2, 0, 0)
scene.render.resolution_x = scene.render.resolution_y = RES
scene.render.filepath = str(out / "front.png")
bpy.ops.render.render(write_still=True)
(out / "maps.json").write_text(json.dumps({"cx": cx, "cz": cz, "ortho": ORTHO, "res": RES, "front_axis": "-Y"}, indent=1))
print("DONE", mode, out, flush=True)

"""Prepare the HD bald Tripo head of Yuki for MetaHuman's head-only conform.

    ./blender_headless.sh yuki_bald_prep.py -- <model.glb> <out_dir>

Tripo returned a bust 1.6 units tall facing +X (auto_size took it for a whole object). It is turned to face -Y and
scaled so that crown to chin is CHIN_CROWN_M (default 0.215 m, an adult woman). The chin is found on the midline
profile: below the nose, the lowest point that still lies within 25 % of the head depth of the face front; under it
the profile falls back to the neck. Everything lower than NECK_CM below the chin is cut off (shoulders, tank top).
Writes yuki_head.fbx (centimetres), its texture, a textured front portrait for the face tracker, a side check render
with the chin and crown marked, and yuki_head.clean.json with the camera in Unreal axes.
"""
import json
import math
import os
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

src, out = Path(sys.argv[-2]).resolve(), Path(sys.argv[-1]).resolve()
out.mkdir(parents=True, exist_ok=True)
CHIN_CROWN = float(os.environ.get("CHIN_CROWN_M", 0.215))
NECK = float(os.environ.get("NECK_CM", 7)) / 100
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(src))
objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
obj = max(objs, key=lambda o: len(o.data.vertices))
for o in objs:
    if o is not obj:
        bpy.data.objects.remove(o)
obj.data.transform(obj.matrix_world)
obj.parent = None
obj.matrix_world = Matrix.Identity(4)
me = obj.data
me.transform(Matrix.Rotation(-math.pi / 2, 4, "Z"))  # +X front -> -Y front (measured: the face is +X)
P = np.array([v.co[:] for v in me.vertices])
crown = float(P[:, 2].max())
# midline profile: forward-most point (min y) per height slice
mid = P[np.abs(P[:, 0] - np.median(P[P[:, 2] > crown - 0.3 * np.ptp(P[:, 2]), 0])) < 0.01 * np.ptp(P[:, 2])]
zs = np.linspace(crown, P[:, 2].min(), 400)
front = np.array([mid[np.abs(mid[:, 2] - z) < np.ptp(P[:, 2]) / 400, 1].min() if (np.abs(mid[:, 2] - z) < np.ptp(P[:, 2]) / 400).any() else np.nan for z in zs])
upper = zs > crown - 0.45 * np.ptp(P[:, 2])
nose_i = int(np.nanargmin(np.where(upper, front, np.nan)))
depth = float(np.ptp(P[P[:, 2] > zs[nose_i], 1]))
chin_i = nose_i
for i in range(nose_i, len(zs)):
    if np.isnan(front[i]):
        continue
    if front[i] - front[nose_i] > 0.25 * depth:
        break
    chin_i = i
chin = float(zs[chin_i])
s = CHIN_CROWN / (crown - chin)
me.transform(Matrix.Scale(s, 4))
P = P * s
chin, crown = chin * s, crown * s
# cut below the neck
bm = bmesh.new()
bm.from_mesh(me)
bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.calc_center_median().z < chin - NECK], context="FACES")
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
bm.to_mesh(me)
bm.free()
P = np.array([v.co[:] for v in me.vertices])
cx, cy = (P[:, 0].max() + P[:, 0].min()) / 2, (P[:, 1].max() + P[:, 1].min()) / 2
# place the head at a standing woman's height: chin at 1.45 m
me.transform(Matrix.Translation((-cx, -cy, 1.45 - chin)))
crown, chin = crown + 1.45 - chin, 1.45
me.update()
# 1.37 M faces is far more than the conform needs; decimate to about TARGET_FACES, keeping the UVs
target = int(os.environ.get("TARGET_FACES", 200000))
if len(me.polygons) > target:
    bpy.context.view_layer.objects.active = obj
    md = obj.modifiers.new("dec", "DECIMATE")
    md.ratio = target / len(me.polygons)
    bpy.ops.object.modifier_apply(modifier="dec")
obj.name = me.name = "yuki_head"
for img in bpy.data.images:
    if img.size[0]:
        img.filepath_raw = str(out / f"yuki_head_{img.name.split('_')[0]}.png")
        img.file_format = "PNG"
        img.save()
bpy.ops.object.select_all(action="DESELECT")
obj.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(out / "yuki_head.fbx"), use_selection=True, object_types={"MESH"},
                         apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE", path_mode="COPY",
                         embed_textures=False, add_leaf_bones=False)

scene = bpy.context.scene
FOV, DIST, PX = 20.0, 1.15, 1024
face_z = chin + 0.45 * CHIN_CROWN
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
cam.data.sensor_fit = "HORIZONTAL"
cam.data.angle = math.radians(FOV)
scene.collection.objects.link(cam)
scene.camera = cam
cam.location = (0.0, -DIST, face_z)
cam.rotation_euler = (math.pi / 2, 0.0, 0.0)
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "FLAT"
scene.display.shading.color_type = "TEXTURE"
scene.render.resolution_x = scene.render.resolution_y = PX
scene.view_settings.view_transform = "Standard"
world = bpy.data.worlds.new("w")
world.color = (0.5, 0.5, 0.5)
scene.world = world
scene.render.filepath = str(out / "yuki_head_portrait.png")
bpy.ops.render.render(write_still=True)
# side check with chin and crown lines
cam.data.type = "ORTHO"
cam.data.ortho_scale = 0.4
cam.location = (DIST, 0.0, chin + 0.08)
cam.rotation_euler = (math.pi / 2, 0.0, math.pi / 2)
for z, nm in ((chin, "chin"), (crown, "crown")):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, z))
    bpy.context.object.scale = (0.001, 0.4, 0.001)
    bpy.context.object.name = nm
scene.display.shading.color_type = "OBJECT"
scene.render.filepath = str(out / "yuki_head_side_check.png")
bpy.ops.render.render(write_still=True)
rep = {"scale": round(s, 5), "crown_m": round(crown, 4), "chin_m": round(chin, 4), "head_depth_m": round(depth * s, 4),
       "vertices": len(me.vertices), "faces": len(me.polygons),
       "camera_unreal": {"location_cm": [0.0, DIST * 100, face_z * 100], "rotation_pitch_yaw_roll": [0.0, -90.0, 0.0],
                         "fov_deg": FOV, "image_px": [PX, PX], "portrait": "yuki_head_portrait.png"}}
(out / "yuki_head.clean.json").write_text(json.dumps(rep, indent=2))
print("PREP", json.dumps(rep), flush=True)

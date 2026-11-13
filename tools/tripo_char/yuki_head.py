"""Cut the skin of the head out of a Tripo character for MetaHuman Creator's head-only conform.

    ./blender_headless.sh yuki_head.py -- <model.glb> <out_dir>

Yuki's hair covers the forehead and the sides of the face, and her cat ears sit on the hair. Hair and ears fitted as
head shape would swell the skull, as clothing swelled the body of hero 01. So only the skin is kept: faces of the head
whose texture is not hair-coloured, in the connected piece that holds the nose. Writes the head FBX (centimetres,
facing -Y), a textured front portrait for the face tracker, a mask render, and the camera in Unreal axes.
"""
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix

src, out = Path(sys.argv[-2]).resolve(), Path(sys.argv[-1]).resolve()
out.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(src))
objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
obj = max(objs, key=lambda o: len(o.data.vertices))
for o in objs:
    if o is not obj:
        bpy.data.objects.remove(o)
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
obj.parent = None

# Face -Y with feet on the floor, as clean_body.py does: Tripo exports the character facing +X.
me = obj.data
P = np.array([v.co[:] for v in me.vertices])
if np.ptp(P[:, 1]) > np.ptp(P[:, 0]):
    me.transform(Matrix.Rotation(-math.pi / 2, 4, "Z"))
P = np.array([v.co[:] for v in me.vertices])
me.transform(Matrix.Translation((-(P[:, 0].max() + P[:, 0].min()) / 2, -(P[:, 1].max() + P[:, 1].min()) / 2, -P[:, 2].min())))
P = np.array([v.co[:] for v in me.vertices])
H = float(P[:, 2].max())

# Base colour per face from the texture at the face's UV centre.
img = next(n.image for m in me.materials if m and m.use_nodes for n in m.node_tree.nodes
           if n.type == "TEX_IMAGE" and n.image and n.image.size[0] and "base" in n.image.name.lower()) \
    if any(n.type == "TEX_IMAGE" and n.image and "base" in n.image.name.lower() for m in me.materials if m and m.use_nodes for n in m.node_tree.nodes) \
    else next(n.image for m in me.materials if m and m.use_nodes for n in m.node_tree.nodes if n.type == "TEX_IMAGE" and n.image and n.image.size[0])
W, Hh = img.size
px = np.array(img.pixels[:], dtype=np.float32).reshape(Hh, W, 4)[..., :3]
uv = np.zeros((len(me.loops), 2))
me.uv_layers.active.data.foreach_get("uv", uv.ravel())
lf = np.zeros(len(me.loops), dtype=np.int64)
for p in me.polygons:
    lf[p.loop_start:p.loop_start + p.loop_total] = p.index
nf = len(me.polygons)
cnt = np.bincount(lf, minlength=nf)
fu = np.bincount(lf, uv[:, 0] % 1, nf) / cnt
fv = np.bincount(lf, uv[:, 1] % 1, nf) / cnt
col = px[np.clip((fv * Hh).astype(int), 0, Hh - 1), np.clip((fu * W).astype(int), 0, W - 1)]
fc = np.array([p.center[:] for p in me.polygons])

# Head: above the neck. The chin sits about 0.13 of the height below the crown on this figure (measured below).
nose_i = int(np.argmin(np.where((fc[:, 2] > H - 0.2) & (np.abs(fc[:, 0]) < 0.03), fc[:, 1], 9)))
nose = fc[nose_i]
neck_z = nose[2] - 0.20
head = fc[:, 2] > neck_z
r, g, b = col[:, 0], col[:, 1], col[:, 2]
# Pink and lavender hair and ears: blue at or above green and well above it relative to red-green skin. Skin, lips,
# blush and brows keep green above blue. Lashes and irises are dark or orange and pass as non-hair.

# Colour cannot separate them: the graded texture tints hair and skin alike (nose b-g 0.008, fringe 0.012, measured).
# So the face is taken by what the front camera sees inside an oval from the brows to the chin: the fringe ends above
# the brows and the side strands lie outside the cheeks. The skull and the hidden forehead are left to the solver.
from mathutils.bvhtree import BVHTree
OVAL_W = 0.056  # half-width of the face oval in metres, inside the side strands
from mathutils import Vector as _V
bvh = BVHTree.FromPolygons([v.co.copy() for v in me.vertices], [tuple(p.vertices) for p in me.polygons])
camp = _V((float(nose[0]), -1.15, float(nose[2])))
hit = set()
rel = fc - nose
# `nose` is the front-most point of the head, which is the fringe about 5 cm above the eyes (measured on the portrait:
# eyes 5 cm, brows 3.2 cm, mouth 12.6 cm, chin 15.4 cm below it). The oval runs from just under the fringe to the chin.
cand = np.nonzero(head & ((rel[:, 0] / OVAL_W) ** 2 + ((rel[:, 2] + 0.093) / 0.064) ** 2 <= 1.0) & (rel[:, 1] < 0.08))[0]
for fi_ in cand:
    c = _V(fc[fi_])
    d = c - camp
    loc, nrm, fi, dist = bvh.ray_cast(camp, d.normalized(), d.length + 0.01)
    if fi is not None and (fi == fi_ or abs(dist - d.length) < 0.0015):  # nothing in front of this face
        hit.add(int(fi_))
hair = np.zeros(nf, bool)
keep = np.zeros(nf, bool)
keep[list(hit)] = True
stats = {"faces": nf, "head_faces": int(head.sum()), "hair_in_head": int((head & hair).sum()), "kept": int(keep.sum()),
         "nose_m": [round(float(x), 4) for x in nose], "neck_z_m": round(float(neck_z), 4), "height_m": round(H, 4),
         "texture": img.name, "texture_px": [W, Hh],
         "skin_b_minus_g_p10_50_90": [round(float(x), 3) for x in np.percentile((b - g)[keep], [10, 50, 90])],
         "hair_b_minus_g_p10_50_90": [round(float(x), 3) for x in np.percentile((b - g)[head & hair], [10, 50, 90])] if (head & hair).any() else None}

FOV_DEG, DIST_M, PX = 20.0, 1.15, 1024
scene = bpy.context.scene
for m in me.materials:
    if m and m.use_nodes:
        t = next((n for n in m.node_tree.nodes if n.type == "TEX_IMAGE" and n.image is img), None)
        if t:
            m.node_tree.nodes.active = t  # Workbench shows the active image node's texture
cam_data = bpy.data.cameras.new("portrait")
cam_data.sensor_fit = "HORIZONTAL"
cam = bpy.data.objects.new("portrait", cam_data)
scene.collection.objects.link(cam)
# The face is not at the bounding-box centre (tail and hair skew it), so the camera looks straight at the nose.
cam.location = (float(nose[0]), -DIST_M, float(nose[2]) - 0.08)
cam.rotation_euler = (math.pi / 2, 0.0, 0.0)
scene.camera = cam
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "FLAT"
scene.display.shading.color_type = "TEXTURE"
scene.render.resolution_x = scene.render.resolution_y = PX
scene.view_settings.view_transform = "Standard"
world = bpy.data.worlds.new("w")
world.color = (0.5, 0.5, 0.5)
scene.world = world


def shot(name, fov):
    cam_data.angle = math.radians(fov)
    scene.render.filepath = str(out / name)
    bpy.ops.render.render(write_still=True)


shot("yuki_full_portrait.png", FOV_DEG)
shot("yuki_full_close.png", 8.0)
bm = bmesh.new()
bm.from_mesh(me)
bm.faces.ensure_lookup_table()
bmesh.ops.delete(bm, geom=[f for f in bm.faces if not keep[f.index]], context="FACES")
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
bm.faces.ensure_lookup_table()
# keep the connected piece that holds the nose; by shared vertex, so a pinched lid stays attached
from mathutils import Vector
nv = Vector(nose)
nv = Vector((nose[0], nose[1], nose[2] - 0.09))  # middle of the face oval
seed = min(bm.faces, key=lambda f: (f.calc_center_median() - nv).length)
seen, stack = {seed}, [seed]
while stack:
    f = stack.pop()
    for v in f.verts:
        for g_ in v.link_faces:
            if g_ not in seen:
                seen.add(g_)
                stack.append(g_)
drop = [f for f in bm.faces if f not in seen]
stats["dropped_islands_faces"] = len(drop)
bmesh.ops.delete(bm, geom=drop, context="FACES")
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
stats["boundary_edges"] = sum(1 for e in bm.edges if e.is_boundary)
bm.to_mesh(me)
bm.free()
me.update()
stats["out_vertices"] = len(me.vertices)
stats["out_faces"] = len(me.polygons)
obj.name = me.name = "yuki_head"

img.filepath_raw = str(out / "yuki_head_BaseColor.png")
img.file_format = "PNG"
img.save()
bpy.ops.export_scene.fbx(filepath=str(out / "yuki_head.fbx"), use_selection=True, object_types={"MESH"},
                         apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE", path_mode="COPY",
                         embed_textures=False, add_leaf_bones=False)

shot("yuki_head_portrait.png", FOV_DEG)
shot("yuki_head_close.png", 8.0)
camera = {"location_cm": [float(nose[0]) * 100, DIST_M * 100, (float(nose[2]) - 0.08) * 100], "rotation_pitch_yaw_roll": [0.0, -90.0, 0.0],
          "fov_deg": FOV_DEG, "image_px": [PX, PX], "portrait": "yuki_full_portrait.png", "portrait_cut": "yuki_head_portrait.png"}
rep = {"source": src.name, "camera_unreal": camera, "cut": stats}
(out / "yuki_head.clean.json").write_text(json.dumps(rep, indent=2))
print("HEAD", json.dumps(rep), flush=True)

"""Position and normal maps of the MetaHuman head in its own skin UV layout, and a front render for landmarks.

    ./blender_headless.sh yuki_concept_maps.py -- <mh_head.fbx> <skin_tex.png> <out_dir> [size]

The head stays in its own frame (front is -Y, Z up, metres). Writes:
  front.png      orthographic front render, skin wearing <skin_tex.png>, simple eyeballs, for the face landmarker
  pos.npy        (size, size, 3) float32 world position per skin texel, row 0 at the top of the image
  nrm.npy        (size, size, 3) float32 smooth normal per skin texel
  cov.npy        (size, size) bool, True where a skin face covers the texel
  maps.json      camera of front.png: centre x and z, ortho scale in metres, resolution in pixels
yuki_concept_face.py uses these to carry the concept picture onto the texture without a second mesh.
"""
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

args = sys.argv[sys.argv.index("--") + 1:]
mh_p, tex_p, out = args[0], args[1], Path(args[2]).resolve()
SIZE = int(args[3]) if len(args) > 3 else 2048
RES, ORTHO = 1400, 0.30
out.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(Path(mh_p).resolve()))
mh = max((o for o in bpy.data.objects if o.type == "MESH"), key=lambda o: len(o.data.vertices))
for md in list(mh.modifiers):
    mh.modifiers.remove(md)
bpy.context.view_layer.update()
mw = mh.matrix_world.copy()
mh.parent = None
mh.matrix_world = Matrix.Identity(4)
mh.data.transform(mw)
for o in list(bpy.data.objects):
    if o is not mh:
        bpy.data.objects.remove(o)
names = [s.material.name if s.material else "" for s in mh.material_slots]
counts = np.bincount([p.material_index for p in mh.data.polygons], minlength=len(names))
skin_i = int(np.argmax(counts))
print("SLOTS", list(zip(names, counts.tolist())), "skin", skin_i, flush=True)


def delete_faces(pred):
    bpy.context.view_layer.objects.active = mh
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.object.mode_set(mode="OBJECT")
    for p in mh.data.polygons:
        p.select = pred(p.material_index)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.delete(type="FACE")
    bpy.ops.object.mode_set(mode="OBJECT")


# eye shell, lashes, eye edge and saliva are see-through in Unreal; here they would cover the eyes
hide = {i for i, n in enumerate(names) if any(k in n for k in ("eyeshell", "eyelashes", "eyeEdge", "saliva"))}
delete_faces(lambda i: i in hide)
eye = bpy.data.images.new("eye", 256, 256)
yy, xx = np.mgrid[0:256, 0:256]
r = np.hypot(xx - 127.5, yy - 127.5) / 128
e = np.ones((256, 256, 4), np.float32)
e[r < 0.30] = (0.45, 0.25, 0.05, 1)
e[r < 0.12] = (0, 0, 0, 1)
eye.pixels = e.ravel()
skin_img = bpy.data.images.load(str(Path(tex_p).resolve()))
for i, s in enumerate(mh.material_slots):
    m = bpy.data.materials.new(f"m{i}")
    m.use_nodes = True
    t = m.node_tree.nodes.new("ShaderNodeTexImage")
    t.image = skin_img if i == skin_i else eye if "eye" in names[i] else None
    m.node_tree.nodes.active = t
    if t.image:
        m.node_tree.links.new(t.outputs["Color"], next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"])
    s.material = m
scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "FLAT"
scene.display.shading.color_type = "TEXTURE"
scene.render.resolution_x = scene.render.resolution_y = RES
scene.view_settings.view_transform = "Standard"
world = bpy.data.worlds.new("w")
world.color = (0.5, 0.5, 0.5)
scene.world = world
P = np.array([v.co[:] for v in mh.data.vertices])
cx, cz = float((P[:, 0].max() + P[:, 0].min()) / 2), float(P[:, 2].max() - 0.12)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
cam.data.type = "ORTHO"
cam.data.ortho_scale = ORTHO
scene.collection.objects.link(cam)
scene.camera = cam
cam.location = (cx, -2.0, cz)
cam.rotation_euler = (math.pi / 2, 0, 0)
scene.render.filepath = str(out / "front.png")
bpy.ops.render.render(write_still=True)
(out / "maps.json").write_text(json.dumps({"cx": cx, "cz": cz, "ortho": ORTHO, "res": RES, "size": SIZE, "front_axis": "-Y"}, indent=1))

# bake position and normal of the skin section into its UVs
delete_faces(lambda i: i != skin_i)
mh.data.uv_layers.active_index = 0
V = np.array([v.co[:] for v in mh.data.vertices])
lo, hi = V.min(0) - 0.01, V.max(0) + 0.01
scene.render.engine = "CYCLES"
scene.cycles.samples = 1
scene.cycles.device = "CPU"
bs = scene.render.bake
bs.use_selected_to_active = False
bs.margin = 0
bs.use_clear = True


def bake(name, build):
    img = bpy.data.images.new(name, SIZE, SIZE, alpha=True, float_buffer=True)
    img.colorspace_settings.name = "Non-Color"
    img.generated_color = (0, 0, 0, 0)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for nd in list(nt.nodes):
        if nd.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(nd)
    em = nt.nodes.new("ShaderNodeEmission")
    build(nt, em)
    nt.links.new(em.outputs[0], next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL").inputs["Surface"])
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = img
    nt.nodes.active = t
    mh.data.materials.clear()
    mh.data.materials.append(m)
    for p in mh.data.polygons:
        p.material_index = 0
    bpy.ops.object.select_all(action="DESELECT")
    mh.select_set(True)
    bpy.context.view_layer.objects.active = mh
    bpy.ops.object.bake(type="EMIT")
    return np.array(img.pixels[:], dtype=np.float32).reshape(SIZE, SIZE, 4)[::-1]


def pos_nodes(nt, em):
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sub = nt.nodes.new("ShaderNodeVectorMath")
    sub.operation = "SUBTRACT"
    sub.inputs[1].default_value = lo.tolist()
    div = nt.nodes.new("ShaderNodeVectorMath")
    div.operation = "DIVIDE"
    div.inputs[1].default_value = (hi - lo).tolist()
    nt.links.new(geo.outputs["Position"], sub.inputs[0])
    nt.links.new(sub.outputs[0], div.inputs[0])
    nt.links.new(div.outputs[0], em.inputs["Color"])


def nrm_nodes(nt, em):
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    mad = nt.nodes.new("ShaderNodeVectorMath")
    mad.operation = "MULTIPLY_ADD"
    mad.inputs[1].default_value = (0.5, 0.5, 0.5)
    mad.inputs[2].default_value = (0.5, 0.5, 0.5)
    nt.links.new(geo.outputs["Normal"], mad.inputs[0])
    nt.links.new(mad.outputs[0], em.inputs["Color"])


p = bake("pos", pos_nodes)
cov = p[..., 3] > 0.5
np.save(out / "pos.npy", (p[..., :3] * (hi - lo) + lo).astype(np.float32))
np.save(out / "cov.npy", cov)
n = bake("nrm", nrm_nodes)
np.save(out / "nrm.npy", (n[..., :3] * 2 - 1).astype(np.float32))
print("MAPS coverage", round(float(cov.mean()), 3), "pos range", lo.round(3).tolist(), hi.round(3).tolist(), flush=True)

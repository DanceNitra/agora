"""Paint the concept's face onto a Tripo model's base colour, so the face matches the picture.

Tripo's texture keeps the face shape but loses the make-up (eyeliner, lips, blush) and turns the
skin pale. This projects the front concept straight onto the face and bakes it into the base colour
texture through a soft mask; everything outside the mask keeps Tripo's texture.

  1. ./blender_headless.sh face_project.py -- render <model.glb> <work_dir>
     Front orthographic render of the face (unlit base colour) and the camera, in work_dir.
  2. align_face.py finds the similarity transform from that render to the concept (OpenCV ECC).
  3. ./blender_headless.sh face_project.py -- bake <model.glb> <work_dir> <concept.png> <out.glb>
     Projects, bakes and writes the model with the new texture.

TURN_DEG rotates the model about Z before anything (Yuki H3.1 faces +X: -90).
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
mode, src, work = args[0], Path(args[1]).resolve(), Path(args[2]).resolve()
work.mkdir(parents=True, exist_ok=True)
TURN = float(os.environ.get("TURN_DEG", "0"))
RES = 1024

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
mesh.data.transform(Matrix.Translation((-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2])))
mesh.data.vertices.foreach_get("co", co)
P = co.reshape(-1, 3)

# Face window: the nose is the front-most point of the head band; centre a little above it.
band = P[(P[:, 2] > 0.84 * h) & (P[:, 2] < 0.93 * h)]
nose = band[np.argmin(band[:, 1])]
cam_cfg = {"cx": float(nose[0]), "cz": float(nose[2] + 0.005 * h), "scale": 0.16 * h, "res": RES, "h": float(h)}

mat = mesh.data.materials[0]
nodes = mat.node_tree.nodes
bsdf = next(nd for nd in nodes if nd.type == "BSDF_PRINCIPLED")
base_link = bsdf.inputs["Base Color"].links[0]
base_tex = base_link.from_node   # the base colour image node
base_img = base_tex.image
print("BASE", base_img.name, tuple(base_img.size))

scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 1


def unlit_front_render(path: Path) -> None:
    """Base colour only, no light: what the projection will be compared against."""
    emit = nodes.new("ShaderNodeEmission")
    mat.node_tree.links.new(base_tex.outputs["Color"], emit.inputs["Color"])
    out = next(nd for nd in nodes if nd.type == "OUTPUT_MATERIAL")
    old = out.inputs["Surface"].links[0].from_socket
    mat.node_tree.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = cam_cfg["scale"]
    cam.location = (cam_cfg["cx"], -5, cam_cfg["cz"])
    cam.rotation_euler = (math.radians(90), 0, 0)
    scene.collection.objects.link(cam)
    scene.camera = cam
    scene.render.resolution_x = scene.render.resolution_y = RES
    scene.render.filepath = str(path)
    scene.view_settings.view_transform = "Standard"
    bpy.ops.render.render(write_still=True)
    mat.node_tree.links.new(old, out.inputs["Surface"])


if mode == "render":
    unlit_front_render(work / "face_render.png")
    (work / "camera.json").write_text(json.dumps(cam_cfg, indent=2))
    print("done render")
    sys.exit(0)

# ---- bake ----------------------------------------------------------------------------------
concept_path, out_glb = Path(args[3]).resolve(), Path(args[4]).resolve()
A = np.array(json.loads((work / "align.json").read_text())["render_to_concept"])   # 2x3
concept = bpy.data.images.load(str(concept_path))
cw, ch = concept.size

# Vertex -> render pixel (ortho, top-left origin) -> concept pixel -> UV in the concept image.
s, R = cam_cfg["scale"], RES
px = (P[:, 0] - cam_cfg["cx"]) / s * R + R / 2
py = -(P[:, 2] - cam_cfg["cz"]) / s * R + R / 2
cxy = (A @ np.vstack([px, py, np.ones(n)])).T
u, v = cxy[:, 0] / cw, 1 - cxy[:, 1] / ch

# Mask: an ellipse over brows-to-chin, faded at the rim, times "faces the camera".
nrm = np.empty(n * 3)
mesh.data.vertices.foreach_get("normal", nrm)
front = np.clip((-nrm.reshape(-1, 3)[:, 1] - 0.35) / 0.4, 0, 1)
ex = (P[:, 0] - cam_cfg["cx"]) / (0.042 * h)
ez = (P[:, 2] - (nose[2] - 0.006 * h)) / (0.052 * h)
r = np.sqrt(ex ** 2 + ez ** 2)
ell = np.clip((1.0 - r) / 0.35, 0, 1)
mask = (front * ell * (P[:, 1] < nose[1] + 0.07 * h)).astype(np.float32)
print("MASK verts > 0.5:", int((mask > 0.5).sum()))

# Per-loop UV and mask from the per-vertex values.
me = mesh.data
loops = np.empty(len(me.loops), dtype=np.int64)
me.loops.foreach_get("vertex_index", loops)
proj = me.uv_layers.new(name="proj")
proj.data.foreach_set("uv", np.column_stack([u[loops], v[loops]]).ravel().astype(np.float32))
attr = me.color_attributes.new(name="facemask", type="FLOAT_COLOR", domain="POINT")
attr.data.foreach_set("color", np.repeat(mask, 4).astype(np.float32))
orig_uv = next(l for l in me.uv_layers if l.name != "proj")
me.uv_layers.active = orig_uv
orig_uv.active_render = True

# Material for the bake: mix(original, concept via "proj", mask) -> emission.
uvn = nodes.new("ShaderNodeUVMap")
uvn.uv_map = "proj"
ctex = nodes.new("ShaderNodeTexImage")
ctex.image = concept
ctex.extension = "EXTEND"
mat.node_tree.links.new(uvn.outputs["UV"], ctex.inputs["Vector"])
attrn = nodes.new("ShaderNodeVertexColor")
attrn.layer_name = "facemask"
mix = nodes.new("ShaderNodeMix")
mix.data_type = "RGBA"
mat.node_tree.links.new(attrn.outputs["Color"], mix.inputs["Factor"])
mat.node_tree.links.new(base_tex.outputs["Color"], mix.inputs[6])
mat.node_tree.links.new(ctex.outputs["Color"], mix.inputs[7])
emit = nodes.new("ShaderNodeEmission")
mat.node_tree.links.new(mix.outputs[2], emit.inputs["Color"])
out = next(nd for nd in nodes if nd.type == "OUTPUT_MATERIAL")
old_surface = out.inputs["Surface"].links[0].from_socket
mat.node_tree.links.new(emit.outputs["Emission"], out.inputs["Surface"])

W, H = base_img.size
target = bpy.data.images.new("base_face", W, H, alpha=False)
tnode = nodes.new("ShaderNodeTexImage")
tnode.image = target
nodes.active = tnode
for o in bpy.data.objects:
    o.select_set(o == mesh)
bpy.context.view_layer.objects.active = mesh
scene.cycles.bake_type = "EMIT"
scene.render.bake.margin = 8
print("BAKING", W, H, flush=True)
bpy.ops.object.bake(type="EMIT")
target.filepath_raw = str(work / "base_face.png")
target.file_format = "PNG"
target.save()

# Put the new texture in place of the old base colour and restore the shader.
mat.node_tree.links.new(old_surface, out.inputs["Surface"])
base_tex.image = target
me.uv_layers.remove(me.uv_layers["proj"])
me.color_attributes.remove(me.color_attributes["facemask"])
for nd in (uvn, ctex, attrn, mix, emit, tnode):
    nodes.remove(nd)
if TURN:   # back to Tripo's own orientation, so downstream tools see the usual file
    mesh.data.transform(Matrix.Rotation(math.radians(-TURN), 4, "Z"))
bpy.ops.export_scene.gltf(filepath=str(out_glb), export_format="GLB", use_selection=True)
print("done bake", out_glb)

"""Bake the colour of Yuki's Tripo HD head onto the MetaHuman head's own UV layout.

    ./blender_headless.sh yuki_face_bake.py -- <mh_head.fbx> <tripo_head.fbx> <out_dir> [size]

The MetaHuman face was conformed to this Tripo head, so the two surfaces lie within about a millimetre around the
eyes and a few millimetres at the chin. A Cycles selected-to-active bake carries the painted face (liner, brows,
lips, blush: all from the concept) across. Only the skin section of the MetaHuman head is a bake target; teeth, eyes
and lashes have their own UV islands in the same 0 to 1 square. Writes tripo_on_mh.png (RGBA, alpha 0 where no
source surface was found within reach) and a check render of the MetaHuman head wearing it.
"""
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

args = sys.argv[sys.argv.index("--") + 1:]
mh_p, tr_p, out = args[0], args[1], Path(args[2]).resolve()
SIZE = int(args[3]) if len(args) > 3 else 4096
out.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)


def load(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(Path(path).resolve()))
    new = [o for o in bpy.data.objects if o not in before]
    m = max((o for o in new if o.type == "MESH"), key=lambda o: len(o.data.vertices))
    for md in list(m.modifiers):
        m.modifiers.remove(md)
    bpy.context.view_layer.update()
    mw = m.matrix_world.copy()
    m.parent = None
    m.matrix_world = Matrix.Identity(4)
    m.data.transform(mw)
    for o in new:
        if o is not m:
            bpy.data.objects.remove(o)
    return m


mh = load(mh_p)
tr = load(tr_p)
print("MH slots", [(i, s.material.name if s.material else None, sum(1 for p in mh.data.polygons if p.material_index == i))
                   for i, s in enumerate(mh.material_slots)], flush=True)
print("UV layers", [u.name for u in mh.data.uv_layers], flush=True)
# The conform does not leave the MetaHuman head exactly where the target stood (the first bake only hit the rim of
# the head). The MetaHuman head is moved onto the Tripo head: front-most points together, then rigid ICP with
# uniform scale from a sample of the Tripo vertices, as in yuki_face_compare.py. UVs do not change.
from mathutils.bvhtree import BVHTree


def bvh_of(o):
    return BVHTree.FromPolygons([v.co.copy() for v in o.data.vertices], [tuple(q.vertices) for q in o.data.polygons])


Mv = np.array([v.co[:] for v in mh.data.vertices])
Qall = np.array([v.co[:] for v in tr.data.vertices])
Q = Qall[Qall[:, 2] > Qall[:, 2].max() - 0.20]          # head only, no neck stump
Q = Q[np.random.default_rng(3).choice(len(Q), size=min(20000, len(Q)), replace=False)]
mh.data.transform(Matrix.Translation(Vector(Q[np.argmin(Q[:, 1])] - Mv[np.argmin(Mv[:, 1])])))
hist = []
for it in range(30):
    b = bvh_of(mh)
    near = np.array([b.find_nearest(Vector(q))[0][:] for q in Q])
    d = np.linalg.norm(near - Q, axis=1)
    k = d < np.percentile(d, 85)
    A, B = near[k], Q[k]
    ca, cb = A.mean(0), B.mean(0)
    U, S_, Vt = np.linalg.svd((A - ca).T @ (B - cb))
    R = Vt.T @ U.T
    if np.linalg.det(R) < 0:
        Vt[-1] *= -1
        R = Vt.T @ U.T
    sc = min(max(float(np.sqrt(((B - cb) ** 2).sum() / ((A - ca) ** 2).sum())), 0.95), 1.05)
    mh.data.transform(Matrix.Translation(Vector(cb)) @ Matrix.Scale(sc, 4) @ Matrix(R.tolist()).to_4x4() @ Matrix.Translation(Vector(-ca)))
    hist.append(round(float(np.median(d)) * 1000, 2))
print("ICP median mm", hist[::5] + hist[-1:], flush=True)
counts = np.bincount([p.material_index for p in mh.data.polygons], minlength=len(mh.material_slots))
skin_i = int(np.argmax(counts))
# keep only the skin section as the bake target
bpy.context.view_layer.objects.active = mh
bpy.ops.object.select_all(action="DESELECT")
mh.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="DESELECT")
bpy.ops.object.mode_set(mode="OBJECT")
for p in mh.data.polygons:
    p.select = p.material_index != skin_i
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.delete(type="FACE")
bpy.ops.object.mode_set(mode="OBJECT")
mh.data.uv_layers.active_index = 0

img = bpy.data.images.new("tripo_on_mh", SIZE, SIZE, alpha=True)
img.generated_color = (0, 0, 0, 0)
mat = bpy.data.materials.new("bake_target")
mat.use_nodes = True
nt = mat.node_tree
tex = nt.nodes.new("ShaderNodeTexImage")
tex.image = img
nt.nodes.active = tex
mh.data.materials.clear()
mh.data.materials.append(mat)
for p in mh.data.polygons:
    p.material_index = 0

scene = bpy.context.scene
scene.render.engine = "CYCLES"
prefs = bpy.context.preferences.addons["cycles"].preferences
for dev in ("OPTIX", "CUDA"):
    try:
        prefs.compute_device_type = dev
        prefs.get_devices()
        for dv in prefs.devices:
            dv.use = dv.type == dev
        scene.cycles.device = "GPU"
        break
    except TypeError:
        continue
scene.cycles.samples = 4
bs = scene.render.bake
bs.use_selected_to_active = True
bs.use_pass_direct = False
bs.use_pass_indirect = False
bs.use_pass_color = True
bs.cage_extrusion = 0.008
bs.max_ray_distance = 0.02
bs.margin = 16
bs.use_clear = True
bpy.ops.object.select_all(action="DESELECT")
tr.select_set(True)
mh.select_set(True)
bpy.context.view_layer.objects.active = mh
bpy.ops.object.bake(type="DIFFUSE")
img.filepath_raw = str(out / "tripo_on_mh.png")
img.file_format = "PNG"
img.save()
px = np.array(img.pixels[:], dtype=np.float32).reshape(SIZE, SIZE, 4)
print("BAKE coverage", round(float((px[..., 3] > 0.5).mean()), 3), "mean rgb where covered",
      [round(float(x), 3) for x in px[px[..., 3] > 0.5][:, :3].mean(0)], flush=True)

# Height mask in the same UV layout: 0 at 12 cm under the crown-to-chin line's chin, 1 at the chin and above. The
# Tripo bust carries a black top at the base of the neck; the composite fades to the MetaHuman's own skin there.
zc = np.array([v.co[2] for v in mh.data.vertices])
crown_z = float(zc.max())
chin_z = crown_z - 0.215
img2 = bpy.data.images.new("height_mask", SIZE // 2, SIZE // 2, alpha=False)
mat2 = bpy.data.materials.new("height")
mat2.use_nodes = True
n2 = mat2.node_tree
for nd in list(n2.nodes):
    if nd.type != "OUTPUT_MATERIAL":
        n2.nodes.remove(nd)
geo = n2.nodes.new("ShaderNodeNewGeometry")
sep = n2.nodes.new("ShaderNodeSeparateXYZ")
mr = n2.nodes.new("ShaderNodeMapRange")
mr.inputs["From Min"].default_value = chin_z - 0.07
mr.inputs["From Max"].default_value = chin_z - 0.02
em = n2.nodes.new("ShaderNodeEmission")
t2 = n2.nodes.new("ShaderNodeTexImage")
t2.image = img2
n2.links.new(geo.outputs["Position"], sep.inputs["Vector"])
n2.links.new(sep.outputs["Z"], mr.inputs["Value"])
n2.links.new(mr.outputs["Result"], em.inputs["Color"])
n2.links.new(em.outputs[0], next(n for n in n2.nodes if n.type == "OUTPUT_MATERIAL").inputs["Surface"])
n2.nodes.active = t2
mh.data.materials.clear()
mh.data.materials.append(mat2)
bs.use_selected_to_active = False
bpy.ops.object.select_all(action="DESELECT")
mh.select_set(True)
bpy.context.view_layer.objects.active = mh
bpy.ops.object.bake(type="EMIT")
img2.filepath_raw = str(out / "height_mask.png")
img2.file_format = "PNG"
img2.save()
print("MASK saved; chin z", round(chin_z, 4), "crown z", round(crown_z, 4), flush=True)
mh.data.materials.clear()
mh.data.materials.append(mat)

# check render: the MetaHuman head wearing the baked texture
bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
tr.hide_render = True
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "FLAT"
scene.display.shading.color_type = "TEXTURE"
scene.render.resolution_x = scene.render.resolution_y = 900
scene.view_settings.view_transform = "Standard"
world = bpy.data.worlds.new("w")
world.color = (0.5, 0.5, 0.5)
scene.world = world
P = np.array([v.co[:] for v in mh.data.vertices])
c = Vector(((P[:, 0].max() + P[:, 0].min()) / 2, (P[:, 1].max() + P[:, 1].min()) / 2, P[:, 2].max() - 0.12))
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
cam.data.type = "ORTHO"
cam.data.ortho_scale = 0.30
scene.collection.objects.link(cam)
scene.camera = cam
for name, yaw in (("front", 0), ("q34", 35), ("side", 90)):
    a = math.radians(yaw)
    cam.location = c + Vector((2 * math.sin(a), -2 * math.cos(a), 0))
    cam.rotation_euler = (math.pi / 2, 0, a)
    scene.render.filepath = str(out / f"check_{name}.png")
    bpy.ops.render.render(write_still=True)
print("DONE", out, flush=True)

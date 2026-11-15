"""Front view of the dressed Tripo model's head at a known scale, and the MetaHuman head's eye joints.

    ./blender_headless.sh yuki_dressed_head_probe.py -- <dressed.glb> <mh_head.fbx> <out_dir>

The dressed model is stood as in yuki_costume_tripo (facing -Y, soles on z = 0, centred on the soles). Writes
head_front.png (orthographic, base colour, PX pixels over SPAN metres, centred on x = 0 at height CZ) and probe.json
with that mapping, the depth (y) of the front surface per pixel column of the eye band for later use, and the
MetaHuman's eye joints (FACIAL_L_Eye, FACIAL_R_Eye) if the head file has them."""
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

glb, head_p = (str(Path(a).resolve()) for a in sys.argv[-3:-1])
out = Path(sys.argv[-1]).resolve()
out.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
dr = max((o for o in bpy.data.objects if o.type == "MESH"), key=lambda o: len(o.data.vertices))
dr.data.transform(dr.matrix_world)
dr.matrix_world = Matrix.Identity(4)
me = dr.data


def co(m):
    a = np.zeros(len(m.vertices) * 3)
    m.vertices.foreach_get("co", a)
    return a.reshape(-1, 3)


P = co(me)
if np.ptp(P[:, 0]) < np.ptp(P[:, 1]):
    me.transform(Matrix.Rotation(-math.pi / 2, 4, "Z"))
    P = co(me)
me.transform(Matrix.Translation((0, 0, -P[:, 2].min())))
P = co(me)
ft = P[P[:, 2] < 0.04]
me.transform(Matrix.Translation((-(ft[:, 0].max() + ft[:, 0].min()) / 2, 0, 0)))
P = co(me)
legs = P[(P[:, 2] > 0.3) & (P[:, 2] < 0.5)]
feet = P[P[:, 2] < 0.05]
if feet[:, 1].mean() > legs[:, 1].mean():
    me.transform(Matrix.Rotation(math.pi, 4, "Z"))
    P = co(me)
    legs = P[(P[:, 2] > 0.3) & (P[:, 2] < 0.5)]
me.transform(Matrix.Translation((0, -float(legs[:, 1].mean()), 0)))
P = co(me)
H = float(P[:, 2].max())
img = next(i for i in bpy.data.images if i.size[0] and i.name.lower().startswith("base"))
chk = bpy.data.materials.new("check")
chk.use_nodes = True
nt = chk.node_tree
for n in list(nt.nodes):
    if n.type != "OUTPUT_MATERIAL":
        nt.nodes.remove(n)
t = nt.nodes.new("ShaderNodeTexImage")
t.image = img
e = nt.nodes.new("ShaderNodeEmission")
nt.links.new(t.outputs["Color"], e.inputs["Color"])
nt.links.new(e.outputs[0], next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL").inputs["Surface"])
me.materials.clear()
me.materials.append(chk)
scene = bpy.context.scene
try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError:
    scene.render.engine = "BLENDER_EEVEE"
PX, SPAN, CZ = 1024, 0.40, H - 0.26
scene.render.resolution_x = scene.render.resolution_y = PX
scene.view_settings.view_transform = "Standard"
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
cam.data.type = "ORTHO"
cam.data.ortho_scale = SPAN
scene.collection.objects.link(cam)
scene.camera = cam
cam.location = (0, -3, CZ)
cam.rotation_euler = (math.pi / 2, 0, 0)
scene.render.filepath = str(out / "head_front.png")
bpy.ops.render.render(write_still=True)
bvh = BVHTree.FromPolygons([Vector(p) for p in P], [tuple(q.vertices) for q in me.polygons])
rep = {"height": H, "px": PX, "span_m": SPAN, "centre_z": CZ, "note": "pixel (u, v) from the top left: x = (u / PX - 0.5) * SPAN, z = CZ + (0.5 - v / PX) * SPAN"}
depth = {}
for zz in np.arange(CZ - 0.12, CZ + 0.12, 0.004):
    for xx in np.arange(-0.10, 0.1001, 0.004):
        hit = bvh.ray_cast(Vector((xx, -3, zz)), Vector((0, 1, 0)), 6)
        if hit[0] is not None:
            depth["%.3f,%.3f" % (xx, zz)] = round(float(hit[0].y), 4)
rep["front_depth_y"] = depth
before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=head_p)
arm = next((o for o in bpy.data.objects if o not in before and o.type == "ARMATURE"), None)
hm = max((o for o in bpy.data.objects if o not in before and o.type == "MESH"), key=lambda o: len(o.data.vertices))
bpy.context.view_layer.update()
if arm:
    names = [b.name for b in arm.data.bones]
    rep["mh_bones"] = len(names)
    rep["mh_eye_bones"] = {n: [round(float(x), 4) for x in (arm.matrix_world @ arm.data.bones[n].head_local)] for n in names if "eye" in n.lower() and "lid" not in n.lower()}
    for n in ("head", "neck_01", "FACIAL_C_FacialRoot", "FACIAL_C_Jaw", "FACIAL_C_NoseTip"):
        if n in names:
            rep.setdefault("mh_joints", {})[n] = [round(float(x), 4) for x in (arm.matrix_world @ arm.data.bones[n].head_local)]
Hm = np.array([hm.matrix_world @ v.co for v in hm.data.vertices])
rep["mh_head_bounds"] = [Hm.min(0).round(4).tolist(), Hm.max(0).round(4).tolist()]
(out / "probe.json").write_text(json.dumps(rep))
print("HEADPROBE", json.dumps({k: v for k, v in rep.items() if k != "front_depth_y"}), flush=True)

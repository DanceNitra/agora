"""Clean, lengthen, thicken and recolour a HairDeck hair GLB for Yuki.

    ./blender_headless.sh yuki_hair_fix.py -- <hair_seedN.glb> <out_dir>

- Inner faces: each card is a closed tube whose sections are also capped inside. A ring edge is shared by two wall
  faces and one inner cap face, so an inner cap triangle has two such non-manifold edges; walls and the two end caps
  have at most one. Those faces are deleted.
- Length: the concept's hair reaches the thighs, about 4.7 head heights below the crown; HairDeck's reaches about 3.6.
  Below the chin of the head proxy the hair is stretched downward by LENGTH (env, default 1.5).
- Volume: a second copy of the cards, turned THICK_DEG (env, default 4) about the head's vertical axis and pushed out
  by 3 %, fills the gaps between the flat cards seen from the back.
- Colour: pastel pink-silver base from the concept, with HairDeck's per-card colours kept as light variation.
Writes yuki_hair.glb (cards only) and front, side, back renders with the head proxy.
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

src, out = sys.argv[-2], Path(sys.argv[-1]).resolve()
out.mkdir(parents=True, exist_ok=True)
LENGTH = float(os.environ.get("LENGTH", 1.5))
THICK_DEG = float(os.environ.get("THICK_DEG", 4.0))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(Path(src).resolve()))
hair = bpy.data.objects["hair_cards"]
head = bpy.data.objects.get("head_proxy")
for o in (hair, head):
    if o:
        o.data.transform(o.matrix_world)
        o.parent = None
        o.matrix_world = Matrix.Identity(4)
HP = np.array([v.co[:] for v in head.data.vertices])
chin_z, crown_z = float(HP[:, 2].min()), float(HP[:, 2].max())
hc = HP.mean(0)
rep = {"head_height": round(crown_z - chin_z, 4)}

bm = bmesh.new()
bm.from_mesh(hair.data)
bm.faces.ensure_lookup_table()
rep["faces_before"] = len(bm.faces)
P0 = np.array([v.co[:] for v in bm.verts])
rep["length_heads_before"] = round((crown_z - P0[:, 2].min()) / (crown_z - chin_z), 2)
inner = [f for f in bm.faces if sum(1 for e in f.edges if len(e.link_faces) > 2) >= 2]
bmesh.ops.delete(bm, geom=inner, context="FACES")
rep["inner_faces_removed"] = len(inner)
rep["nonmanifold_edges_left"] = sum(1 for e in bm.edges if len(e.link_faces) > 2)

# lengthen below the chin, smoothly: the stretch grows from 1 at the chin to LENGTH a head height below it
# local stretch s(d) = 1 + (LENGTH - 1) d / h for d < h, then LENGTH; the new depth is its integral
h = crown_z - chin_z
for v in bm.verts:
    d = chin_z - v.co.z
    if d > 0:
        nd = d + (LENGTH - 1.0) * d * d / (2 * h) if d < h else h * (1 + (LENGTH - 1.0) / 2) + (d - h) * LENGTH
        v.co.z = chin_z - nd
P1 = np.array([v.co[:] for v in bm.verts])
rep["length_heads_after"] = round((crown_z - P1[:, 2].min()) / (crown_z - chin_z), 2)

# thicken: a turned, slightly larger copy
geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
dup = bmesh.ops.duplicate(bm, geom=geom)
dv = [g for g in dup["geom"] if isinstance(g, bmesh.types.BMVert)]
T = (Matrix.Translation(Vector(hc)) @ Matrix.Rotation(math.radians(THICK_DEG), 4, "Z") @ Matrix.Diagonal((1.03, 1.03, 1.0, 1.0))
     @ Matrix.Translation(-Vector(hc)))
bmesh.ops.transform(bm, matrix=T, verts=dv)
rep["faces_after"] = len(bm.faces)
bm.to_mesh(hair.data)
bm.free()
hair.data.update()

# colour: pastel pink-silver from the concept, card colours kept as +-15 % variation
mat = hair.data.materials[0]
mat.use_nodes = True
nt = mat.node_tree
bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
base = tuple(float(x) for x in os.environ.get("HAIR_RGB", "0.95,0.80,0.86").split(","))  # concept hair, mid tone, sRGB
lin = [c ** 2.2 for c in base]
attr = nt.nodes.new("ShaderNodeAttribute")
attr.attribute_name = "Color"
mix = nt.nodes.new("ShaderNodeMix")
mix.data_type = "RGBA"
mix.blend_type = "OVERLAY"
mix.inputs["Factor"].default_value = 0.25
mix.inputs["A"].default_value = (*lin, 1.0)
nt.links.new(attr.outputs["Color"], mix.inputs["B"])
# Fine strands inside each card: stripes across the card's UV width, lighter toward the tips (silver sheen).
uvn = nt.nodes.new("ShaderNodeUVMap")
sep = nt.nodes.new("ShaderNodeSeparateXYZ")
nt.links.new(uvn.outputs["UV"], sep.inputs["Vector"])
wave = nt.nodes.new("ShaderNodeTexWave")
wave.wave_type = "BANDS"
wave.bands_direction = os.environ.get("STRIPE_AXIS", "X")
wave.inputs["Scale"].default_value = float(os.environ.get("STRIPE_SCALE", 40))
wave.inputs["Distortion"].default_value = 4.0
wave.inputs["Detail"].default_value = 3.0
nt.links.new(uvn.outputs["UV"], wave.inputs["Vector"])
ramp = nt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].color = (0.55, 0.55, 0.55, 1)
ramp.color_ramp.elements[1].color = (1.15, 1.15, 1.15, 1)
nt.links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
mul = nt.nodes.new("ShaderNodeMix")
mul.data_type = "RGBA"
mul.blend_type = "MULTIPLY"
mul.inputs["Factor"].default_value = 1.0
nt.links.new(mix.outputs["Result"], mul.inputs["A"])
nt.links.new(ramp.outputs["Color"], mul.inputs["B"])
nt.links.new(mul.outputs["Result"], bsdf.inputs["Base Color"])
bsdf.inputs["Roughness"].default_value = 0.55
for key in ("Coat Weight", "Sheen Weight"):
    if key in bsdf.inputs:
        bsdf.inputs[key].default_value = 0.2

bpy.ops.object.select_all(action="DESELECT")
hair.select_set(True)
bpy.context.view_layer.objects.active = hair
bpy.ops.export_scene.gltf(filepath=str(out / "yuki_hair.glb"), use_selection=True)
(out / "fix.json").write_text(json.dumps(rep, indent=1))
print("FIX", json.dumps(rep), flush=True)

scene = bpy.context.scene
try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError:
    scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = scene.render.resolution_y = 800
scene.view_settings.view_transform = "Standard"
world = bpy.data.worlds.new("w")
world.color = (0.8, 0.8, 0.8)
scene.world = world
for name, rot, e in (("key", (50, 0, -30), 3.0), ("fill", (60, 0, 150), 1.5)):
    L = bpy.data.objects.new(name, bpy.data.lights.new(name, "SUN"))
    L.data.energy = e
    L.rotation_euler = [math.radians(a) for a in rot]
    scene.collection.objects.link(L)
P = np.array([v.co[:] for v in hair.data.vertices])
lo, hi = P.min(0), P.max(0)
c = (lo + hi) / 2
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
cam.data.type = "ORTHO"
cam.data.ortho_scale = float(max(hi - lo)) * 1.08
scene.collection.objects.link(cam)
scene.camera = cam
for tag, yaw in (("front", 0), ("side", 90), ("back", 180)):
    a = math.radians(yaw)
    cam.location = Vector((c[0] + 5 * math.sin(a), c[1] - 5 * math.cos(a), c[2]))
    cam.rotation_euler = (math.pi / 2, 0, a)
    scene.render.filepath = str(out / f"{tag}.png")
    bpy.ops.render.render(write_still=True)
print("DONE", out, flush=True)

"""Measure one GLB and render fixed inspection views. Run headless:

    blender -b --python inspect_glb.py -- <model.glb> <out_dir>

Writes stats.json and front, back, side, face, hand_l, hand_r, feet PNG files.
"""
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

# Absolute paths: Blender resolves a relative render path against the drive root.
glb, out = Path(sys.argv[-2]).resolve(), Path(sys.argv[-1]).resolve()
out.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(glb))
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]

lo = Vector((1e9, 1e9, 1e9))
hi = Vector((-1e9, -1e9, -1e9))
verts = tris = boundary = nonmanifold = components = 0
for o in meshes:
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.transform(o.matrix_world)
    # glTF splits vertices at UV seams; weld them so holes and components are real ones.
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    verts += len(bm.verts)
    tris += sum(len(f.verts) - 2 for f in bm.faces)
    boundary += sum(1 for e in bm.edges if e.is_boundary)
    nonmanifold += sum(1 for e in bm.edges if not e.is_manifold and not e.is_boundary)
    for v in bm.verts:
        for i in range(3):
            lo[i] = min(lo[i], v.co[i])
            hi[i] = max(hi[i], v.co[i])
    seen = set()
    for v in bm.verts:
        if v.index in seen:
            continue
        components += 1
        stack = [v]
        seen.add(v.index)
        while stack:
            for e in stack.pop().link_edges:
                for w in e.verts:
                    if w.index not in seen:
                        seen.add(w.index)
                        stack.append(w)
    bm.free()

size = hi - lo
stats = {
    "file": glb.name, "objects": len(meshes), "vertices": verts, "triangles": tris,
    "components": components, "boundary_edges": boundary, "non_manifold_edges": nonmanifold,
    "size_xyz_m": [round(s, 4) for s in size], "min": [round(c, 4) for c in lo], "max": [round(c, 4) for c in hi],
    "materials": sorted({m.name for o in meshes for m in o.data.materials if m}),
    "images": sorted({f"{i.name} {i.size[0]}x{i.size[1]}" for i in bpy.data.images if i.size[0]}),
}
(out / "stats.json").write_text(json.dumps(stats, indent=2))
print("STATS", json.dumps(stats))

scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "FLAT"
scene.display.shading.color_type = "TEXTURE"
scene.render.resolution_x = scene.render.resolution_y = 1100
scene.render.film_transparent = False
world = bpy.data.worlds.new("w")
scene.world = world
world.color = (0.75, 0.75, 0.75)
cam_data = bpy.data.cameras.new("cam")
cam_data.type = "ORTHO"
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam

center = (lo + hi) / 2
# glTF import gives Z up; the widest horizontal axis is the arm span.
span_axis = 0 if size[0] >= size[1] else 1
depth_axis = 1 - span_axis
height = size[2]


def shot(name, target, direction, scale):
    cam_data.ortho_scale = scale
    cam.location = target + direction * 10
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(out / f"{name}.png")
    bpy.ops.render.render(write_still=True)


d = Vector((0, 0, 0))
d[depth_axis] = -1
s = Vector((0, 0, 0))
s[span_axis] = 1
full = max(size[span_axis], height) * 1.05
shot("front", center, d, full)
shot("back", center, -d, full)
shot("side", center, s, height * 1.05)
top = Vector(center)
top[2] = hi[2] - height * 0.07
shot("face", top, d, height * 0.2)
# Which side is the front depends on the export; shoot the head and feet from both.
shot("face_b", top, -d, height * 0.2)
low = Vector(center)
low[2] = lo[2] + height * 0.06
shot("feet_b", low, (-d + Vector((0, 0, 0.6))).normalized(), height * 0.35)
for name, sign in (("hand_l", -1), ("hand_r", 1)):
    t = Vector(center)
    t[span_axis] = center[span_axis] + sign * size[span_axis] * 0.44
    t[2] = lo[2] + height * 0.78
    shot(name, t, d, height * 0.2)
    shot(name + "_top", t, Vector((0, 0, 1)), height * 0.2)
ft = Vector(center)
ft[2] = lo[2] + height * 0.05
shot("feet", ft, (d + Vector((0, 0, 0.6))).normalized(), height * 0.35)

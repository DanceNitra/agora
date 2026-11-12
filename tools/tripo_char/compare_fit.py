"""Measure the conformed MetaHuman against the Tripo source and render both side by side.

    blender -b --factory-startup --python compare_fit.py -- <source.fbx> <metahuman_fullbody.fbx> <out_dir>

The MetaHuman is in A pose and the source in T pose, so distances are reported by region and the arms are
left out of the numbers. Distances are from MetaHuman vertices to the nearest source surface point.
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

src_path, mh_path, out = (Path(a).resolve() for a in sys.argv[-3:])
out.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)


def load(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(path))
    objs = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    pts, polys = [], []
    for o in objs:
        base = len(pts)
        pts += [o.matrix_world @ v.co for v in o.data.vertices]
        polys += [[base + i for i in p.vertices] for p in o.data.polygons]
    return objs, pts, polys


s_objs, s_pts, s_polys = load(src_path)
m_objs, m_pts, m_polys = load(mh_path)


def bounds(pts):
    return [min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]


s_lo, s_hi = bounds(s_pts)
m_lo, m_hi = bounds(m_pts)
tree = BVHTree.FromPolygons(s_pts, s_polys)
H = m_hi[2] - m_lo[2]
regions = {
    "head (above 87 % of height)": lambda p: p.z > m_lo[2] + 0.87 * H and abs(p.x) < 0.14,
    "torso (53 to 82 %, within 17 cm of centre)": lambda p: m_lo[2] + 0.53 * H < p.z < m_lo[2] + 0.82 * H and abs(p.x) < 0.17,
    "pelvis and thighs (30 to 53 %)": lambda p: m_lo[2] + 0.30 * H < p.z <= m_lo[2] + 0.53 * H and abs(p.x) < 0.25,
    "lower legs (6 to 30 %)": lambda p: m_lo[2] + 0.06 * H < p.z <= m_lo[2] + 0.30 * H and abs(p.x) < 0.25,
    "feet (below 6 %)": lambda p: p.z <= m_lo[2] + 0.06 * H and abs(p.x) < 0.25,
}
stats = {"source_size_m": [round(s_hi[i] - s_lo[i], 4) for i in range(3)],
         "metahuman_size_m": [round(m_hi[i] - m_lo[i], 4) for i in range(3)],
         "metahuman_vertices": len(m_pts), "regions_mm": {}}
for name, test in regions.items():
    d = sorted(tree.find_nearest(p)[3] * 1000 for p in m_pts if test(p))
    if d:
        stats["regions_mm"][name] = {"vertices": len(d), "median": round(d[len(d) // 2], 1),
                                     "p90": round(d[int(len(d) * 0.9)], 1), "max": round(d[-1], 1)}
(out / "fit_stats.json").write_text(json.dumps(stats, indent=2))
print("FIT", json.dumps(stats))

# Renders: source in grey-blue, MetaHuman in orange, overlaid and side by side.
scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "OBJECT"
scene.display.shading.show_xray = False
scene.render.resolution_x = scene.render.resolution_y = 1100
world = bpy.data.worlds.new("w")
world.color = (0.8, 0.8, 0.8)
scene.world = world
for o in s_objs:
    o.color = (0.35, 0.5, 0.75, 1)
for o in m_objs:
    o.color = (0.95, 0.55, 0.2, 1)
cd = bpy.data.cameras.new("c")
cd.type = "ORTHO"
cam = bpy.data.objects.new("c", cd)
scene.collection.objects.link(cam)
scene.camera = cam


def shot(name, target, direction, scale, show):
    for o in s_objs:
        o.hide_render = "s" not in show
    for o in m_objs:
        o.hide_render = "m" not in show
    cd.ortho_scale = scale
    cam.location = Vector(target) + Vector(direction) * 10
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(out / f"{name}.png")
    bpy.ops.render.render(write_still=True)


mid = (0, 0, H / 2)
head = (0, 0, m_lo[2] + 0.93 * H)
for tag, show in (("src", "s"), ("mh", "m"), ("both", "sm")):
    shot(f"front_{tag}", mid, (0, -1, 0), 2.0, show)
    shot(f"side_{tag}", mid, (1, 0, 0), 2.0, show)
    shot(f"head_front_{tag}", head, (0, -1, 0), 0.42, show)
    shot(f"head_side_{tag}", head, (1, 0, 0), 0.42, show)

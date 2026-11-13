"""Measures how far the costume stands off the body around the left shoulder, in the rest pose and with the left arm
raised overhead, and renders that pose. The owner saw a thick round sleeve and a ridge on the upper back in a dance clip.

    blender_headless.sh costume_shoulder_probe.py -- <body.fbx> <costume.fbx> <out_dir>

Blender drives no MetaHuman corrective bones, so the body here deforms by plain skinning. The figures compare costume
versions with each other; they are not the Unreal result.
"""
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

body_fbx, cos_fbx, out = sys.argv[-3], sys.argv[-2], Path(sys.argv[-1]).resolve()
out.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)


def load(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(Path(path).resolve()))
    new = [o for o in bpy.data.objects if o not in before]
    arm = next(o for o in new if o.type == "ARMATURE")
    meshes = [o for o in new if o.type == "MESH"]
    return arm, meshes


barm, bmeshes = load(body_fbx)
carm, cmeshes = load(cos_fbx)
body = max(bmeshes, key=lambda o: len(o.data.vertices))
cos = max(cmeshes, key=lambda o: len(o.data.vertices))
for o in bmeshes:
    if o is not body:
        o.hide_render = True
print("BODY", body.name, len(body.data.vertices), "COSTUME", cos.name, len(cos.data.vertices), flush=True)


def world_mesh(o):
    dg = bpy.context.evaluated_depsgraph_get()
    e = o.evaluated_get(dg)
    m = e.to_mesh()
    P = np.array([o.matrix_world @ v.co for v in m.vertices])
    m.calc_loop_triangles()
    T = [tuple(t.vertices) for t in m.loop_triangles]
    e.to_mesh_clear()
    return P, T


def raise_arm(arm, deg):
    """Turn the left upper arm about its head, in armature space, from hanging towards straight up."""
    pb = arm.pose.bones["upperarm_l"]
    bpy.context.view_layer.update()
    head = arm.matrix_world @ pb.head
    tail = arm.matrix_world @ arm.pose.bones["lowerarm_l"].head
    d = (tail - head).normalized()
    axis = d.cross(Vector((0, 0, 1)))
    axis.normalize()
    R = Matrix.Translation(head) @ Matrix.Rotation(math.radians(deg), 4, axis) @ Matrix.Translation(-head)
    pb.matrix = arm.matrix_world.inverted() @ R @ arm.matrix_world @ pb.matrix
    bpy.context.view_layer.update()
    return head


def standoff(tag, head):
    BP, BT = world_mesh(body)
    CP, _ = world_mesh(cos)
    bvh = BVHTree.FromPolygons([Vector(p) for p in BP], BT)
    sel = np.nonzero(np.linalg.norm(CP - np.array(head), axis=1) < 0.16)[0]
    d = np.array([(Vector(CP[i]) - bvh.find_nearest(Vector(CP[i]))[0]).length for i in sel])
    above = CP[sel, 2] > head[2]
    back = CP[sel, 1] > head[1]  # MetaHuman faces -Y
    r = {"n": int(len(sel)), "all_mm": [round(float(x) * 1000, 1) for x in np.percentile(d, [50, 90, 99])],
         "upper_back_mm": [round(float(x) * 1000, 1) for x in np.percentile(d[back & ~above], [50, 90, 99])] if (back & ~above).any() else None,
         "over_4cm_pct": round(float((d > 0.04).mean()) * 100, 1)}
    print("STANDOFF", tag, r, flush=True)
    return r


def folds():
    """Fold angle per costume edge between two faces, from the evaluated mesh, in degrees."""
    dg = bpy.context.evaluated_depsgraph_get()
    e = cos.evaluated_get(dg)
    m = e.to_mesh()
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(m)
    bm.edges.ensure_lookup_table()
    A = np.array([math.degrees(ed.calc_face_angle(0.0)) if len(ed.link_faces) == 2 else 0.0 for ed in bm.edges])
    V = np.array([[ed.verts[0].index, ed.verts[1].index] for ed in bm.edges])
    bm.free()
    e.to_mesh_clear()
    return A, V


rep = {}
bpy.context.view_layer.update()
A0, EV = folds()
h = barm.matrix_world @ barm.pose.bones["upperarm_l"].head
rep["rest"] = standoff("rest", h)
for a in (barm, carm):
    h = raise_arm(a, 140)
rep["arm_up_140"] = standoff("arm_up_140", h)
A1, _ = folds()
CPw, _ = world_mesh(cos)
mid = (CPw[EV[:, 0]] + CPw[EV[:, 1]]) / 2
near = np.linalg.norm(mid - np.array(h), axis=1) < 0.20
gain = np.where(near, A1 - A0, 0)
bad = np.nonzero(gain > 35)[0]
groups = {g.index: g.name for g in cos.vertex_groups}
mass = {}
for v in np.unique(EV[bad].ravel()):
    for g in cos.data.vertices[int(v)].groups:
        mass[groups[g.group]] = mass.get(groups[g.group], 0) + g.weight
top = sorted(mass.items(), key=lambda kv: -kv[1])[:10]
rel = mid[bad] - np.array(h)
rep["fold_gain_over_35deg"] = {"edges": int(len(bad)), "near_edges": int(near.sum()),
    "where_cm_median_xyz": [round(float(x) * 100, 1) for x in np.median(rel, 0)] if len(bad) else None,
    "dist_cm_10_50_90": [round(float(x) * 100, 1) for x in np.percentile(np.linalg.norm(rel, axis=1), [10, 50, 90])] if len(bad) else None,
    "dz_cm_10_50_90": [round(float(x) * 100, 1) for x in np.percentile(rel[:, 2], [10, 50, 90])] if len(bad) else None,
    "back_share": round(float((rel[:, 1] > 0).mean()), 2) if len(bad) else None,
    "weight_mass_top": [[k, round(v, 1)] for k, v in top]}
print("FOLDS", rep["fold_gain_over_35deg"], flush=True)
(out / "probe.json").write_text(json.dumps(rep, indent=1))

scene = bpy.context.scene
try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError:
    scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = scene.render.resolution_y = 900
world = bpy.data.worlds.new("w")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.7, 0.7, 0.7, 1)
scene.world = world
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
sun.data.energy = 3
sun.rotation_euler = (math.radians(55), 0, math.radians(-25))
scene.collection.objects.link(sun)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
cam.data.type = "ORTHO"
cam.data.ortho_scale = 0.75
scene.collection.objects.link(cam)
scene.camera = cam
c = Vector((h[0], h[1], h[2] + 0.12))
for name, loc, rot in (("backleft", (2.8, 2.8, 0), (90, 0, 135)), ("back", (0, 4, 0), (90, 0, 180)), ("front", (0, -4, 0), (90, 0, 0)), ("left", (4, 0, 0), (90, 0, 90))):
    cam.location = c + Vector(loc)
    cam.rotation_euler = [math.radians(x) for x in rot]
    scene.render.filepath = str(out / f"arm_up_{name}.png")
    bpy.ops.render.render(write_still=True)
print("DONE", out, flush=True)

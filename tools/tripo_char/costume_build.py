"""Costume from the dressed Tripo mesh, skinned to the fitted MetaHuman skeleton. Run headless:

    blender -b --factory-startup --python costume_build.py -- <mh_fullbody.fbx> <bare_clean.fbx> <dressed.glb> <out_dir>

Method: the dressed mesh is in Tripo's T-pose, the MetaHuman export is in the A-pose. The MetaHuman arms and legs are
posed onto the dressed mesh, the head and hands are cut from the dressed mesh, each costume vertex takes the skin
weights of the nearest point on the posed body, and the costume is then moved back to the rest pose with the inverse
of its own skinning transform. Writes <out_dir>/hero01_costume.fbx, the textures, check renders, and a report.
"""
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

mh_p, bare_p, glb_p = (str(Path(a).resolve()) for a in sys.argv[-4:-1])
out = Path(sys.argv[-1]).resolve()
out.mkdir(parents=True, exist_ok=True)
rep = {}
bpy.ops.wm.read_factory_settings(use_empty=True)


def imported(op, path):
    before = set(bpy.data.objects)
    op(filepath=path)
    return list(set(bpy.data.objects) - before)


def stand(P):
    """Face -Y, centred, feet on the floor: the same frame clean_body.py writes."""
    M = Matrix.Identity(4)
    if np.ptp(P[:, 1]) > np.ptp(P[:, 0]):
        M = Matrix.Rotation(-math.pi / 2, 4, "Z")
        P = P @ np.array(M.to_3x3()).T
    t = Vector((-(P[:, 0].max() + P[:, 0].min()) / 2, -(P[:, 1].max() + P[:, 1].min()) / 2, -P[:, 2].min()))
    return Matrix.Translation(t) @ M


def world_pts(o):
    return np.array([o.matrix_world @ v.co for v in o.data.vertices])


def marks(P):
    h = P[:, 2].max()
    x = 0.35 * P[:, 0].max()
    s = P[np.abs(P[:, 0] - x) < 0.01]
    mid = P[(np.abs(P[:, 0]) < 0.012) & (P[:, 2] < 0.6 * h)]
    return {"shoulder_arm_z": (s[:, 2].max() + s[:, 2].min()) / 2, "crotch_z": mid[:, 2].min(), "tip_x": P[:, 0].max()}


def line_dir(C):
    c = C.mean(0)
    d = np.linalg.svd(C - c)[2][0]
    return c, d


# ---- 1. dressed mesh into the bare mesh's frame ---------------------------------------------------------------
bare = next(o for o in imported(bpy.ops.import_scene.fbx, bare_p) if o.type == "MESH")
Bp = world_pts(bare)
Bp = Bp @ np.array(stand(Bp).to_3x3()).T + np.array(stand(Bp).translation)
mb = marks(Bp)
bpy.data.objects.remove(bare)

dr = next(o for o in imported(bpy.ops.import_scene.gltf, glb_p) if o.type == "MESH")
dr.data.transform(dr.matrix_world)
dr.matrix_world = Matrix.Identity(4)
bm = bmesh.new()
bm.from_mesh(dr.data)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
bm.to_mesh(dr.data)
bm.free()
Dp = world_pts(dr)
dr.data.transform(stand(Dp))
md = marks(world_pts(dr))
# Uniform scale and height from two landmarks that clothing changes little: arm height at the shoulder, crotch.
s = (mb["shoulder_arm_z"] - mb["crotch_z"]) / (md["shoulder_arm_z"] - md["crotch_z"])
# A dressed mesh in the A-pose has no arm at the bare T-pose's shoulder height, so the landmark above does not apply.
# COSTUME_SCALE passes the scale measured on the T-pose dressed mesh of the same figure (hero 01: 0.9951).
import os
if os.environ.get("COSTUME_SCALE"):
    s = float(os.environ["COSTUME_SCALE"])
dz = mb["crotch_z"] - s * md["crotch_z"]
dr.data.transform(Matrix.Translation((0, 0, dz)) @ Matrix.Scale(s, 4))
D = world_pts(dr)
rep["align"] = {"scale": round(s, 4), "dz_m": round(dz, 4), "dressed_bottom_z": round(float(D[:, 2].min()), 4),
                "bare_tip_x": round(mb["tip_x"], 4), "dressed_tip_x": round(float(D[:, 0].max()), 4)}

# ---- 2. MetaHuman posed onto the dressed mesh ------------------------------------------------------------------
mh = imported(bpy.ops.import_scene.fbx, mh_p)
arm = next(o for o in mh if o.type == "ARMATURE")
body = next(o for o in mh if o.type == "MESH")
A = arm.matrix_world.copy()
Ai = A.inverted()
bpy.context.view_layer.objects.active = arm


def joint(n):
    bpy.context.view_layer.update()
    return A @ arm.pose.bones[n].head


def turn(bone, tip, target, scale=1.0):
    """Rotate pose bone `bone` about its head so the direction head->`tip` joint becomes `target`."""
    pb = arm.pose.bones[bone]
    h = joint(bone)
    a = (joint(tip) - h).normalized()
    R = a.rotation_difference(Vector(target).normalized()).to_matrix().to_4x4()
    # Scale along the bone only. A uniform scale also shrank the arm's cross-section in this pose, and undoing it on the
    # way back to the rest pose widened the sleeve by 11 % where the arm weights begin: a shelf around the upper arm.
    W = Matrix.Translation(h) @ R @ Matrix.Scale(scale, 4, a) @ Matrix.Translation(-h)
    pb.matrix = Ai @ W @ A @ pb.matrix
    bpy.context.view_layer.update()


def slabs(P, axis, lo, hi, side):
    C = []
    other = [i for i in range(3) if i != axis]
    for a in np.arange(lo, hi, 0.02):
        m = (P[:, axis] >= a) & (P[:, axis] < a + 0.02)
        if axis == 2:
            m &= (P[:, 0] * side > 0.02)
        q = P[m]
        if len(q) > 20:
            c = np.zeros(3)
            c[axis] = a + 0.01
            for i in other:
                c[i] = (q[:, i].max() + q[:, i].min()) / 2
            C.append(c)
    return np.array(C)


def body_pts():
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    e = body.evaluated_get(dg)
    me = e.to_mesh()
    P = np.array([e.matrix_world @ v.co for v in me.vertices])
    e.to_mesh_clear()
    return P


pose_rep = {}
for sfx, side in (("l", 1.0), ("r", -1.0)):
    tip = D[:, 0].max() if side > 0 else -D[:, 0].min()
    Ca = slabs(D * np.array([side, 1, 1]), 0, 0.30, 0.80 * tip, 1) * np.array([side, 1, 1])
    c, d0 = line_dir(Ca)
    # The wrist is one hand length (0.176 m on hero 01's T-pose mesh) back from the fingertips along the arm. With the
    # arms lowered, 0.80 of the fingertip x stops short of it.
    Ca = slabs(D * np.array([side, 1, 1]), 0, 0.30, tip - 0.176 * abs(d0[0]), 1) * np.array([side, 1, 1])
    c, d0 = line_dir(Ca)
    # Aim the arm from the MetaHuman shoulder joint at the dressed wrist, and scale it so the wrist joint lands there.
    # A parallel arm 6 cm beside the sleeve let the push-out step collapse the sleeve onto one side of the arm.
    wrist = Ca[-1]
    sh = np.array(joint(f"upperarm_{sfx}"))
    d = (wrist - sh) / np.linalg.norm(wrist - sh)
    turn(f"upperarm_{sfx}", f"lowerarm_{sfx}", d)
    turn(f"lowerarm_{sfx}", f"hand_{sfx}", d)
    turn(f"hand_{sfx}", f"middle_01_{sfx}", d)
    k = np.linalg.norm(wrist - sh) / (np.array(joint(f"hand_{sfx}")) - sh).dot(d)
    turn(f"upperarm_{sfx}", f"lowerarm_{sfx}", d, scale=k)
    Cl = slabs(D, 2, 0.12, 0.70, side)
    cl, dl = line_dir(Cl)
    dl = dl * -np.sign(dl[2])
    hip0 = np.array(joint(f"thigh_{sfx}"))
    aim = Cl[0] - hip0
    turn(f"thigh_{sfx}", f"foot_{sfx}", aim / np.linalg.norm(aim))
    sh = np.array(joint(f"upperarm_{sfx}"))
    hip, foot = np.array(joint(f"thigh_{sfx}")), np.array(joint(f"foot_{sfx}"))
    pose_rep[sfx] = {"arm_dir": [round(float(x), 3) for x in d], "arm_scale": round(float(k), 4),
                     "shoulder_to_arm_line_cm": round(float(np.linalg.norm(np.cross(sh - c, d))) * 100, 2),
                     "leg_dir": [round(float(x), 3) for x in dl],
                     "foot_to_leg_line_cm": round(float(np.linalg.norm(np.cross(foot - cl, dl))) * 100, 2),
                     "hip_to_leg_line_cm": round(float(np.linalg.norm(np.cross(hip - cl, dl))) * 100, 2)}
rep["pose"] = pose_rep
ARM_AX = {sfx: (np.array(joint(f"upperarm_{sfx}")), np.array(joint(f"hand_{sfx}"))) for sfx in ("l", "r")}
bpy.context.view_layer.update()

# posed body: points, triangles, weights, bone matrices
dg = bpy.context.evaluated_depsgraph_get()
dg.update()
be = body.evaluated_get(dg)
bme = be.to_mesh()
bme.calc_loop_triangles()
BP = np.array([be.matrix_world @ v.co for v in bme.vertices])
BT = np.array([t.vertices[:] for t in bme.loop_triangles])
BVN = np.array([be.matrix_world.to_3x3() @ v.normal for v in bme.vertices])
BVN /= np.maximum(np.linalg.norm(BVN, axis=1), 1e-9)[:, None]
BN = np.array([be.matrix_world.to_3x3() @ t.normal for t in bme.loop_triangles])
BN /= np.linalg.norm(BN, axis=1)[:, None]
gnames = [g.name for g in body.vertex_groups]
bones = [n for n in gnames if n in arm.pose.bones]
bidx = {n: i for i, n in enumerate(bones)}
BW = np.zeros((len(BP), len(bones)), dtype=np.float32)
for v in body.data.vertices:
    for g in v.groups:
        n = gnames[g.group]
        if n in bidx:
            BW[v.index, bidx[n]] = g.weight
BW /= np.maximum(BW.sum(1), 1e-9)[:, None]
BM = np.array([np.array(A @ arm.pose.bones[n].matrix @ arm.data.bones[n].matrix_local.inverted() @ Ai) for n in bones])
bvh = BVHTree.FromPolygons([Vector(p) for p in BP], [tuple(int(i) for i in t) for t in BT])
be.to_mesh_clear()

# ---- 3. cut head and hands from the dressed mesh by texture colour and place -----------------------------------
mat = dr.data.materials[0]
# Tripo's material is single-sided (glTF doubleSided false). Looking into a cuff, the far inner wall of the sleeve was
# culled and the background showed as light spots beside the wrist. Cloth is two-sided; in Unreal the costume material
# needs Two Sided as well, because FBX does not carry this flag.
mat.use_backface_culling = False
tex = {}
for node in mat.node_tree.nodes:
    if node.type == "TEX_IMAGE" and node.image:
        tex[node.image.name.split("_")[0]] = node.image
col_img = tex.get("Color") or next(iter(tex.values()))
w, h = col_img.size
px = np.array(col_img.pixels[:], dtype=np.float32).reshape(h, w, 4)[:, :, :3]
px = np.where(px <= 0.0031308, px * 12.92, 1.055 * np.power(np.maximum(px, 1e-9), 1 / 2.4) - 0.055)  # to sRGB
uv = dr.data.uv_layers.active.data
me = dr.data
FC = np.zeros((len(me.polygons), 3))
FCOL = np.zeros((len(me.polygons), 3))
for p in me.polygons:
    FC[p.index] = np.array(p.center)
    u = np.mean([uv[i].uv[:] for i in p.loop_indices], axis=0)
    FCOL[p.index] = px[min(h - 1, int((u[1] % 1.0) * h)), min(w - 1, int((u[0] % 1.0) * w))]
r, g, b = FCOL[:, 0], FCOL[:, 1], FCOL[:, 2]
lum = FCOL.mean(1)
skin = (r > 0.45) & (r - b > 0.08) & (lum > 0.42)
blue = (b - r > 0.03)
_kb = np.nonzero(blue)[0]
_k = int(_kb[np.argsort(lum[_kb])[len(_kb) // 2]])
STOCK_UV = tuple(float(x) for x in np.mean([uv[i].uv[:] for i in me.polygons[_k].loop_indices], axis=0))  # a texel of the cloth's median blue
ax = np.abs(FC[:, 0])
collar_top = FC[blue & (ax < 0.12), 2].max()
cuff = {sgn: (FC[blue & (FC[:, 0] * sgn > 0.3), 0] * sgn).max() for sgn in (1, -1)}
neck_skin_low = FC[skin & (ax < 0.1) & (FC[:, 2] > 1.3), 2].min()
head = (ax < 0.16) & (FC[:, 2] > neck_skin_low) & ~blue
head |= (FC[:, 2] > collar_top + 0.005)
# Hair is neither skin nor blue, and dark hair can read as blue and lift `collar_top` to the crown (1.837 on the A-pose
# mesh), which left the hair on the head. Nothing of the costume is higher than 15 cm above the lowest neck skin.
head |= (FC[:, 2] > neck_skin_low + 0.15)
hands = np.zeros(len(FC), bool)
for sgn in (1, -1):
    hands |= (FC[:, 0] * sgn > cuff[sgn] + 0.003) | ((FC[:, 0] * sgn > cuff[sgn] - 0.06) & skin)
drop = head | hands | (skin & (FC[:, 2] > 1.25))
# Ragged rims. The colour cut leaves faces that are neither skin nor cloth on the open edges: dark hair on the back of
# the collar (b-r 0.03 to 0.05, lum under 0.39 on the A-pose mesh) and pink blended texels around the cuff opening.
# Cloth is b-r 0.10 and more. Such faces are removed ring by ring, only while they touch a face already removed.
# Touching is by a shared vertex: with shared edges only, hair faces hanging on one corner stayed (v31).
_lv = np.zeros(len(me.loops), dtype=np.int64)
me.loops.foreach_get("vertex_index", _lv)
_lf = np.repeat(np.arange(len(me.polygons)), [p.loop_total for p in me.polygons])
ragged = (ax < 0.16) & (FC[:, 2] > neck_skin_low) & (b - r < 0.07) & (lum < 0.40)
for sgn in (1, -1):
    ragged |= (FC[:, 0] * sgn > cuff[sgn] - 0.06) & (b - r < 0.06)
_n0 = int(drop.sum())
for _ in range(12):
    vd = np.zeros(len(me.vertices), bool)
    vd[_lv[drop[_lf]]] = True
    touch = np.zeros(len(FC), bool)
    touch[_lf[vd[_lv]]] = True
    new = touch & ragged & ~drop
    if not new.any():
        break
    drop |= new
print("RIMTRIM", int(drop.sum()) - _n0, flush=True)
rep["cut"] = {"rim_trim_faces": int(drop.sum()) - _n0,"faces": int(len(FC)), "dropped": int(drop.sum()), "collar_top_z": round(float(collar_top), 3),
              "neck_skin_low_z": round(float(neck_skin_low), 3), "cuff_x": {str(k): round(float(v), 3) for k, v in cuff.items()},
              "skin_faces_left": int((skin & ~drop).sum())}
reg = (ax > 0.3) & (ax < 0.62)
rep["cut"]["arm_region"] = {"faces": int(reg.sum()), "by_head": int((reg & head).sum()), "by_hands": int((reg & hands).sum()),
                            "by_skin": int((reg & skin & (FC[:, 2] > 1.25)).sum()), "x_of_skin_drops": [round(float(v), 2) for v in np.percentile(ax[reg & skin], [0, 50, 100])] if (reg & skin).any() else []}
print("ARMCUT", rep["cut"]["arm_region"], flush=True)
bm = bmesh.new()
bm.from_mesh(me)
bm.faces.ensure_lookup_table()
bmesh.ops.delete(bm, geom=[bm.faces[i] for i in np.nonzero(drop)[0]], context="FACES")
# keep parts of at least 300 faces; smaller islands are scraps of the cut
bm.faces.ensure_lookup_table()
seen, small = set(), []
for f in bm.faces:
    if f.index in seen:
        continue
    comp, stack = [], [f]
    seen.add(f.index)
    while stack:
        q = stack.pop()
        comp.append(q)
        for e in q.edges:
            for n in e.link_faces:
                if n.index not in seen:
                    seen.add(n.index)
                    stack.append(n)
    if len(comp) < 300:
        small += comp
rep["cut"]["scrap_faces_removed"] = len(small)
sx = np.array([abs(f.calc_center_median().x) for f in small]) if small else np.zeros(0)
rep["cut"]["scrap_in_arm_region"] = int(((sx > 0.3) & (sx < 0.62)).sum())
print("SCRAP", len(small), "in arm region", rep["cut"]["scrap_in_arm_region"], flush=True)
bmesh.ops.delete(bm, geom=small, context="FACES")
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
bm.to_mesh(me)
bm.free()
me.update()

scene = bpy.context.scene
try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError:
    scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = scene.render.resolution_y = 900
world = bpy.data.worlds.new("w")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.7, 0.7, 0.7, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 1.2
scene.world = world
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
sun.data.energy = 3
sun.rotation_euler = (math.radians(55), 0, math.radians(-25))
scene.collection.objects.link(sun)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
cam.data.type = "ORTHO"
cam.data.ortho_scale = 2.0
scene.collection.objects.link(cam)
scene.camera = cam
skinm = bpy.data.materials.new("skin")
skinm.diffuse_color = (0.8, 0.5, 0.4, 1)
skinm.use_nodes = True
next(n for n in skinm.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"].default_value = (0.8, 0.45, 0.35, 1)
body.data.materials.clear()
body.data.materials.append(skinm)


def shots(tag):
    for name, loc, rot in (("front", (0, -4, 0.93), (90, 0, 0)), ("back", (0, 4, 0.93), (90, 0, 180)), ("side", (4, 0, 0.93), (90, 0, 90)), ("top", (0, 0, 5), (0, 0, 0))):
        cam.location = loc
        cam.rotation_euler = tuple(math.radians(a) for a in rot)
        scene.render.filepath = str(out / f"check_{tag}_{name}.png")
        bpy.ops.render.render(write_still=True)
    # Costume alone from the front: a hole here is missing faces, a hole only in the shots with the body is the body
    # coming through the cloth.
    body.hide_render = True
    cam.location, cam.rotation_euler = (0, -4, 0.93), (math.radians(90), 0, 0)
    scene.render.filepath = str(out / f"check_{tag}_front_costume_only.png")
    bpy.ops.render.render(write_still=True)
    body.hide_render = False
    cam.data.ortho_scale = 0.6
    for name, z in (("crotch", 0.92), ("belt", 1.1), ("collar", 1.52)):
        cam.location = (0, -4, z)
        scene.render.filepath = str(out / f"check_{tag}_close_{name}.png")
        bpy.ops.render.render(write_still=True)
    for name, loc, rot in (("arm_r_front", (-0.47, -4, 1.4), (90, 0, 0)), ("arm_r_top", (-0.47, 0, 5), (0, 0, 0))):
        cam.location, cam.rotation_euler = loc, tuple(math.radians(a) for a in rot)
        scene.render.filepath = str(out / f"check_{tag}_close_{name}.png")
        bpy.ops.render.render(write_still=True)
    cam.data.ortho_scale = 2.0


# ---- 4. weights from the posed body, then back to the rest pose ------------------------------------------------
CP = np.array([v.co[:] for v in me.vertices])
CP0 = CP.copy()
E = np.array([e.vertices[:] for e in me.edges])


RAYS = [Vector(v).normalized() for v in ((0.31, 0.87, 0.38), (-0.52, -0.41, 0.75), (0.63, -0.22, -0.74))]


def nearest(P):
    W = np.zeros((len(P), len(bones)), dtype=np.float32)
    dist, LOC, NRM = np.zeros(len(P)), np.zeros((len(P), 3)), np.zeros((len(P), 3))
    for i, p in enumerate(P):
        loc, nrm, fi, d = bvh.find_nearest(Vector(p))
        t = BT[fi]
        a, bb, c = BP[t[0]], BP[t[1]], BP[t[2]]
        v0, v1, v2 = bb - a, c - a, np.array(loc) - a
        d00, d01, d11, d20, d21 = v0 @ v0, v0 @ v1, v1 @ v1, v2 @ v0, v2 @ v1
        den = d00 * d11 - d01 * d01 or 1e-12
        bv = (d11 * d20 - d01 * d21) / den
        bw = (d00 * d21 - d01 * d20) / den
        W[i] = (1 - bv - bw) * BW[t[0]] + bv * BW[t[1]] + bw * BW[t[2]]
        # Inside or outside by ray parity, two of three rays. The triangle normal is not reliable where the posed
        # body folds on itself (straightened elbow), and it left holes there. NRM is the way out through LOC.
        votes = 0
        for ray in RAYS:
            n_hit, start = 0, Vector(p)
            while True:
                hit = bvh.ray_cast(start, ray, 3.0)
                if hit[0] is None:
                    break
                n_hit += 1
                start = hit[0] + ray * 1e-5
            votes += n_hit % 2
        inside = votes >= 2
        away = np.array(loc) - p if inside else p - np.array(loc)
        ln = np.linalg.norm(away)
        LOC[i], NRM[i] = loc, (away / ln if ln > 1e-7 else BN[fi])
        dist[i] = -d if inside else d
    return W, dist, LOC, NRM


def smooth(F, n):
    for _ in range(n):
        acc, cnt = F.copy(), np.ones(len(F))
        np.add.at(acc, E[:, 0], F[E[:, 1]])
        np.add.at(acc, E[:, 1], F[E[:, 0]])
        np.add.at(cnt, E[:, 0], 1)
        np.add.at(cnt, E[:, 1], 1)
        F = acc / cnt[:, None]
    return F


CW, dist, LOC, NRM = nearest(CP)
before = {"inside_over_5mm_pct": round(float((dist < -0.005).mean()) * 100, 2), "gap_median_mm": round(float(np.median(dist)) * 1000, 1)}
# The MetaHuman body is more muscular than the dressed figure, so part of the costume lies inside it. Push those
# vertices out to MARGIN above the body surface and taper the push into their neighbours.
MARGIN = 0.005
# First pass along the costume's own outward normal, so a vertex deep inside a limb leaves on its own side. The
# nearest-surface push alone sent such vertices out through the opposite wall and left holes at the elbows.
me.update()
CN = np.array([v.normal[:] for v in me.vertices])
# Arms first, by radius from the shoulder-to-wrist axis: a ray from the axis out through the vertex, farthest body hit.
# The straightened elbow folds the body mesh on itself, so both the triangle normal and ray parity misjudge inside
# there, and the sleeve ended under the skin at the front of the elbow (v8: costume intact alone, body through it).
def centre_line(a0, a1, P, S=None):
    """Origin on a limb's own centre line for each point of P: the centre of the source points S (the posed body by
    default) in the 1 cm slab at the point's place along the axis. The joint axis itself is 1 to 2 cm off the centre
    of the flesh, and a ray from there misjudges the skin on one side."""
    S = BP if S is None else S
    L = np.linalg.norm(a1 - a0)
    ad = (a1 - a0) / L
    tb = (S - a0) @ ad
    fb = a0 + tb[:, None] * ad
    near = np.linalg.norm(S - fb, axis=1) < 0.13
    n = int(1.1 * L / 0.01) + 1
    off = np.zeros((n, 3))
    for k in range(n):
        m = near & (tb >= k * 0.01 - 0.005) & (tb < k * 0.01 + 0.015)
        if m.sum() > 8:
            q = S[m] - fb[m]
            off[k] = (q.max(0) + q.min(0)) / 2
        elif k:
            off[k] = off[k - 1]
    # Smooth the centre line along the limb and read it by interpolation. Raw 1 cm slabs jitter with every wrinkle, and
    # reading the nearest slab moved neighbouring rings of the sleeve by different amounts, which crumpled it.
    ker = np.exp(-np.arange(-9, 10) ** 2 / (2 * 3.0 ** 2))
    ker /= ker.sum()
    off = np.stack([np.convolve(np.pad(off[:, k], 9, mode="edge"), ker, mode="valid") for k in range(3)], 1)
    t = (P - a0) @ ad
    x = np.clip(t / 0.01, 0, n - 1.001)
    k0 = x.astype(int)
    fr = (x - k0)[:, None]
    foot = a0 + t[:, None] * ad + off[k0] * (1 - fr) + off[k0 + 1] * fr
    return L, t, foot, off


def envelope(P, mag, reach=0.04, sigma=0.025, cell=0.015):
    """Upper envelope of `mag` over points P: the largest value within `reach`, then a Gaussian blur. In 1.5 cm cells."""
    keys, inv = np.unique(np.floor(P / cell).astype(np.int64), axis=0, return_inverse=True)
    inv = inv.ravel()
    nc = len(keys)
    cnt = np.bincount(inv, minlength=nc).astype(float)
    cpos = np.stack([np.bincount(inv, P[:, k], nc) / cnt for k in range(3)], 1)
    cmax = np.zeros(nc)
    np.maximum.at(cmax, inv, mag)
    cdil, cenv = np.zeros(nc), np.zeros(nc)
    for c0 in range(0, nc, 400):
        d2 = ((cpos[c0:c0 + 400, None, :] - cpos[None, :, :]) ** 2).sum(2)
        cdil[c0:c0 + 400] = np.where(d2 < reach ** 2, cmax[None, :], 0).max(1)
    for c0 in range(0, nc, 400):
        d2 = ((cpos[c0:c0 + 400, None, :] - cpos[None, :, :]) ** 2).sum(2)
        wgt = np.exp(-d2 / (2 * sigma ** 2)) * cnt[None, :]
        cenv[c0:c0 + 400] = (wgt * cdil[None, :]).sum(1) / wgt.sum(1)
    return cenv[inv]


# Sleeves as tubes: each sleeve vertex keeps its direction and radius about the sleeve's own centre line and is put
# on the arm's centre line, no closer than MARGIN above the skin. A push from the arm's centre alone tore the sleeve
# where it lay deep in the arm, because vertices near the centre left in unrelated directions.
armv = np.zeros(len(CP), bool)
WA = np.zeros(len(CP))      # how much of a vertex belongs to the sleeve tube: 0 torso, 1 sleeve, between at the shoulder
TUBE = CP.copy()            # where the tube map alone puts it
TREL = np.full(len(CP), -1.0)  # place along the arm, 0 shoulder joint to 1 wrist joint
arm_pushed = 0
for sfx, (a0, a1) in ARM_AX.items():
    L, t, bfoot, off = centre_line(a0, a1, CP)
    _, _, cfoot, coff = centre_line(a0, a1, CP, CP)
    before["centre_off_axis_cm_" + sfx] = [round(float(np.linalg.norm(off[int(f * L / 0.01)])) * 100, 1) for f in (0.2, 0.4, 0.5, 0.6, 0.8)]
    before["sleeve_off_arm_cm_" + sfx] = [round(float(np.linalg.norm((coff - off)[int(f * L / 0.01)])) * 100, 1) for f in (0.2, 0.4, 0.5, 0.6, 0.8)]
    rc = np.linalg.norm(CP - cfoot, axis=1)
    axis_r = np.linalg.norm(CP - (a0 + t[:, None] * (a1 - a0) / L), axis=1)
    sel = (t > 0.15 * L) & (t < 1.05 * L) & (axis_r < 0.13) & (rc > 1e-5)
    ramp = np.clip((t - 0.15 * L) / (0.20 * L), 0, 1)
    armv |= sel & (ramp >= 1)
    si = np.nonzero(sel)[0]
    U = (CP[si] - cfoot[si]) / rc[si][:, None]
    FAR = np.zeros(len(si))
    for k, i in enumerate(si):
        o, u = Vector(bfoot[i]), Vector(U[k])
        start, left, far = o.copy(), 0.15, 0.0
        while left > 0:
            hit = bvh.ray_cast(start, u, left)
            if hit[0] is None:
                break
            far = (hit[0] - o).length
            step = (hit[0] - start).length + 1e-4
            start, left = hit[0] + u * 1e-4, left - step
        FAR[k] = far
    extra = np.maximum(FAR + MARGIN - rc[si], 0)
    arm_pushed += int((extra > 0).sum())
    # the same upper envelope as on the torso, so the sleeve does not copy the biceps and the deltoid
    # One smooth radial field for the whole sleeve. A per-vertex minimum radius put both sides of every fold on the same
    # shell, which crumpled the sleeve into overlapping triangles.
    env = envelope(CP[si], np.minimum(extra, np.percentile(extra, 98)), reach=0.08, sigma=0.045)  # bridges deltoid to biceps
    extra = np.where(env > 0.0005, env + 0.002, 0.0)
    before["sleeve_extra_radius_mm_" + sfx] = [round(float(x) * 1000, 1) for x in np.percentile(extra, [50, 95, 100])]
    target = bfoot[si] + U * (rc[si] + extra)[:, None]
    TUBE[si], WA[si] = target, ramp[si]
    TREL[si] = t[si] / L
    CP[si] = CP[si] + ramp[si][:, None] * (target - CP[si])
before["arm_vertices"] = int(armv.sum())
before["arm_pushed_by_radius"] = arm_pushed
CW, dist, LOC, NRM = nearest(CP)
dist[armv] = 1.0  # the arms are settled; the passes below leave them alone
moved = np.zeros((len(CP), 3))
rayed = 0
for i in np.nonzero(dist < MARGIN)[0]:
    if CN[i] @ NRM[i] < 0.3:  # the normal points across the body, not out of it: leave it to the nearest push
        continue
    o, n, far = Vector(CP[i]), Vector(CN[i]), None
    start, left = o.copy(), 0.045
    while left > 0:
        hit = bvh.ray_cast(start, n, left)
        if hit[0] is None:
            break
        far = hit[0]
        step = (far - start).length + 1e-4
        start, left = far + n * 1e-4, left - step
    if far is not None:
        moved[i] = np.array(far + n * MARGIN) - CP[i]
        rayed += 1
CP = CP + np.where(armv[:, None], 0.0, np.where((np.abs(moved).sum(1) > 0)[:, None], moved, smooth(moved, 4)))
CW, dist, LOC, NRM = nearest(CP)
dist[armv] = 1.0
before["moved_along_own_normal"] = rayed
for _ in range(3):
    need = np.where((dist < MARGIN)[:, None], LOC + NRM * MARGIN - CP, 0.0)
    soft = smooth(need, 4)
    CP = CP + np.where(armv[:, None], 0.0, np.where((dist < MARGIN)[:, None], need, soft))
    CW, dist, LOC, NRM = nearest(CP)
    dist[armv] = 1.0
# Whole-body cover, driven by the measurement itself: a skin vertex with no cloth outside it and cloth up to 3 cm
# beneath it lifts that cloth triangle above the skin. Skin that has no cloth beneath (neck, hands) is left alone.
# The pushes above move each vertex on its own, which sent single vertices out as spikes (collar, belt) and pushed the
# tunic through the belt that lies over it. Make the displacement a field in space: median, then Gaussian, over the
# neighbours in the source positions, so layers that lie together move together.
from mathutils import kdtree
kd0 = kdtree.KDTree(len(CP0))
for i, q in enumerate(CP0):
    kd0.insert(Vector(q), i)
kd0.balance()
Dsp = CP - CP0
NB = [None] * len(CP0)
for i in np.nonzero(~armv)[0]:
    r = kd0.find_range(Vector(CP0[i]), 0.02)
    NB[i] = (np.array([j for _, j, _ in r]), np.array([d for _, _, d in r]))
Dm = Dsp.copy()
for i in np.nonzero(~armv)[0]:
    j, d = NB[i]
    Dm[i] = np.median(Dsp[j[d < 0.015]], axis=0)
Dg = Dm.copy()
for i in np.nonzero(~armv)[0]:
    j, d = NB[i]
    w = np.exp(-(d / 0.01) ** 2 / 2)
    Dg[i] = (Dm[j] * w[:, None]).sum(0) / w.sum()
rep["field"] = {"spike_vertices_over_1cm": int((np.linalg.norm(Dsp - Dg, axis=1)[~armv] > 0.01).sum()),
                "max_change_cm": round(float(np.linalg.norm(Dsp - Dg, axis=1)[~armv].max()) * 100, 1)}
print("FIELD", rep["field"], flush=True)
# Torso drape: where the push follows the body exactly, the cloth copies every muscle. Raise the push on the torso to
# its own upper envelope over about 4 cm (largest push nearby, then blurred), so the tunic keeps the shape it had on
# the dressed figure, moved out as a whole, and bridges the hollows between the muscles.
torso = ~armv & (CP0[:, 2] > 0.95)
ti = np.nonzero(torso)[0]
mag = np.linalg.norm(Dg[ti], axis=1)
keys, inv = np.unique(np.floor(CP0[ti] / 0.015).astype(np.int64), axis=0, return_inverse=True)
inv = inv.ravel()
nc = len(keys)
cnt = np.bincount(inv, minlength=nc).astype(float)
cpos = np.stack([np.bincount(inv, CP0[ti][:, k], nc) / cnt for k in range(3)], 1)
cvec = np.stack([np.bincount(inv, Dg[ti][:, k], nc) / cnt for k in range(3)], 1)
cmax = np.zeros(nc)
np.maximum.at(cmax, inv, mag)
cmax = np.minimum(cmax, np.percentile(mag, 95))
cdil, cenv, cdir = np.zeros(nc), np.zeros(nc), np.zeros((nc, 3))
for a0_ in range(0, nc, 400):
    d2 = ((cpos[a0_:a0_ + 400, None, :] - cpos[None, :, :]) ** 2).sum(2)
    cdil[a0_:a0_ + 400] = np.where(d2 < 0.07 ** 2, cmax[None, :], 0).max(1)
for a0_ in range(0, nc, 400):
    d2 = ((cpos[a0_:a0_ + 400, None, :] - cpos[None, :, :]) ** 2).sum(2)
    wgt = np.exp(-d2 / (2 * 0.04 ** 2)) * cnt[None, :]
    cenv[a0_:a0_ + 400] = (wgt * cdil[None, :]).sum(1) / wgt.sum(1)
    cdir[a0_:a0_ + 400] = wgt @ cvec
cdir /= np.maximum(np.linalg.norm(cdir, axis=1), 1e-9)[:, None]
ramp_t = np.clip((CP0[ti][:, 2] - 0.95) / 0.1, 0, 1) * np.clip((neck_skin_low - CP0[ti][:, 2]) / 0.03 + 1, 0, 1)  # not the collar
want = ramp_t * cenv[inv]
lift = np.maximum(want - (Dg[ti] * cdir[inv]).sum(1), 0)
Dg[ti] += cdir[inv] * lift[:, None]
rep["drape"] = {"torso_vertices": int(len(ti)), "cells": int(nc), "push_median_mm": round(float(np.median(mag)) * 1000, 1),
                "push_p95_mm": round(float(np.percentile(mag, 95)) * 1000, 1), "envelope_median_mm": round(float(np.median(cenv[inv])) * 1000, 1),
                "lift_median_mm": round(float(np.median(lift)) * 1000, 1), "lift_max_mm": round(float(lift.max()) * 1000, 1)}
print("DRAPE", rep["drape"], flush=True)
# Shoulder: blend the field result into the tube map by the sleeve weight, so the two meet without a step.
CP = WA[:, None] * TUBE + (1 - WA[:, None]) * (CP0 + Dg)
me.calc_loop_triangles()
CT = [tuple(t.vertices) for t in me.loop_triangles]
skin_out = np.array([bvh.ray_cast(Vector(BP[j]) + Vector(BVN[j]) * 1e-4, Vector(BVN[j]), 0.02)[0] is None for j in range(len(BP))])
cover_log = []
for it in range(8):
    cbvh = BVHTree.FromPolygons([Vector(q) for q in CP], CT)
    kdc = kdtree.KDTree(len(CP))
    for i, q in enumerate(CP):
        kdc.insert(Vector(q), i)
    kdc.balance()
    need = np.zeros((len(CP), 3))
    amt = np.zeros(len(CP))
    bare_z = []
    for j in np.nonzero(skin_out)[0]:
        o, n = Vector(BP[j]), Vector(BVN[j])
        if cbvh.ray_cast(o, n, 0.15)[0] is not None:
            continue
        hit = cbvh.ray_cast(o, -n, 0.03)
        if hit[0] is None:
            continue
        d = (hit[0] - o).length + MARGIN
        bare_z.append(BP[j][2])
        for _, v, _ in kdc.find_range(hit[0], 0.015):  # every layer near the hit moves with it
            if d > amt[v]:
                amt[v], need[v] = d, BVN[j] * d
    hist = np.histogram(bare_z, bins=[0, 0.5, 0.8, 0.95, 1.1, 1.3, 1.5, 2.0])[0].tolist() if bare_z else []
    cover_log.append({"bare": len(bare_z), "by_height": hist})
    print("COVER", it, len(bare_z), hist, flush=True)
    if not bare_z or it == 7:
        break
    CP = CP + np.where((amt > 0)[:, None], need, smooth(need, 2))
rep["cover_fix"] = cover_log
CW, dist, LOC, NRM = nearest(CP)
me.vertices.foreach_set("co", CP.ravel())
me.update()
# Underlayer: the skin that lies under or beside the cloth, to be copied 2 mm out as a plain cloth-coloured layer with
# the body's own weights. The source costume has real openings (tunic front, under the hem), and skin shows there.
cbvh = BVHTree.FromPolygons([Vector(q) for q in CP], CT)
_ex = [i for i, n in enumerate(bones) if any(k in n.lower() for k in ("hand", "thumb", "index", "middle", "ring", "pinky", "head", "facial"))]
_wex = BW[:, _ex].sum(1)
STOCK = np.zeros(len(BP), bool)
for j in np.nonzero(_wex < 0.5)[0]:
    o = Vector(BP[j])
    STOCK[j] = cbvh.find_nearest(o, 0.015)[0] is not None or cbvh.ray_cast(o, Vector(BVN[j]), 0.06)[0] is not None
# Close small gaps in the selection, then pull its border back about 2 cm, so the layer ends under the collar and
# inside the cuffs and does not show as a jagged dark edge on the neck and wrists.
if len(body.data.vertices) == len(STOCK):
    BE = np.array([e.vertices[:] for e in body.data.edges])
    for grow in (True, True, False, False, False, False, False):
        other = np.zeros(len(STOCK), bool)
        src = STOCK if grow else ~STOCK
        other[BE[src[BE[:, 0]], 1]] = True
        other[BE[src[BE[:, 1]], 0]] = True
        STOCK = (STOCK | other) & (_wex < 0.5) if grow else STOCK & ~other
rep["underlayer"] = {"body_vertices": int(len(BP)), "selected": int(STOCK.sum())}
# Coverage of the posed arms: for each body vertex, is there cloth outside it along the ray from the arm axis, and if
# not, how deep under the skin is the cloth.
me.calc_loop_triangles()
cbvh = BVHTree.FromPolygons([Vector(p) for p in CP], [tuple(t.vertices) for t in me.loop_triangles])
cover = {}
for sfx, (a0, a1) in ARM_AX.items():
    L, t, foot, off = centre_line(a0, a1, BP)
    rad = np.linalg.norm(BP - foot, axis=1)
    bins = {}
    for i in np.nonzero((t > 0.15 * L) & (t < 0.95 * L) & (rad < 0.13) & (rad > 1e-4))[0]:
        u = Vector((BP[i] - foot[i]) / rad[i])
        # only the outer skin: nothing of the body further out along the ray
        if bvh.ray_cast(Vector(BP[i]) + u * 1e-4, u, 0.15)[0] is not None:
            continue
        k = int(10 * t[i] / L)
        e = bins.setdefault(k, {"skin": 0, "bare": 0, "under_mm": []})
        e["skin"] += 1
        if cbvh.ray_cast(Vector(BP[i]), u, 0.15)[0] is None:
            e["bare"] += 1
            inner = cbvh.ray_cast(Vector(BP[i]), -u, rad[i])
            e["under_mm"].append(1000 * (inner[0] - Vector(BP[i])).length if inner[0] is not None else -1)
    cover[sfx] = {k: {"skin": e["skin"], "bare": e["bare"], "no_cloth_at_all": int(sum(1 for x in e["under_mm"] if x < 0)),
                      "under_mm_median": round(float(np.median([x for x in e["under_mm"] if x >= 0])), 1) if any(x >= 0 for x in e["under_mm"]) else None}
                  for k, e in sorted(bins.items())}
rep["arm_cover"] = cover
print("ARMCOVER", json.dumps(cover), flush=True)
shots("posed")
# smooth the weights over the costume's own edges so neighbouring vertices do not jump between limbs
CW = smooth(CW, 30).astype(np.float32)  # 6 left the sleeve lumpy after the inverse skinning: weights from the nearest body point jump across muscle creases
# Elbow: measured in v24, the edges that change length most on the way back to the rest pose all lie at 0.4 to 0.6 of
# the arm, between upperarm_twistCor_02 and lowerarm_twist_02. The body's narrow elbow blend relies on corrective bones
# that this script does not drive, so the sleeve folded there. Widen the blend on the sleeve to a few centimetres.
def widen_blend(zone, fade, passes=150):
    """Diffuse the weights over the costume's own edges inside `zone`; `fade` (0 to 1 per zone vertex) holds the border."""
    global CW
    zi = np.nonzero(zone)[0]
    loc_of = -np.ones(len(CW), dtype=np.int64)
    loc_of[zi] = np.arange(len(zi))
    Ez = E[zone[E[:, 0]] & zone[E[:, 1]]]
    Ez = np.stack([loc_of[Ez[:, 0]], loc_of[Ez[:, 1]]], 1)
    Fz = CW[zi].astype(np.float64)
    fade = fade[:, None]
    for _ in range(passes):
        acc, cnt = Fz.copy(), np.ones(len(Fz))
        np.add.at(acc, Ez[:, 0], Fz[Ez[:, 1]])
        np.add.at(acc, Ez[:, 1], Fz[Ez[:, 0]])
        np.add.at(cnt, Ez[:, 0], 1)
        np.add.at(cnt, Ez[:, 1], 1)
        Fz = fade * (acc / cnt[:, None]) + (1 - fade) * Fz
    CW[zi] = Fz.astype(np.float32)


zone = (TREL > 0.25) & (TREL < 0.75)
widen_blend(zone, np.clip(np.minimum(TREL[zone] - 0.25, 0.75 - TREL[zone]) / 0.1, 0, 1))
# Shoulder: measured in v27, 89 of the 113 sleeve edges that gain more than 25 degrees of fold on the way back lie at
# 0.1 to 0.3 of the arm. Widening the weight blend there the same way was tried in v28 and made it worse (686 edges):
# the diffusion runs through the armpit and brings spine weights into the sleeve. Not applied.
# at most 8 influences
order = np.argsort(-CW, axis=1)[:, :8]
keep = np.zeros_like(CW)
np.put_along_axis(keep, order, np.take_along_axis(CW, order, 1), 1)
CW = keep / np.maximum(keep.sum(1), 1e-9)[:, None]
M = np.einsum("vb,bij->vij", CW, BM)
rest = np.einsum("vij,vj->vi", np.linalg.inv(M), np.c_[CP, np.ones(len(CP))])[:, :3]
# Where the way back to the rest pose is not smooth: sleeve edges whose length changes most, and the bones whose
# weights differ most across them.
el_p = np.linalg.norm(CP[E[:, 0]] - CP[E[:, 1]], axis=1)
el_r = np.linalg.norm(rest[E[:, 0]] - rest[E[:, 1]], axis=1)
ratio = el_r / np.maximum(el_p, 1e-9)
arm_e = (TREL[E[:, 0]] >= 0) & (TREL[E[:, 1]] >= 0) & (el_p > 1e-5)
bad = arm_e & ((ratio > 1.6) | (ratio < 0.6))
dW = np.abs(CW[E[bad, 0]] - CW[E[bad, 1]]).sum(0)
top = np.argsort(-dW)[:10]
mW = (CW[E[bad, 0]] + CW[E[bad, 1]]).sum(0)
topm = np.argsort(-mW)[:10]
rep["fold"] = {"arm_edges": int(arm_e.sum()), "bad_edges": int(bad.sum()),
               "ratio_percentiles_1_50_99": [round(float(x), 2) for x in np.percentile(ratio[arm_e], [1, 50, 99])],
               "bad_place_along_arm_hist_0_to_1": np.histogram(TREL[E[bad, 0]], bins=10, range=(0, 1))[0].tolist(),
               "all_place_along_arm_hist_0_to_1": np.histogram(TREL[E[arm_e, 0]], bins=10, range=(0, 1))[0].tolist(),
               "bones_weight_jump": {bones[i]: round(float(dW[i]), 1) for i in top},
               "bones_weight_mass": {bones[i]: round(float(mW[i]), 1) for i in topm}}
print("FOLD", json.dumps(rep["fold"]), flush=True)
# The same question for bending: edges whose fold angle differs most between the two poses.
TRI = np.array(CT)


def tri_normals(Q):
    nn = np.cross(Q[TRI[:, 1]] - Q[TRI[:, 0]], Q[TRI[:, 2]] - Q[TRI[:, 0]])
    return nn / np.maximum(np.linalg.norm(nn, axis=1), 1e-12)[:, None]


emap = {}
for fi, tr in enumerate(CT):
    for a_, b_ in ((tr[0], tr[1]), (tr[1], tr[2]), (tr[2], tr[0])):
        emap.setdefault((min(a_, b_), max(a_, b_)), []).append(fi)
pairs = np.array([(k[0], k[1], v[0], v[1]) for k, v in emap.items() if len(v) == 2])
Np, Nr = tri_normals(CP), tri_normals(rest)
ang_p = np.degrees(np.arccos(np.clip((Np[pairs[:, 2]] * Np[pairs[:, 3]]).sum(1), -1, 1)))
ang_r = np.degrees(np.arccos(np.clip((Nr[pairs[:, 2]] * Nr[pairs[:, 3]]).sum(1), -1, 1)))
arm_p = (TREL[pairs[:, 0]] >= 0) & (TREL[pairs[:, 1]] >= 0)
bent = arm_p & (ang_r - ang_p > 25)
dWb = np.abs(CW[pairs[bent, 0]] - CW[pairs[bent, 1]]).sum(0)
mWb = (CW[pairs[bent, 0]] + CW[pairs[bent, 1]]).sum(0)
rep["bend"] = {"arm_edges": int(arm_p.sum()), "bent_over_25deg": int(bent.sum()),
               "place_along_arm_hist_0_to_1": np.histogram(TREL[pairs[bent, 0]], bins=10, range=(0, 1))[0].tolist(),
               "sleeve_weight_hist_0_to_1": np.histogram(WA[pairs[bent, 0]], bins=5, range=(0, 1.0001))[0].tolist(),
               "bones_weight_jump": {bones[i]: round(float(dWb[i]), 1) for i in np.argsort(-dWb)[:8]},
               "bones_weight_mass": {bones[i]: round(float(mWb[i]), 1) for i in np.argsort(-mWb)[:8]}}
print("BEND", json.dumps(rep["bend"]), flush=True)
rep["weights"] = {"before_push": before, "vertices": int(len(CP)), "inside_body_over_5mm_pct": round(float((dist < -0.005).mean()) * 100, 2),
                  "inside_body_over_15mm_pct": round(float((dist < -0.015).mean()) * 100, 2),
                  "gap_median_mm": round(float(np.median(dist)) * 1000, 1), "gap_p95_mm": round(float(np.percentile(dist, 95)) * 1000, 1),
                  "bones_used": int((CW.sum(0) > 1e-4).sum())}

# rest pose, in the body mesh's local frame, bound to the armature
for pb in arm.pose.bones:
    pb.matrix_basis = Matrix.Identity(4)
bpy.context.view_layer.update()
Li = np.array(body.matrix_world.inverted())
local = (np.c_[rest, np.ones(len(rest))] @ Li.T)[:, :3]
me.vertices.foreach_set("co", local.ravel())
me.update()
dr.name = me.name = "hero01_costume"
dr.parent = body.parent
dr.matrix_world = body.matrix_world.copy()
for i, n in enumerate(bones):
    col = CW[:, i]
    nz = np.nonzero(col > 1e-4)[0]
    if len(nz):
        vg = dr.vertex_groups.new(name=n)
        for v in nz:
            vg.add([int(v)], float(col[v]), "REPLACE")
mod = dr.modifiers.new("Armature", "ARMATURE")
mod.object = arm
# underlayer mesh from the rest body, joined into the costume
if len(body.data.vertices) == len(STOCK):
    k_loc = 0.002 / body.matrix_world.to_scale()[0]
    ids = np.nonzero(STOCK)[0]
    remap = {int(v): i for i, v in enumerate(ids)}
    sv = [tuple(body.data.vertices[int(v)].co + body.data.vertices[int(v)].normal * k_loc) for v in ids]
    sf = [tuple(remap[v] for v in pl.vertices) for pl in body.data.polygons if all(STOCK[v] for v in pl.vertices)]
    sm = bpy.data.meshes.new("underlayer")
    sm.from_pydata(sv, [], sf)
    sm.update()
    ul = sm.uv_layers.new(name=me.uv_layers.active.name)
    for l in ul.data:
        l.uv = STOCK_UV
    sm.materials.append(mat)
    so = bpy.data.objects.new("underlayer", sm)
    scene.collection.objects.link(so)
    so.parent = dr.parent
    so.matrix_world = dr.matrix_world.copy()
    for n in bones:
        gi = body.vertex_groups[n].index
        vg = None
        for v in ids:
            for g in body.data.vertices[int(v)].groups:
                if g.group == gi and g.weight > 1e-4:
                    vg = vg or so.vertex_groups.new(name=n)
                    vg.add([remap[int(v)]], g.weight, "REPLACE")
    bpy.ops.object.select_all(action="DESELECT")
    so.select_set(True)
    dr.select_set(True)
    bpy.context.view_layer.objects.active = dr
    bpy.ops.object.join()
    me = dr.data
    rep["underlayer"]["faces"] = len(sf)
else:
    rep["underlayer"]["skipped"] = "rest and posed body vertex counts differ"
print("UNDERLAYER", rep["underlayer"], flush=True)
for img in bpy.data.images:
    if img.size[0] and img.name.split("_")[0] in ("Color", "NormalGL", "ORM"):
        img.filepath_raw = str(out / f"hero01_costume_{img.name.split('_')[0]}.png")
        img.file_format = "PNG"
        img.save()
mat.name = "M_Hero01_Costume"

# rest-pose check against the rest body
dg = bpy.context.evaluated_depsgraph_get()
dg.update()
RB = body_pts()
RC = world_pts(dr)
rep["rest"] = {"costume_lo_m": [round(float(x), 3) for x in RC.min(0)], "costume_hi_m": [round(float(x), 3) for x in RC.max(0)],
               "body_lo_m": [round(float(x), 3) for x in RB.min(0)], "body_hi_m": [round(float(x), 3) for x in RB.max(0)]}

# ---- 5. check renders: rest pose, costume over the body ----
shots("rest")

# ---- 6. export -------------------------------------------------------------------------------------------------
bpy.ops.object.select_all(action="DESELECT")
for o in (dr, arm, body.parent):
    if o:
        o.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.fbx(filepath=str(out / "hero01_costume.fbx"), use_selection=True, object_types={"ARMATURE", "MESH", "EMPTY"},
                         add_leaf_bones=False, bake_anim=False, mesh_smooth_type="FACE", path_mode="COPY", embed_textures=False)
(out / "costume_report.json").write_text(json.dumps(rep, indent=1, default=float))
print("REPORT", json.dumps(rep, default=float))

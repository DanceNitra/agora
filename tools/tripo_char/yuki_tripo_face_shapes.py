"""Path T, step 1: puts the 51 ARKit expressions of Yuki's MetaHuman face onto the dressed Tripo model's head as
shape keys, so the Tripo face (its make-up and eyes, which the owner prefers) can move.

    ./blender_headless.sh yuki_tripo_face_shapes.py -- <dressed.glb> <arkit_dir> <out_dir>

arkit_dir holds face_000.txt .. face_052.txt and face_tris.txt from ue_face_arkit_export.py: the MetaHuman face mesh
in Unreal component space (cm, faces +Y), frame k = pose k of PA_MetaHuman_ARKit_Mapping (0 = neutral). The MetaHuman
skin (its largest connected part) is aligned to the Tripo face (eye centres, then rigid ICP with uniform scale on the
face), and every Tripo head vertex near that skin takes the expression offsets of its nearest skin point
(barycentric), fading to zero between NEAR and FAR metres from the skin. Writes yuki_tripo_head_shapes.blend (head
only, with shape keys), align.json and check renders of a few expressions.
SURGERY=1 (default) also opens the face where the MetaHuman skin is open: the lip slit (Tripo triangles whose
corners map to the MetaHuman upper lip and lower lip at once) and the two eye openings (Tripo faces inside the
MetaHuman lid margin, seen from the front). The MetaHuman eyeballs, teeth, tongue, gums and mouth cavity are added as
a second object with the same shape keys; the eyeballs take the Tripo painted eye as their texture (front projection).
Without it (SURGERY=0) the Tripo eyes and mouth stay one closed painted surface: a blink drags the painted iris and an
open jaw stretches the lips (measured 2026-11-14, sheet T1)."""
import json
import math
import os
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

glb, adir, out = sys.argv[-3], Path(sys.argv[-2]), Path(sys.argv[-1]).resolve()
out.mkdir(parents=True, exist_ok=True)
NEAR, FAR = float(os.environ.get("NEAR", 0.004)), float(os.environ.get("FAR", 0.012))
NAMES = ['Default', 'EyeBlinkLeft', 'EyeLookDownLeft', 'EyeLookInLeft', 'EyeLookOutLeft', 'EyeLookUpLeft',
         'EyeSquintLeft', 'EyeWideLeft', 'EyeBlinkRight', 'EyeLookDownRight', 'EyeLookInRight', 'EyeLookOutRight',
         'EyeLookUpRight', 'EyeSquintRight', 'EyeWideRight', 'JawForward', 'JawLeft', 'JawRight', 'JawOpen',
         'MouthFunnel', 'MouthPucker', 'MouthLeft', 'MouthRight', 'MouthSmileLeft', 'MouthSmileRight',
         'MouthFrownLeft', 'MouthFrownRight', 'MouthDimpleLeft', 'MouthDimpleRight', 'MouthStretchLeft',
         'MouthStretchRight', 'MouthRollLower', 'MouthRollUpper', 'MouthShrugLower', 'MouthShrugUpper',
         'MouthPressLeft', 'MouthPressRight', 'MouthLowerDownLeft', 'MouthLowerDownRight', 'MouthUpperUpLeft',
         'MouthUpperUpRight', 'BrowDownLeft', 'BrowDownRight', 'BrowInnerUp', 'BrowOuterUpLeft', 'BrowOuterUpRight',
         'CheekPuff', 'CheekSquintLeft', 'CheekSquintRight', 'NoseSneerLeft', 'NoseSneerRight', 'TongueOut']

# --- the dressed Tripo model, stood as in yuki_dressed_head_probe (facing -Y, soles on z = 0) ---------------------
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(Path(glb).resolve()))
dr = max((o for o in bpy.data.objects if o.type == "MESH"), key=lambda o: len(o.data.vertices))
for o in list(bpy.data.objects):
    if o is not dr:
        bpy.data.objects.remove(o)
dr.data.transform(dr.matrix_world)
dr.parent = None
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
eyes = json.load(open(Path(__file__).resolve().parent / "models/yuki/dressed_head_probe/eyes.json"))
chin_z = float(eyes["chin_z"])
# keep the head and neck only (faces entirely above the chin minus 9 cm)
bm = bmesh.new()
bm.from_mesh(me)
cut = chin_z - 0.09
bmesh.ops.delete(bm, geom=[f for f in bm.faces if min(v.co.z for v in f.verts) < cut], context="FACES")
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
bm.to_mesh(me)
bm.free()
me.update()
dr.name = me.name = "yuki_tripo_head"
P = co(me)
print("HEAD verts", len(P), "faces", len(me.polygons), "z", round(P[:, 2].min(), 3), round(P[:, 2].max(), 3), flush=True)

# --- the MetaHuman face poses ------------------------------------------------------------------------------------
tris = np.loadtxt(adir / "face_tris.txt", dtype=np.int64)
poses = [np.loadtxt(adir / f"face_{k:03d}.txt") for k in range(len(NAMES))]
poses = [np.c_[p[:, 0], -p[:, 1], p[:, 2]] / 100.0 for p in poses]     # Unreal cm, +Y front -> Blender m, -Y front
nv = len(poses[0])
par = np.arange(nv)


def find(i):
    while par[i] != i:
        par[i] = par[par[i]]
        i = par[i]
    return i


for a, b, c in tris:
    for u, v in ((a, b), (b, c)):
        ru, rv = find(u), find(v)
        if ru != rv:
            par[ru] = rv
root = np.array([find(i) for i in range(nv)])
ids, counts = np.unique(root, return_counts=True)
comps = sorted(zip(counts, ids), reverse=True)
skin_id = comps[0][1]
skin_v = root == skin_id
print("MH components", len(comps), "largest", [int(c) for c, _ in comps[:8]], flush=True)
# eyeballs: components about 2.2 to 2.8 cm across
eye_c = []
for c, i in comps:
    pts = poses[0][root == i]
    ext = np.ptp(pts, axis=0)
    if 0.020 < ext.max() < 0.030 and ext.min() > 0.015:
        eye_c.append(pts.mean(0))
eye_c = sorted(eye_c, key=lambda p: p[0])[:2] if len(eye_c) >= 2 else eye_c
print("MH eyeball centres", [list(np.round(e, 4)) for e in eye_c], flush=True)
skin_tris = tris[skin_v[tris].all(1)]

# --- alignment: eye centres first, then ICP (rotation, translation, uniform scale) on the face --------------------
mid_tr = np.array([eyes["mid"][0], 0.0, eyes["mid"][1]])
bvh_tr = BVHTree.FromPolygons([Vector(v) for v in P], [tuple(p.vertices) for p in me.polygons])
hit = bvh_tr.ray_cast(Vector((mid_tr[0], -1.0, mid_tr[2] + 0.03)), Vector((0, 1, 0)))   # forehead surface
# scale from the eyes: Tripo iris distance over MetaHuman eyeball distance (the ICP keeps it; letting the ICP scale
# drifted to 1.13 on 2026-11-14 and put the lip cut under the Tripo lips)
s0 = float(eyes["iod"]) / float(np.linalg.norm(eye_c[1] - eye_c[0])) if len(eye_c) == 2 else 1.0 / float(eyes["scale"])
mh_mid = np.mean(eye_c, axis=0) if len(eye_c) == 2 else poses[0][skin_v].mean(0)
Pm = (poses[0] - mh_mid) * s0
# front of MetaHuman forehead to front of Tripo forehead
fh = Pm[skin_v & (np.abs(Pm[:, 0]) < 0.01) & (np.abs(Pm[:, 2] - 0.03) < 0.006)]
y_off = (hit[0].y if hit[0] else P[:, 1].min()) - fh[:, 1].min()
T = np.eye(4)
T[:3, :3] *= s0
T[:3, 3] = np.array([mid_tr[0], y_off, mid_tr[2]]) - mh_mid * s0
face_q = P[(np.abs(P[:, 0] - mid_tr[0]) < 0.055) & (P[:, 2] > chin_z) & (P[:, 2] < mid_tr[2] + 0.05) &
           (P[:, 1] < P[:, 1].min() + 0.06)]
rng = np.random.default_rng(3)
face_q = face_q[rng.choice(len(face_q), size=min(15000, len(face_q)), replace=False)]


def apply(Tm, X):
    return X @ Tm[:3, :3].T + Tm[:3, 3]


hist = []
for it in range(40):
    A_all = apply(T, poses[0])
    bvh_mh = BVHTree.FromPolygons([Vector(v) for v in A_all], [tuple(t) for t in skin_tris])
    near = np.array([bvh_mh.find_nearest(Vector(q))[0][:] for q in face_q])
    d = np.linalg.norm(near - face_q, axis=1)
    k = d < np.percentile(d, 80)
    A, B = near[k], face_q[k]
    ca, cb = A.mean(0), B.mean(0)
    U, S_, Vt = np.linalg.svd((A - ca).T @ (B - cb))
    R = Vt.T @ U.T
    if np.linalg.det(R) < 0:
        Vt[-1] *= -1
        R = Vt.T @ U.T
    sc = 1.0
    step = np.eye(4)
    step[:3, :3] = sc * R
    step[:3, 3] = cb - sc * R @ ca
    T = step @ T
    hist.append(round(float(np.median(d)) * 1000, 2))
print("ICP median mm", hist[::8] + hist[-1:], flush=True)
L = T[:3, :3]
A0 = apply(T, poses[0])
A0r = A0.copy()   # rigidly aligned MetaHuman rest pose, before the landmark warp (TEETH_RIGID)
CAM = {"cx": float(mid_tr[0]), "cz": float((mid_tr[2] + chin_z) / 2 + 0.01), "span": 0.17, "px": 1024}


def front_render(objs, path, emission_tex):
    """Orthographic front view of the given objects (others hidden) at CAM, for MediaPipe."""
    sc_ = bpy.context.scene
    try:
        sc_.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        sc_.render.engine = "BLENDER_EEVEE"
    sc_.render.resolution_x = sc_.render.resolution_y = CAM["px"]
    sc_.view_settings.view_transform = "Standard"
    if sc_.world is None:
        w_ = bpy.data.worlds.new("w")
        w_.use_nodes = True
        next(n_ for n_ in w_.node_tree.nodes if n_.type == "BACKGROUND").inputs["Strength"].default_value = 0.35
        sc_.world = w_
        sn = bpy.data.objects.new("lm_sun", bpy.data.lights.new("lm_sun", "SUN"))
        sn.data.energy = 3.5
        sn.rotation_euler = (math.radians(75), 0, math.radians(10))
        sc_.collection.objects.link(sn)
    cm = bpy.data.objects.get("lm_cam") or bpy.data.objects.new("lm_cam", bpy.data.cameras.new("lm_cam"))
    if cm.name not in sc_.collection.objects:
        sc_.collection.objects.link(cm)
    cm.data.type = "ORTHO"
    cm.data.ortho_scale = CAM["span"]
    cm.location = (CAM["cx"], -1.0, CAM["cz"])
    cm.rotation_euler = (math.pi / 2, 0, 0)
    sc_.camera = cm
    for o_ in sc_.objects:
        if o_.type == "MESH":
            o_.hide_render = o_ not in objs
    sc_.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


LM = os.environ.get("LM", "")
if os.environ.get("MODE", "") == "lm":
    # pass A: front renders of the Tripo head (its texture) and the aligned MetaHuman skin (grey, lit) for MediaPipe
    img0 = next((i_ for i_ in bpy.data.images if i_.size[0] and i_.name.lower().startswith("base")), None)
    m_t = bpy.data.materials.new("lm_tex")
    m_t.use_nodes = True
    ntt = m_t.node_tree
    for nd in list(ntt.nodes):
        if nd.type != "OUTPUT_MATERIAL":
            ntt.nodes.remove(nd)
    emn = ntt.nodes.new("ShaderNodeEmission")
    tx0 = ntt.nodes.new("ShaderNodeTexImage")
    tx0.image = img0
    ntt.links.new(tx0.outputs["Color"], emn.inputs["Color"])
    ntt.links.new(emn.outputs[0], next(nd for nd in ntt.nodes if nd.type == "OUTPUT_MATERIAL").inputs["Surface"])
    me.materials.clear()
    me.materials.append(m_t)
    mm = bpy.data.meshes.new("mh_skin")
    mm.from_pydata([tuple(v) for v in A0], [], [tuple(t) for t in skin_tris])
    mm.update()
    for pl in mm.polygons:
        pl.use_smooth = True
    mo = bpy.data.objects.new("mh_skin", mm)
    bpy.context.scene.collection.objects.link(mo)
    gm = bpy.data.materials.new("grey")
    gm.use_nodes = True
    next(n_ for n_ in gm.node_tree.nodes if n_.type == "BSDF_PRINCIPLED").inputs["Base Color"].default_value = (0.75, 0.62, 0.55, 1)
    mm.materials.append(gm)
    front_render([dr], out / "lm_tripo.png", True)
    front_render([mo], out / "lm_mh.png", False)
    json.dump(CAM, open(out / "lm_cam.json", "w"))
    print("LM renders written", flush=True)
    sys.exit(0)

WARP = {}
if LM:
    # pass C: thin-plate warp of the MetaHuman so its MediaPipe landmarks land on the Tripo face's landmarks
    lmj = json.load(open(LM))
    bvh_t0 = BVHTree.FromPolygons([Vector(v) for v in P], [tuple(p_.vertices) for p_ in me.polygons])
    bvh_m0 = BVHTree.FromPolygons([Vector(v) for v in A0], [tuple(t) for t in skin_tris])

    def to3d(bvh_, uv):
        x = CAM["cx"] + (uv[0] - 0.5) * CAM["span"]
        z = CAM["cz"] + (0.5 - uv[1]) * CAM["span"]
        h_ = bvh_.ray_cast(Vector((x, -1.0, z)), Vector((0, 1, 0)))
        return None if h_[0] is None else np.array(h_[0][:])

    src, dst = [], []
    for i_ in lmj["use"]:
        a_ = to3d(bvh_m0, lmj["mh"][i_])
        b_ = to3d(bvh_t0, lmj["tripo"][i_])
        if a_ is not None and b_ is not None and np.linalg.norm(a_ - b_) < 0.02:
            src.append(a_)
            dst.append(b_)
    src, dst = np.array(src), np.array(dst)

    def tps_fit(X, Y, lam=1e-6):
        n_ = len(X)
        K = np.linalg.norm(X[:, None] - X[None], axis=2)
        Pp = np.c_[np.ones(n_), X]
        M_ = np.zeros((n_ + 4, n_ + 4))
        M_[:n_, :n_] = K + lam * np.eye(n_)
        M_[:n_, n_:] = Pp
        M_[n_:, :n_] = Pp.T
        rhs = np.zeros((n_ + 4, 3))
        rhs[:n_] = Y
        return np.linalg.solve(M_, rhs)

    def tps_apply(X, C, Z):
        K = np.linalg.norm(Z[:, None] - X[None], axis=2)
        return K @ C[:len(X)] + np.c_[np.ones(len(Z)), Z] @ C[len(X):]

    Cw = tps_fit(src, dst)
    A0 = np.vstack([tps_apply(src, Cw, A0[i_:i_ + 4000]) for i_ in range(0, len(A0), 4000)])
    res = np.linalg.norm(tps_apply(src, Cw, src) - dst, axis=1)
    WARP = {"landmarks": int(len(src)), "max_shift_mm": round(float(np.linalg.norm(dst - src, axis=1).max()) * 1000, 2),
            "mean_shift_mm": round(float(np.linalg.norm(dst - src, axis=1).mean()) * 1000, 2),
            "fit_residual_mm": round(float(res.max()) * 1000, 3)}
    print("WARP", WARP, flush=True)
bvh_mh = BVHTree.FromPolygons([Vector(v) for v in A0], [tuple(t) for t in skin_tris])

# every pose goes through the same warp as the rest pose, so the offsets fit the Tripo proportions (a MetaHuman
# blink moved the lid by the MetaHuman eye height and left a strip open on the larger Tripo eye, sheet T7)
if LM:
    deltas = [np.vstack([tps_apply(src, Cw, X[i_:i_ + 4000]) for i_ in range(0, len(X), 4000)]) - A0
              for X in (apply(T, p) for p in poses)]
else:
    deltas = [(p - poses[0]) @ L.T for p in poses]
# --- surgery, transfer and mouth interior --------------------------------------------------------------------------
SURGERY = os.environ.get("SURGERY", "1") == "1"
from collections import defaultdict
from mathutils.kdtree import KDTree
# full Tripo head before any cut: positions, triangles and the UV of every triangle corner (for the eyeball texture)
faces_full = np.array([tuple(p_.vertices) for p_ in me.polygons])
uv_loop = np.zeros((len(me.loops), 2))
me.uv_layers.active.data.foreach_get("uv", uv_loop.ravel())
tri_uv = np.array([[uv_loop[li] for li in p_.loop_indices] for p_ in me.polygons])
P_full = P.copy()
bvh_full = BVHTree.FromPolygons([Vector(v) for v in P_full], [tuple(f) for f in faces_full])
n = len(P)

eyes_ids = [i for c, i in comps[1:] if 0.020 < np.ptp(poses[0][root == i], axis=0).max() < 0.030 and
            np.ptp(poses[0][root == i], axis=0).min() > 0.015]
eye_centres_w = [A0[root == i].mean(0) for i in eyes_ids]
# MetaHuman skin openings: neck, mouth (inner lip line) and the two lid margins
ec = defaultdict(int)
for t in skin_tris:
    for u, v in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
        ec[(min(u, v), max(u, v))] += 1
adj = defaultdict(list)
for (u, v), c in ec.items():
    if c == 1:
        adj[u].append(v)
        adj[v].append(u)
seen, loops = set(), []
for st in adj:
    if st in seen:
        continue
    loop, prev, cur = [st], None, st
    seen.add(st)
    while True:
        nx = [w for w in adj[cur] if w != prev and w not in seen]
        if not nx:
            break
        prev, cur = cur, nx[0]
        seen.add(cur)
        loop.append(cur)
    loops.append(np.array(loop))
loops.sort(key=len, reverse=True)
mouth, eye_loops = loops[1], loops[2:4]
mc = A0[mouth].mean(0)
jaw = np.linalg.norm(deltas[NAMES.index("JawOpen")], axis=1)

# transfer only from outward-facing skin: the inner lid and lip surfaces fold back toward the eye and the teeth,
# and Tripo vertices that landed on them took their large blink and jaw offsets (vertical streaks on sheet T3)
tn_ = np.cross(A0[skin_tris[:, 1]] - A0[skin_tris[:, 0]], A0[skin_tris[:, 2]] - A0[skin_tris[:, 0]])
tn_ /= np.linalg.norm(tn_, axis=1, keepdims=True) + 1e-12
fore = (np.abs(A0[skin_tris].mean(1)[:, 0] - mc[0]) < 0.02) & (A0[skin_tris].mean(1)[:, 2] > mid_tr[2] + 0.03)
if tn_[fore, 1].mean() > 0:                               # winding flipped by the Unreal-to-Blender mirror
    tn_ = -tn_
# ...except at the lid margins: there the margin itself must drive the cut edge, or the closed lid stops short
# (sheet T5: a strip of white left at full blink)
from mathutils.kdtree import KDTree as _KD
_kd = _KD(sum(len(el) for el in eye_loops))
_c = 0
for el in eye_loops:
    for vi in el:
        _kd.insert(Vector(A0[vi]), _c)
        _c += 1
_kd.balance()
tcen = A0[skin_tris].mean(1)
near_margin = np.array([_kd.find(Vector(c))[2] < 0.003 for c in tcen])
# and at the lips: the line where the lips meet faces inward, and without it the Tripo mouth corners took the motion of
# the outer skin, which narrows far less on an "o" (mouth width -2.1 mm against the MetaHuman's -7.1, DIAG 2026-11-14)
_kdm = _KD(len(mouth))
for _j, vi in enumerate(mouth):
    _kdm.insert(Vector(A0[vi]), _j)
_kdm.balance()
near_lips = np.array([_kdm.find(Vector(c))[2] < float(os.environ.get("LIP_NEAR", 0.0)) for c in tcen])
out_tris = skin_tris[(tn_[:, 1] < float(os.environ.get("FACING", -0.15))) | near_margin | near_lips]
bvh_out = BVHTree.FromPolygons([Vector(v) for v in A0], [tuple(t) for t in out_tris])
fi = np.full(n, -1)
bc = np.zeros((n, 3))
dist = np.full(n, 9.0)
for i, v in enumerate(P):
    loc, nrm, idx_, dd = bvh_out.find_nearest(Vector(v), FAR)
    if loc is None:
        continue
    t = out_tris[idx_]
    a, b, c = A0[t[0]], A0[t[1]], A0[t[2]]
    v0, v1, v2 = b - a, c - a, np.array(loc[:]) - a
    d00, d01, d11, d20, d21 = v0 @ v0, v0 @ v1, v1 @ v1, v2 @ v0, v2 @ v1
    den = d00 * d11 - d01 * d01
    w1 = (d11 * d20 - d01 * d21) / den if den else 0.0
    w2 = (d00 * d21 - d01 * d20) / den if den else 0.0
    fi[i], bc[i], dist[i] = idx_, (1 - w1 - w2, w1, w2), dd
wgt = np.clip((FAR - dist) / (FAR - NEAR), 0.0, 1.0)
on = fi >= 0
tt = out_tris[np.maximum(fi, 0)]
print("TRANSFER verts in reach", int(on.sum()), "full weight", int((wgt >= 1).sum()), flush=True)

kill = np.zeros(len(faces_full), bool)
lip_edge = []
cut_info = {}
if SURGERY:
    fc = P_full[faces_full].mean(1)
    # lip slit: Tripo triangles whose corners take their offsets from the upper and the lower lip at once, between the
    # mouth corners only (outside them the labels also flip along the cheek crease)
    lower_v = jaw > 0.5 * jaw[mouth].max()
    lower_corner = np.zeros(n, bool)
    known = on & (np.linalg.norm(P - mc, axis=1) < 0.03)
    tri_lower = lower_v[tt].sum(1) >= 2
    lower_corner[known] = tri_lower[known]
    xm0, xm1 = A0[mouth][:, 0].min() + 0.0005, A0[mouth][:, 0].max() - 0.0005
    zone = (fc[:, 0] > xm0) & (fc[:, 0] < xm1) & (np.abs(fc[:, 2] - mc[2]) < 0.012)
    kf = known[faces_full].all(1)
    mixed = lower_corner[faces_full].any(1) & ~lower_corner[faces_full].all(1)
    kill |= zone & kf & mixed
    n_mouth = int(kill.sum())

    def inside(poly_, x, z):
        xs, zs = poly_[:, 0], poly_[:, 1]
        xs2, zs2 = np.roll(xs, -1), np.roll(zs, -1)
        den_ = np.where(zs2 - zs == 0, 1e-12, zs2 - zs)
        return (((zs[None] > z[:, None]) != (zs2[None] > z[:, None])) &
                (x[:, None] < (xs2 - xs)[None] * (z[:, None] - zs[None]) / den_[None] + xs[None])).sum(1) % 2 == 1

    shrink = float(os.environ.get("EYE_SHRINK", 0.0007))
    for el in eye_loops:
        poly = A0[el][:, [0, 2]]
        cen = poly.mean(0)
        poly = cen + (poly - cen) * (1 - shrink / max(1e-6, np.linalg.norm(poly - cen, axis=1).mean()))
        ey = A0[el][:, 1].mean()
        near_e = np.abs(fc[:, 1] - ey) < 0.012
        sel = np.where(near_e)[0]
        kill[sel[inside(poly, fc[sel, 0], fc[sel, 2])]] = True
    n_eye = int(kill.sum()) - n_mouth
    cut_info = {"mouth_faces_cut": n_mouth, "eye_faces_cut": n_eye}

# eye cut edge on the lid margin: every Tripo vertex on the edge of an eye opening moves (in the rest pose) to the
# nearest point of the MetaHuman lid margin and takes that point's offsets in every shape, so a blink closes the
# opening exactly and the edge is smooth (sheet T6: jagged corners, a white strip left at full blink)
snap = {}
if SURGERY:
    alive_v = np.zeros(n, bool)
    alive_v[faces_full[~kill].ravel()] = True
    for el in eye_loops:
        ring = A0[el]
        cen = ring.mean(0)
        dead_e = kill & (np.linalg.norm(P_full[faces_full].mean(1) - cen, axis=1) < 0.025)
        edge_v = np.unique(faces_full[dead_e].ravel())
        edge_v = edge_v[alive_v[edge_v]]
        a_, b_ = ring, np.roll(ring, -1, axis=0)
        ab = b_ - a_
        L2 = np.maximum((ab ** 2).sum(1), 1e-12)
        for v in edge_v:
            t_ = np.clip(((P_full[v] - a_) * ab).sum(1) / L2, 0, 1)
            q = a_ + t_[:, None] * ab
            j = int(np.argmin(np.linalg.norm(q - P_full[v], axis=1)))
            snap[v] = (el[j], el[(j + 1) % len(el)], float(t_[j]), q[j])
    SNAP_MAX = float(os.environ.get("SNAP_MAX", 0.001))
    moved = 0
    for v, (i0, i1, t0, q) in snap.items():
        if np.linalg.norm(P_full[v] - q) < SNAP_MAX:    # larger moves folded triangles into the eye (sheet T7)
            P_full[v] = q
            moved += 1
    P = P_full.copy()
    cut_info["eye_edge_moved"] = moved
    cut_info["eye_edge_snapped"] = len(snap)
    # mouth slit edge: every Tripo vertex on the lip cut takes the offsets of the nearest point of the MetaHuman's lip
    # line (the inner lip loop), position unchanged, like the lid margins; so the corners narrow as the MetaHuman's do
    # LIP_SNAP and LIP_NEAR are off by default (2026-11-15): the inner lip loop lies 1 to 2 cm inside the mouth and
    # moves with the lip roll; driving the Tripo cut edge from it narrowed "o" better in the ARKit test but tore the
    # lower lip into white shards on song frames
    mkill_ = kill & (np.linalg.norm(P_full[faces_full].mean(1) - mc, axis=1) < 0.03)
    lip_edge = [int(v) for v in np.unique(faces_full[mkill_].ravel()) if alive_v[v]]
    if os.environ.get("LIP_SNAP", "0") == "1":
        mkill = kill & (np.linalg.norm(P_full[faces_full].mean(1) - mc, axis=1) < 0.03)
        medge = np.unique(faces_full[mkill].ravel())
        medge = medge[alive_v[medge]]
        ring = A0[mouth]
        a_, b_ = ring, np.roll(ring, -1, axis=0)
        ab = b_ - a_
        L2 = np.maximum((ab ** 2).sum(1), 1e-12)
        # each edge vertex only onto ITS lip's half of the loop: nearest-point alone put every lower-lip edge vertex on
        # the upper half (12 up, 0 low at the centre), the lower edge then moved with the upper lip and the stretch cut
        # tore 70 faces instead of 7 (2026-11-15)
        lowL = lower_v[mouth]
        seg_low = lowL & np.roll(lowL, -1)
        seg_up = ~lowL & ~np.roll(lowL, -1)
        n_lip = 0
        for v in medge:
            t_ = np.clip(((P_full[v] - a_) * ab).sum(1) / L2, 0, 1)
            q = a_ + t_[:, None] * ab
            dd_ = np.linalg.norm(q - P_full[v], axis=1)
            dd_ = np.where(seg_low if lower_corner[v] else seg_up, dd_, np.inf)
            if not np.isfinite(dd_).any():
                continue
            j = int(np.argmin(dd_))
            if np.linalg.norm(q[j] - P_full[v]) < float(os.environ.get("LIP_SNAP_MAX", 0.008)):
                snap[v] = (mouth[j], mouth[(j + 1) % len(mouth)], float(t_[j]), q[j])
                n_lip += 1
        cut_info["lip_edge_snapped"] = n_lip

# offsets per shape, smoothed over the Tripo surface (not across the cuts); vertices on a cut edge stay pinned.
# The glTF import splits vertices along UV seams (one runs down the middle of the face); smoothing each copy on its
# own side opened cracks along the seams (sheet T4: a hole in the upper lip on a smile). So the smoothing runs on
# welded vertices: copies at the same position share one id.
key_ = np.round(P_full / 1e-6).astype(np.int64)
weld = np.unique(key_, axis=0, return_inverse=True)[1].ravel()
nw = int(weld.max()) + 1
alive = weld[faces_full[~kill]]
e_ = np.r_[alive[:, [0, 1]], alive[:, [1, 2]], alive[:, [2, 0]]]
e_ = e_[e_[:, 0] != e_[:, 1]]
pin_w = np.zeros(nw, bool)
if kill.any():
    pin_w[weld[np.unique(faces_full[kill])]] = True
deg = np.bincount(e_.ravel(), minlength=nw).astype(float)
SMOOTH = int(os.environ.get("SMOOTH", 6))
Ds = {}
for k in range(1, len(NAMES)):
    D = np.zeros((n, 3))
    D[on] = (deltas[k][tt[on, 0]] * bc[on, 0:1] + deltas[k][tt[on, 1]] * bc[on, 1:2] +
             deltas[k][tt[on, 2]] * bc[on, 2:3]) * wgt[on, None]
    Dw = np.zeros((nw, 3))
    cnt_w = np.bincount(weld, minlength=nw).astype(float)
    for ax in range(3):
        Dw[:, ax] = np.bincount(weld, weights=D[:, ax], minlength=nw) / np.maximum(cnt_w, 1)
    act = np.linalg.norm(Dw, axis=1) > 1e-6
    for _ in range(SMOOTH):
        acc = np.zeros((nw, 3))
        for ax in range(3):
            acc[:, ax] = (np.bincount(e_[:, 0], weights=Dw[e_[:, 1], ax], minlength=nw) +
                          np.bincount(e_[:, 1], weights=Dw[e_[:, 0], ax], minlength=nw))
        avg = acc / np.maximum(deg, 1)[:, None]
        upd = act & ~pin_w & (deg > 0)
        Dw[upd] = 0.5 * Dw[upd] + 0.5 * avg[upd]
    Ds[k] = Dw[weld]
    for v, (i0, i1, t0, q) in snap.items():
        Ds[k][v] = (1 - t0) * deltas[k][i0] + t0 * deltas[k][i1]

if os.environ.get("DIAG"):
    # where does lip rounding get lost? Lip region: within 1.6 cm of the mouth centre, front half. For each key: MH
    # forward motion (-y) of its lip skin, Tripo forward motion before smoothing (raw transfer) and after.
    lipT = (np.linalg.norm(P_full - mc, axis=1) < 0.016) & (P_full[:, 1] < mc[1] + 0.004)
    lipM = skin_v & (np.linalg.norm(A0 - mc, axis=1) < 0.016) & (A0[:, 1] < mc[1] + 0.004)
    print("DIAG lip verts tripo", int(lipT.sum()), "in reach", int((lipT & on).sum()), "weight p10/50",
          np.round(np.percentile(wgt[lipT], [10, 50]), 2), "dist mm p50/90", np.round(np.percentile(dist[lipT], [50, 90]) * 1000, 1), flush=True)
    for kn in ("MouthPucker", "MouthFunnel", "JawOpen", "MouthSmileLeft"):
        k = NAMES.index(kn)
        raw = np.zeros((n, 3))
        raw[on] = (deltas[k][tt[on, 0]] * bc[on, 0:1] + deltas[k][tt[on, 1]] * bc[on, 1:2] +
                   deltas[k][tt[on, 2]] * bc[on, 2:3]) * wgt[on, None]
        print(f"DIAG {kn:15s} forward mm  MH {-deltas[k][lipM, 1].mean() * 1000:6.2f}  tripo raw {-raw[lipT, 1].mean() * 1000:6.2f}"
              f"  tripo smoothed {-Ds[k][lipT, 1].mean() * 1000:6.2f}   |motion| mm MH {np.linalg.norm(deltas[k][lipM], axis=1).mean() * 1000:5.2f}"
              f" raw {np.linalg.norm(raw[lipT], axis=1).mean() * 1000:5.2f} smoothed {np.linalg.norm(Ds[k][lipT], axis=1).mean() * 1000:5.2f}", flush=True)
if os.environ.get("DIAG"):
    cornM = [mouth[np.argmin(A0[mouth][:, 0])], mouth[np.argmax(A0[mouth][:, 0])]]
    _lipv = [v for v, (i0, i1, t0, q) in snap.items() if np.linalg.norm(q - mc) < 0.03]
    cornT = [min(_lipv, key=lambda v: P_full[v, 0]), max(_lipv, key=lambda v: P_full[v, 0])] if _lipv else         [int(np.argmin(np.linalg.norm(P_full - A0[c_], axis=1))) for c_ in cornM]
    print("DIAG corners MH", np.round(A0[cornM] * 100, 2).tolist(), "tripo", np.round(P_full[cornT] * 100, 2).tolist(),
          "gap mm", [round(float(np.linalg.norm(P_full[t_] - A0[m_])) * 1000, 1) for t_, m_ in zip(cornT, cornM)], flush=True)
    for kn in ("MouthPucker", "MouthFunnel", "MouthSmileLeft"):
        k = NAMES.index(kn)
        wM = np.linalg.norm((A0[cornM[0]] + deltas[k][cornM[0]]) - (A0[cornM[1]] + deltas[k][cornM[1]])) - np.linalg.norm(A0[cornM[0]] - A0[cornM[1]])
        wT = np.linalg.norm((P_full[cornT[0]] + Ds[k][cornT[0]]) - (P_full[cornT[1]] + Ds[k][cornT[1]])) - np.linalg.norm(P_full[cornT[0]] - P_full[cornT[1]])
        print(f"DIAG {kn:15s} mouth width change mm  MH {wM * 1000:6.2f}  tripo {wT * 1000:6.2f}", flush=True)
eye_kill = np.zeros(len(faces_full), bool)
blink_corr = {}
if SURGERY:
    fcx = P_full[faces_full].mean(1)
    for el in eye_loops:
        eye_kill |= kill & (np.linalg.norm(fcx - A0[el].mean(0), axis=1) < 0.025)
    # blink closure: the MetaHuman skin margin stays 3 to 4.4 mm open at full blink (the lid's thickness closes it;
    # measured 2026-11-14 on the left eye), and the Tripo lid has no thickness. For each blink key the upper cut edge
    # goes down to the lower edge at the same x (0.3 mm overlap), with a falloff up the lid over BLINK_R metres, and
    # nothing goes inside the eyeball.
    BLINK_R = float(os.environ.get("BLINK_R", 0.006))
    r_eye = 0.5 * float(np.ptp(A0[root == eyes_ids[0]], axis=0).max()) if eyes_ids else 0.012
    for kname in ("EyeBlinkLeft", "EyeBlinkRight"):
        k = NAMES.index(kname)
        el = max(eye_loops, key=lambda e: np.linalg.norm(deltas[k][e], axis=1).mean())
        ring = A0[el]
        cen = ring.mean(0)
        ec_ = [eb for eb in eye_centres_w if np.linalg.norm(eb - cen) < 0.03]
        xs = ring[:, 0]
        c0, c1 = ring[np.argmin(xs)], ring[np.argmax(xs)]
        line_z = c0[2] + (xs - c0[0]) / max(1e-9, c1[0] - c0[0]) * (c1[2] - c0[2])
        lower_ring = (A0[el] + deltas[k][el])[ring[:, 2] < line_z]
        lo = lower_ring[np.argsort(lower_ring[:, 0])]
        up_edge = [v for v, (i0, i1, t0, q) in snap.items() if np.linalg.norm(q - cen) < 0.025 and
                   q[2] > c0[2] + (q[0] - c0[0]) / max(1e-9, c1[0] - c0[0]) * (c1[2] - c0[2])]
        if not up_edge or len(lo) < 2:
            continue
        pre_blink = Ds[k].copy()
        up_mh = el[ring[:, 2] >= line_z]
        cur = P_full[up_edge] + Ds[k][up_edge]
        tz = np.interp(cur[:, 0], lo[:, 0], lo[:, 2]) - 0.0003
        dz_edge = np.minimum(tz - cur[:, 2], 0.0)
        kd_e = KDTree(len(up_edge))
        for j, v in enumerate(up_edge):
            kd_e.insert(Vector(P_full[v]), j)
        kd_e.balance()
        band = np.where((np.linalg.norm(P_full - cen, axis=1) < 0.03) & (P_full[:, 2] > line_z.min() - 0.002))[0]
        for v in band:
            _, j, dd = kd_e.find(Vector(P_full[v]))
            if dd > BLINK_R or P_full[v, 2] < P_full[up_edge[j], 2] - 0.0005:
                continue
            w_ = (1 - dd / BLINK_R) ** 2
            Ds[k][v, 2] += w_ * dz_edge[j]
            # the closed lid lies on the Tripo face's own surface across the eye (the uncut painted eye), 0.2 mm in
            # front: pushing it out of the MetaHuman eyeball made a ball on sheet T9
            x_ = P_full[v] + Ds[k][v]
            h_ = bvh_full.ray_cast(Vector((x_[0], x_[1] - 0.03, x_[2])), Vector((0, 1, 0)), 0.06)
            if h_[0] is not None and w_ > 0.05:
                Ds[k][v, 1] += (h_[0].y - 0.0002 - x_[1]) * min(1.0, 3 * w_)
        cut_info[f"blink_close_mm_{kname}"] = round(float(-dz_edge.mean()) * 1000, 2)
        blink_corr[kname] = (Ds[k] - pre_blink, up_mh, float(deltas[k][up_mh][:, 2].mean()))

if SURGERY:
    # stretch cut: triangles in the mouth that grow more than 3x when the jaw opens span the opening
    def area(X, F):
        return 0.5 * np.linalg.norm(np.cross(X[F[:, 1]] - X[F[:, 0]], X[F[:, 2]] - X[F[:, 0]]), axis=1)
    a0 = area(P_full, faces_full)
    a1 = area(P_full + Ds[NAMES.index("JawOpen")], faces_full)
    fc = P_full[faces_full].mean(1)
    zone2 = np.linalg.norm(fc - mc, axis=1) < 0.03
    stretch = zone2 & (a1 > 3.0 * np.maximum(a0, 1e-12))
    # only next to the lip cut: with the lip line driving the cut edge, faces inside the lower lip also grew and the cut
    # opened notches in the lip (diag renders, 2026-11-14)
    _kv = np.zeros(n, bool)
    _kv[np.unique(faces_full[kill].ravel())] = True
    stretch &= _kv[faces_full].any(1)
    # STRETCH_CUT=0 keeps them: with the corner seal (SEAL) the corners stay closed, and the stretch holes, cut after
    # the slit edge is known, were not sealed and showed as a dark speck beside the right mouth corner (T52)
    if os.environ.get("STRETCH_CUT", "1") != "1":
        stretch[:] = False
    cut_info["stretch_faces_cut"] = int((stretch & ~kill).sum())
    cut_info["stretch_faces_x_mm_from_mouth_centre"] = np.round((fc[stretch & ~kill][:, 0] - mc[0]) * 1000, 1).tolist()
    kill |= stretch
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[i] for i in np.where(kill)[0]], context="FACES")
    used = np.zeros(n, bool)
    used[faces_full[~kill].ravel()] = True
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(me)
    bm.free()
    me.update()
    keepv = used
else:
    keepv = np.ones(n, bool)
P = P_full[keepv]
print("SURGERY", cut_info, "verts now", len(P), flush=True)
me.vertices.foreach_set("co", P.ravel())
me.update()
dr.shape_key_add(name="Basis")
stats = {}
for k in range(1, len(NAMES)):
    sk = dr.shape_key_add(name=NAMES[k], from_mix=False)
    sk.data.foreach_set("co", (P + Ds[k][keepv]).ravel())
    stats[NAMES[k]] = round(float(np.linalg.norm(Ds[k][keepv], axis=1).max()) * 100, 2)
print("SHAPES max cm", stats, flush=True)

inner = None
if SURGERY:
    # MetaHuman eyeballs and mouth parts (teeth, tongue, gums, cavity): every non-skin part with its centre in the mouth
    # and more than 150 vertices, and the two eyeballs
    keep = np.zeros(nv, bool)
    eyes_parts = []
    # material of each MetaHuman part and per-corner UVs (ue_face_arkit_export.py STEP=uvs)
    mat_names = open(adir / "face_materials.txt").read().split(chr(10))
    tri_mat = np.loadtxt(adir / "face_matid.txt", dtype=np.int64)
    tri_uv0 = np.loadtxt(adir / "face_tri_uv0.txt").reshape(-1, 3, 2)
    troot = root[tris[:, 0]]
    part_mat = {}
    for c_, i_ in comps:
        mm_ = tri_mat[troot == i_]
        if len(mm_):
            part_mat[i_] = mat_names[int(np.bincount(mm_).argmax())]
    for c, i in comps[1:]:
        m = root == i
        pc = A0[m].mean(0)
        ext = np.ptp(poses[0][m], axis=0)        # MetaHuman size, before the alignment scale
        in_mouth = np.linalg.norm(pc - mc) < 0.045
        is_eyeball = 0.020 < ext.max() < 0.030 and ext.min() > 0.015
        mname = part_mat.get(i, "")
        if (in_mouth and c > 150 and "Hide" not in mname) or is_eyeball:   # M_Hide parts are hidden in the MetaHuman too
            keep |= m
            if is_eyeball:
                eyes_parts.append(i)
    idx = np.where(keep)[0]
    remap = -np.ones(nv, int)
    remap[idx] = np.arange(len(idx))
    it_idx = np.where(keep[tris].all(1))[0]
    it = tris[it_idx]
    im = bpy.data.meshes.new("yuki_mh_inner")
    im.from_pydata([tuple(v) for v in A0[idx]], [], [tuple(remap[t]) for t in it])
    im.update()
    for pl in im.polygons:
        pl.use_smooth = True
    inner = bpy.data.objects.new("yuki_mh_inner", im)
    bpy.context.scene.collection.objects.link(inner)
    part_of = root[idx]
    is_eye_v = np.isin(part_of, eyes_parts)
    # never in front of the Tripo skin. A push per shape key does not hold for combinations (left + right smile put
    # the teeth in front of the closed lips on 2026-11-14), so the mouth parts get ONE offset backwards (+y): the
    # largest protrusion over a set of singing combinations, plus MARGIN, capped at 8 mm. The eyeballs stay.
    MARGIN = float(os.environ.get("MARGIN", 0.0012))
    old2new = -np.ones(n, int)
    old2new[np.where(keepv)[0]] = np.arange(keepv.sum())
    Fk = [tuple(old2new[list(f)]) for f in faces_full[~kill]]
    ki = {nm: NAMES.index(nm) for nm in NAMES}
    COMBOS = [{}, {"MouthSmileLeft": 1, "MouthSmileRight": 1}, {"JawOpen": 0.6, "MouthSmileLeft": 0.5, "MouthSmileRight": 0.5},
              {"MouthFunnel": 1, "MouthPucker": 1}, {"MouthPucker": 1}, {"MouthPressLeft": 1, "MouthPressRight": 1},
              {"MouthRollLower": 1, "MouthRollUpper": 1}, {"JawOpen": 1}, {"MouthStretchLeft": 1, "MouthStretchRight": 1},
              {"MouthUpperUpLeft": 1, "MouthUpperUpRight": 1}, {"MouthShrugUpper": 1, "MouthShrugLower": 1}]
    mouth_v = ~is_eye_v
    worst = 0.0
    for cmb in COMBOS:
        Xs = P + sum((Ds[ki[nm]][keepv] * w for nm, w in cmb.items()), np.zeros_like(P))
        Xi = A0[idx] + sum((deltas[ki[nm]][idx] * w for nm, w in cmb.items()), np.zeros((len(idx), 3)))
        bvh_k = BVHTree.FromPolygons([Vector(v) for v in Xs], Fk)
        for j in np.where(mouth_v)[0]:
            # the ray runs 5 cm past the part as well: skin BEHIND a tooth is exactly the case to catch (a ray that
            # stopped at the tooth measured 0 protrusion while the render showed teeth over the lips)
            h_ = bvh_k.ray_cast(Vector((Xi[j, 0], Xi[j, 1] - 0.05, Xi[j, 2])), Vector((0, 1, 0)), 0.10)
            if h_[0] is not None and h_[0].y - Xi[j, 1] < 0.02:
                worst = max(worst, h_[0].y - Xi[j, 1])
    back = min(0.008, max(0.0, worst + MARGIN)) + float(os.environ.get("MOUTH_BACK_EXTRA", 0.0))
    off = np.zeros((len(idx), 3))
    off[mouth_v, 1] = back
    # eyeballs behind the Tripo face's own eye surface: the closed lid lies on that surface, and an eyeball in front
    # of it showed through the closed lid (sheet T10). Each eyeball goes back by its largest protrusion + 0.6 mm.
    eye_back = []
    for i_e in eyes_parts:
        mv = part_of == i_e
        Xe = A0[idx][mv]
        worst_e = 0.0
        for xv in Xe[Xe[:, 1] < Xe[:, 1].mean()]:
            h_ = bvh_full.ray_cast(Vector((xv[0], xv[1] - 0.03, xv[2])), Vector((0, 1, 0)), 0.06)
            if h_[0] is not None and h_[0].y - xv[1] < 0.015:
                worst_e = max(worst_e, h_[0].y + 0.0006 - xv[1])
        off[mv, 1] = min(0.006, worst_e)
        eye_back.append(round(min(0.006, worst_e) * 1000, 2))
    cut_info["eyeballs_back_mm"] = eye_back
    im.vertices.foreach_set("co", (A0[idx] + off).ravel())
    inner.shape_key_add(name="Basis")
    for k in range(1, len(NAMES)):
        sk = inner.shape_key_add(name=NAMES[k], from_mix=False)
        sk.data.foreach_set("co", (A0[idx] + deltas[k][idx] + off).ravel())
    pushed = round(back * 1000, 2)
    cut_info["mouth_parts_back_mm"] = pushed
    # TEETH_RIGID=1: the mouth parts keep their MetaHuman shape. The landmark warp is fitted to the face surface; it
    # also stretched the teeth arches to the wider Tripo mouth and pulled the lower teeth apart into separate pegs
    # (song sheets, 2026-11-15). Each jaw (upper parts, lower parts = those that follow JawOpen) instead gets ONE
    # similarity transform, fitted from its rigid rest pose to where the warp put it, and every song frame moves the
    # rigidly aligned MetaHuman parts by that transform, so the jaw motion is kept and the teeth are not deformed.
    teeth_sim = None
    if os.environ.get("TEETH_RIGID", "0") == "1":
        def sim_fit(X_, Y_):
            mx_, my_ = X_.mean(0), Y_.mean(0)
            Xc_, Yc_ = X_ - mx_, Y_ - my_
            U_, S_, Vt_ = np.linalg.svd(Yc_.T @ Xc_ / len(X_))
            Dm_ = np.diag([1.0, 1.0, np.sign(np.linalg.det(U_ @ Vt_))])
            R_ = U_ @ Dm_ @ Vt_
            sc_ = float(np.trace(np.diag(S_) @ Dm_) / (Xc_ ** 2).sum(1).mean())
            return sc_, R_, my_ - sc_ * R_ @ mx_
        jaw_i = np.linalg.norm(deltas[NAMES.index("JawOpen")][idx], axis=1)
        pm_ = {i_: jaw_i[part_of == i_].mean() for i_ in np.unique(part_of[mouth_v])}
        jmax_ = max(pm_.values())
        low_part = np.array([pm_.get(i_, 0.0) > 0.4 * jmax_ for i_ in part_of]) & mouth_v
        teeth_sim = []
        for nm_g, g_ in (("upper", mouth_v & ~low_part), ("lower", low_part)):
            if g_.sum() < 10:
                continue
            sc_, R_, t_s = sim_fit(A0r[idx][g_], A0[idx][g_])
            Ys_ = (sc_ * (R_ @ A0r[idx][g_].T)).T + t_s
            res_ = np.linalg.norm(Ys_ - A0[idx][g_], axis=1)
            eg_ = it[(remap[it] >= 0).all(1)]
            eg_ = np.r_[eg_[:, [0, 1]], eg_[:, [1, 2]], eg_[:, [2, 0]]]
            loc_ = remap[eg_]
            sel_ = g_[loc_[:, 0]] & g_[loc_[:, 1]]
            Lw_ = np.linalg.norm(A0[idx][loc_[sel_, 0]] - A0[idx][loc_[sel_, 1]], axis=1)
            Ls_ = np.linalg.norm(Ys_[np.searchsorted(np.where(g_)[0], loc_[sel_, 0])] - Ys_[np.searchsorted(np.where(g_)[0], loc_[sel_, 1])], axis=1)
            rt_ = Lw_ / np.maximum(Ls_, 1e-9)
            print("TEETH_RIGID", nm_g, "verts", int(g_.sum()), "scale", round(sc_, 3), "residual mm mean/max",
                  round(float(res_.mean()) * 1000, 2), round(float(res_.max()) * 1000, 2),
                  "warp edge stretch p5/p50/p95", np.round(np.percentile(rt_, [5, 50, 95]), 3).tolist(),
                  "arch width mm warp/rigid", round(float(np.ptp(A0[idx][g_][:, 0])) * 1000, 1), round(float(np.ptp(Ys_[:, 0])) * 1000, 1), flush=True)
            teeth_sim.append((g_, sc_, R_, t_s))

    def mk(name, rgb):
        m_ = bpy.data.materials.new(name)
        m_.use_nodes = True
        bs = next(n_ for n_ in m_.node_tree.nodes if n_.type == "BSDF_PRINCIPLED")
        bs.inputs["Base Color"].default_value = (*rgb, 1)
        bs.inputs["Roughness"].default_value = 0.35 if name == "teeth" else 0.6
        return m_
    mats = {"teeth": mk("teeth", (0.86, 0.84, 0.78)), "gum": mk("gum", (0.30, 0.06, 0.08)),
            "tongue": mk("tongue", (0.70, 0.30, 0.32)), "eye": bpy.data.materials.new("eyeball")}
    # teeth, gums, tongue and palate share the MetaHuman teeth atlas: our whitened bake (teeth_tex_v1) on its UVs
    TEETH_TEX = Path(__file__).resolve().parent / "models/yuki/teeth_tex_v1/yuki_teeth_BC.png"
    if TEETH_TEX.exists():
        tm = mats["teeth"]
        tt_img = bpy.data.images.load(str(TEETH_TEX))
        tn_ = tm.node_tree.nodes.new("ShaderNodeTexImage")
        tn_.image = tt_img
        bs_ = next(n_ for n_ in tm.node_tree.nodes if n_.type == "BSDF_PRINCIPLED")
        tm.node_tree.links.new(tn_.outputs["Color"], bs_.inputs["Base Color"])
    for m_ in mats.values():
        im.materials.append(m_)
    tng_mv = np.linalg.norm(deltas[NAMES.index("TongueOut")], axis=1)
    pidx = {}
    for i in np.unique(part_of):
        m = root == i
        pidx[i] = 3 if i in eyes_parts else (2 if tng_mv[m].mean() > 0.003 else 1)
    mouth_parts = sorted([(int((root == i).sum()), i) for i in np.unique(part_of) if i not in eyes_parts], reverse=True)
    for _, i in mouth_parts[:2]:
        pidx[i] = 0
    for i in np.unique(part_of):
        if "Teeth" in part_mat.get(i, "") and i not in eyes_parts and pidx[i] != 2:   # the tongue keeps its pink
            pidx[i] = 0
    for poly in im.polygons:
        poly.material_index = pidx[part_of[poly.vertices[0]]]
    uv_t = im.uv_layers.new(name="UVMap") if not im.uv_layers else im.uv_layers[0]
    for pi_, poly in enumerate(im.polygons):
        if poly.material_index == 0:
            for c3, li in enumerate(poly.loop_indices):
                u_, v_ = tri_uv0[it_idx[pi_], c3]
                uv_t.data[li].uv = (u_, 1.0 - v_)             # Unreal UV origin is top left
    # eyeball UVs: front projection onto the UNCUT Tripo head, barycentric UV at the hit (the painted eye itself)
    def grow(poly_, d_):
        c_ = poly_.mean(0)
        r_ = np.linalg.norm(poly_ - c_, axis=1, keepdims=True)
        return c_ + (poly_ - c_) * (1 + d_ / np.maximum(r_, 1e-9))

    uvl = im.uv_layers[0]
    # sclera texel: the brightest, least saturated texel among the cut eye faces (where the eyeball turns, a front
    # projection would otherwise land on lid and corner skin: pink zigzags on the eyeball, sheet T8)
    img_e = next((i_ for i_ in bpy.data.images if i_.size[0] and i_.name.lower().startswith("base")), None)
    sclera_uv = None
    if img_e is not None:
        iw, ih = img_e.size
        px_ = np.empty(iw * ih * 4, dtype=np.float32)
        img_e.pixels.foreach_get(px_)
        px_ = px_.reshape(ih, iw, 4)
        best = -1.0
        for fidx in np.where(eye_kill)[0]:
            uvc = tri_uv[fidx].mean(0)
            cpx = px_[int(np.clip(uvc[1], 0, 1) * (ih - 1)), int(np.clip(uvc[0], 0, 1) * (iw - 1)), :3]
            score = float(cpx.mean() - (cpx.max() - cpx.min()))
            if score > best:
                best, sclera_uv = score, tuple(uvc)
    for poly in im.polygons:
        if poly.material_index != 3:
            continue
        for li in poly.loop_indices:
            vco = im.vertices[im.loops[li].vertex_index].co
            el_n = min(eye_loops, key=lambda e: np.linalg.norm(A0[e].mean(0) - np.array(vco[:])))
            poly_s = grow(A0[el_n][:, [0, 2]], -0.0015)
            xz = np.array([vco.x, vco.z])
            if not inside(poly_s, np.array([xz[0]]), np.array([xz[1]]))[0]:
                a_p, b_p = poly_s, np.roll(poly_s, -1, axis=0)
                ab_p = b_p - a_p
                t_p = np.clip(((xz - a_p) * ab_p).sum(1) / np.maximum((ab_p ** 2).sum(1), 1e-12), 0, 1)
                qs = a_p + t_p[:, None] * ab_p
                xz = qs[np.argmin(np.linalg.norm(qs - xz, axis=1))]
            h_ = bvh_full.ray_cast(Vector((xz[0], vco.y - 0.05, xz[1])), Vector((0, 1, 0)), 0.1)
            if h_[0] is None:
                if sclera_uv is not None:
                    uvl.data[li].uv = sclera_uv
                continue
            f = faces_full[h_[2]]
            a, b, c = P_full[f[0]], P_full[f[1]], P_full[f[2]]
            v0, v1, v2 = b - a, c - a, np.array(h_[0][:]) - a
            d00, d01, d11, d20, d21 = v0 @ v0, v0 @ v1, v1 @ v1, v2 @ v0, v2 @ v1
            den = d00 * d11 - d01 * d01
            w1 = (d11 * d20 - d01 * d21) / den if den else 0.0
            w2 = (d00 * d21 - d01 * d20) / den if den else 0.0
            uvs = tri_uv[h_[2]]
            uvl.data[li].uv = tuple((1 - w1 - w2) * uvs[0] + w1 * uvs[1] + w2 * uvs[2])
    em_ = mats["eye"]
    em_.use_nodes = True
    if img_src := next((i_ for i_ in bpy.data.images if i_.size[0] and i_.name.lower().startswith("base")), None):
        tn = em_.node_tree.nodes.new("ShaderNodeTexImage")
        tn.image = img_src
        bs = next(n_ for n_ in em_.node_tree.nodes if n_.type == "BSDF_PRINCIPLED")
        em_.node_tree.links.new(tn.outputs["Color"], bs.inputs["Base Color"])
        bs.inputs["Roughness"].default_value = 0.15
    print("INNER verts", len(idx), "parts", len(pidx), "eyes", len(eyes_parts), "mouth parts back mm", pushed, flush=True)
json.dump({"T": T.tolist(), "icp_mm": hist[-1], "near": NEAR, "far": FAR, "max_cm": stats, "cut": cut_info, "warp": WARP,
           "mh_eyes": [list(map(float, e)) for e in eye_c]}, open(out / "align.json", "w"), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=str(out / "yuki_tripo_head_shapes.blend"))

# --- check renders ------------------------------------------------------------------------------------------------
img = next((i for i in bpy.data.images if i.size[0] and i.name.lower().startswith("base")), None)
mat = bpy.data.materials.new("chk")
mat.use_nodes = True
nt = mat.node_tree
for nd in list(nt.nodes):
    if nd.type != "OUTPUT_MATERIAL":
        nt.nodes.remove(nd)
em = nt.nodes.new("ShaderNodeEmission")
if img:
    tx = nt.nodes.new("ShaderNodeTexImage")
    tx.image = img
    nt.links.new(tx.outputs["Color"], em.inputs["Color"])
nt.links.new(em.outputs[0], next(nd for nd in nt.nodes if nd.type == "OUTPUT_MATERIAL").inputs["Surface"])
me.materials.clear()
me.materials.append(mat)
scene = bpy.context.scene
try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError:
    scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = scene.render.resolution_y = 700
scene.view_settings.view_transform = "Standard"
world = bpy.data.worlds.new("w")
world.use_nodes = True
next(n_ for n_ in world.node_tree.nodes if n_.type == "BACKGROUND").inputs["Strength"].default_value = 1.2
scene.world = world
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
sun.data.energy = 3.0
sun.rotation_euler = (math.radians(70), 0, 0)
scene.collection.objects.link(sun)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
cam.data.type = "ORTHO"
cam.data.ortho_scale = 0.17
scene.collection.objects.link(cam)
scene.camera = cam
cz = (mid_tr[2] + chin_z) / 2 + 0.01
SETS = {"neutral": {}, "jawopen": {"JawOpen": 1.0}, "smile": {"MouthSmileLeft": 1.0, "MouthSmileRight": 1.0},
        "blink": {"EyeBlinkLeft": 1.0, "EyeBlinkRight": 1.0}, "brows_up": {"BrowInnerUp": 1.0,
        "BrowOuterUpLeft": 1.0, "BrowOuterUpRight": 1.0}, "ooh": {"MouthFunnel": 0.8, "MouthPucker": 0.6},
        "sing_ah": {"JawOpen": 0.55, "MouthSmileLeft": 0.3, "MouthSmileRight": 0.3, "BrowInnerUp": 0.4},
        "look_left": {"EyeLookOutLeft": 0.8, "EyeLookInRight": 0.8}, "half_blink": {"EyeBlinkLeft": 0.5, "EyeBlinkRight": 0.5}}
for name, vals in SETS.items():
    for ob in [dr] + ([inner] if inner is not None else []):
        for kb in ob.data.shape_keys.key_blocks[1:]:
            kb.value = vals.get(kb.name, 0.0)
    for view, yaw in (("front", 0), ("q34", 35)):
        a = math.radians(yaw)
        cam.location = (mid_tr[0] + 1.0 * math.sin(a), -1.0 * math.cos(a), cz)
        cam.rotation_euler = (math.pi / 2, 0, a)
        scene.render.filepath = str(out / f"chk_{name}_{view}.png")
        bpy.ops.render.render(write_still=True)
print("DONE", out, flush=True)


# --- song mode: the MetaHuman face of every song frame (ue_face_arkit_export.py STEP=setcopy), transferred exactly ---
SONG_DIR = os.environ.get("SONG_DIR", "")
if SONG_DIR:
    frames = sorted(Path(SONG_DIR).glob("f_*.bin"))
    SONG_OUT = Path(os.environ.get("SONG_OUT", str(out / "song"))).resolve()   # Blender resolves a relative render path against C:\
    SONG_OUT.mkdir(parents=True, exist_ok=True)
    for ob in [dr] + ([inner] if inner is not None else []):
        for kb in ob.data.shape_keys.key_blocks[1:]:
            kb.value = 0.0
    k_song = dr.shape_key_add(name="Song", from_mix=False)
    k_song.value = 1.0
    if os.environ.get("SONG_HIDE_HEAD") == "1":     # debug: only the mouth parts and eyeballs render
        dr.hide_render = True
    k_song_i = inner.shape_key_add(name="Song", from_mix=False) if inner is not None else None
    if k_song_i is not None:
        k_song_i.value = 1.0
    scene.render.resolution_x = scene.render.resolution_y = int(os.environ.get("SONG_PX", 900))
    cam.data.type = "PERSP"
    cam.data.lens = float(os.environ.get("SONG_LENS", 85))
    cam.location = (mid_tr[0], -float(os.environ.get("SONG_DIST", 0.78)), cz + float(os.environ.get("SONG_DZ", 0.005)))
    cam.rotation_euler = (math.pi / 2, 0, 0)
    yaw_ = math.radians(float(os.environ.get("SONG_YAW", 0.0)))
    if yaw_:
        # turned view for design checks: the camera orbits the head axis (x = head centre, y = 0) at the same distance
        d_ = float(os.environ.get("SONG_DIST", 0.78))
        cam.location = (mid_tr[0] + d_ * math.sin(yaw_), -d_ * math.cos(yaw_), cam.location[2])
        cam.rotation_euler = (math.pi / 2, 0, yaw_)
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.03, 0.025, 0.04, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.35
    bg_rgb = None
    if os.environ.get("SONG_ALPHA") == "1":           # debug: transparent film, so alpha shows where the mouth is see-through
        scene.render.film_transparent = True
        scene.render.image_settings.color_mode = "RGBA"
    key = bpy.data.objects.new("key", bpy.data.lights.new("key", "AREA"))
    key.data.energy, key.data.size = float(os.environ.get("KEY_W", 9.0)), 0.6
    key.location = (mid_tr[0] - 0.35, -0.55, cz + 0.25)
    key.rotation_euler = (math.radians(65), 0, math.radians(-30))
    scene.collection.objects.link(key)
    rim = bpy.data.objects.new("rim", bpy.data.lights.new("rim", "AREA"))
    rim.data.energy, rim.data.size = float(os.environ.get("RIM_W", 7.0)), 0.4
    rim.location = (mid_tr[0] + 0.35, 0.35, cz + 0.2)
    rim.rotation_euler = (math.radians(-60), 0, math.radians(140))
    scene.collection.objects.link(rim)
    sun.data.energy = 0.4
    scene.view_settings.view_transform = "AgX"     # Standard clipped the painted texture to white (song_test_sheet)
    for look in ("AgX - Punchy", "Punchy"):        # plain AgX greyed the pink (song_test2_sheet)
        try:
            scene.view_settings.look = look
            break
        except TypeError:
            continue
    # the head gets the model's own glTF material back (base colour, normal and roughness maps) instead of the flat
    # emission used for the checks, so the lights shape the face
    orig = [m_ for m_ in bpy.data.materials if m_.use_nodes and m_.name not in ("chk", "lm_tex", "grey", "teeth", "gum",
            "tongue", "eyeball", "bake_target") and any(n_.type == "TEX_IMAGE" for n_ in m_.node_tree.nodes)]
    if orig:
        me.materials.clear()
        me.materials.append(orig[0])
        print("SONG head material", orig[0].name, flush=True)
    # --- looks: light, colour management and how much of the painted texture shows unlit -----------------------------
    hm_ = me.materials[0]
    hn_ = hm_.node_tree
    bsdf_h = next(n_ for n_ in hn_.nodes if n_.type == "BSDF_PRINCIPLED")
    outp_h = next(n_ for n_ in hn_.nodes if n_.type == "OUTPUT_MATERIAL")
    img_h = next((n_ for n_ in hn_.nodes if n_.type == "TEX_IMAGE" and n_.image and "base" in n_.image.name.lower()),
                 next(n_ for n_ in hn_.nodes if n_.type == "TEX_IMAGE"))
    hsv_h = hn_.nodes.new("ShaderNodeHueSaturation")
    hn_.links.new(img_h.outputs["Color"], hsv_h.inputs["Color"])
    emi_h = hn_.nodes.new("ShaderNodeEmission")
    hn_.links.new(hsv_h.outputs["Color"], emi_h.inputs["Color"])
    mix_h = hn_.nodes.new("ShaderNodeMixShader")
    hn_.links.new(bsdf_h.outputs[0], mix_h.inputs[1])
    hn_.links.new(emi_h.outputs[0], mix_h.inputs[2])
    hn_.links.new(mix_h.outputs[0], outp_h.inputs["Surface"])
    # teeth read grey under the face lights: the same whitened bake, a little brighter, and glossier
    tm_ = bpy.data.materials.get("teeth")
    if tm_ is not None:
        tnt = tm_.node_tree
        ti_ = next((n_ for n_ in tnt.nodes if n_.type == "TEX_IMAGE"), None)
        tb_ = next(n_ for n_ in tnt.nodes if n_.type == "BSDF_PRINCIPLED")
        if ti_ is not None:
            bc_ = tnt.nodes.new("ShaderNodeBrightContrast")
            bc_.inputs["Bright"].default_value = 0.12
            tnt.links.new(ti_.outputs["Color"], bc_.inputs["Color"])
            tnt.links.new(bc_.outputs["Color"], tb_.inputs["Base Color"])
        tb_.inputs["Roughness"].default_value = 0.25
    # the same partial "unlit paint" for the teeth and the eyeballs: in the mouth's shadow the teeth read as grey
    # pebbles and the sclera grey (paint render, 2026-11-14 close-ups)
    inner_mix = []
    teeth_gain_node = None
    for nm_ in ("teeth", "eyeball"):
        im_ = bpy.data.materials.get(nm_)
        if im_ is None:
            continue
        nt_ = im_.node_tree
        bs_ = next(n_ for n_ in nt_.nodes if n_.type == "BSDF_PRINCIPLED")
        op_ = next(n_ for n_ in nt_.nodes if n_.type == "OUTPUT_MATERIAL")
        src_ = bs_.inputs["Base Color"].links[0].from_socket if bs_.inputs["Base Color"].links else None
        if src_ is None:
            continue
        em_n = nt_.nodes.new("ShaderNodeEmission")
        if nm_ == "teeth":
            # light that reaches the teeth: one gain per frame from the lip opening (set in the song loop); a narrow slit
            # leaves them in shadow, an open smile shows them white (fixed AO darkened smiling teeth to grey, T22)
            gn_ = nt_.nodes.new("ShaderNodeMix")
            gn_.data_type = "RGBA"
            gn_.blend_type = "MULTIPLY"
            gn_.inputs[0].default_value = 1.0
            nt_.links.new(src_, gn_.inputs[6])
            gn_.inputs[7].default_value = (1, 1, 1, 1)
            teeth_gain_node = gn_
            nt_.links.new(gn_.outputs[2], bs_.inputs["Base Color"])
            src_ = gn_.outputs[2]
        if nm_ == "teeth" and float(os.environ.get("TEETH_AO", 0)) > 0:
            # depth darkening: real teeth fall into shadow behind the lips; with unlit paint they glowed through the
            # lip slit on "o" frames while the MetaHuman's stayed dark (rounding sheet, 2026-11-14)
            ao_ = nt_.nodes.new("ShaderNodeAmbientOcclusion")
            ao_.inputs["Distance"].default_value = float(os.environ.get("TEETH_AO", 0.012))
            nt_.links.new(src_, ao_.inputs["Color"])
            nt_.links.new(ao_.outputs["Color"], bs_.inputs["Base Color"])
            src_ = ao_.outputs["Color"]
        nt_.links.new(src_, em_n.inputs["Color"])
        mx_ = nt_.nodes.new("ShaderNodeMixShader")
        nt_.links.new(bs_.outputs[0], mx_.inputs[1])
        nt_.links.new(em_n.outputs[0], mx_.inputs[2])
        nt_.links.new(mx_.outputs[0], op_.inputs["Surface"])
        inner_mix.append((nm_, mx_))
    fill = bpy.data.objects.new("fill", bpy.data.lights.new("fill", "AREA"))
    fill.location = (mid_tr[0] + 0.40, -0.55, cz + 0.05)
    fill.rotation_euler = (math.radians(80), 0, math.radians(35))
    scene.collection.objects.link(fill)
    LOOKS = {
        # name: view, look, emission mix, saturation, key W/size, fill W/size, rim W, world strength, exposure
        "agx":    ("AgX", ("AgX - Punchy", "Punchy"), 0.0, 1.0, (9, 0.6), (0, 1.0), 7, 0.35, 0.0),
        "paint":  ("Standard", ("None",), 0.55, 1.0, (5, 0.8), (2, 1.2), 4, 0.5, 0.0),
        "studio": ("Standard", ("None",), 0.0, 1.0, (22, 1.4), (10, 1.4), 8, 0.6, -0.3),
        "glow":   ("AgX", ("AgX - Medium High Contrast", "Medium High Contrast", "AgX - Punchy"), 0.3, 1.3, (12, 1.0),
                   (6, 1.2), 10, 0.4, 0.0),
        "ref":    ("Standard", ("None",), 1.0, 1.0, (0, 1.0), (0, 1.0), 0, 0.0, 0.0),
    }

    def set_look(nm):
        vt, lks, emix, sat, (kw, ks), (fw, fs), rw, ws, ex = LOOKS[nm]
        scene.view_settings.view_transform = vt
        for lk in lks:
            try:
                scene.view_settings.look = lk
                break
            except TypeError:
                continue
        scene.view_settings.exposure = ex
        mix_h.inputs[0].default_value = emix
        for nm_, mx_ in inner_mix:
            gain_ = float(os.environ.get("TEETH_PAINT", 0.35)) if nm_ == "teeth" else float(os.environ.get("INNER_PAINT", 0.8))
            mx_.inputs[0].default_value = min(1.0, emix * gain_)
        hsv_h.inputs["Saturation"].default_value = sat
        key.data.energy, key.data.size = kw, ks
        fill.data.energy, fill.data.size = fw, fs
        rim.data.energy = rw
        sun.data.energy = 0.4 if nm != "ref" else 0.0
        world.node_tree.nodes["Background"].inputs["Strength"].default_value = ws
        if bg_rgb:
            world.node_tree.nodes["Background"].inputs["Color"].default_value = (*bg_rgb, 1)
            world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0

    SONG_LOOK = os.environ.get("SONG_LOOK", "agx")
    VARIANTS = [x for x in os.environ.get("LOOKS", "").split(",") if x]
    VFRAMES = [int(x) for x in os.environ.get("SONG_FRAMES", "").split(",") if x]
    if VARIANTS:
        frames = [frames[i] for i in VFRAMES] if VFRAMES else frames[:1]
    else:
        set_look(SONG_LOOK)
    cnt_w2 = np.bincount(weld, minlength=nw).astype(float)
    # rounding top-up: per frame, the MetaHuman's lip-line width change against the Tripo cut's; a shortfall on
    # narrowing is filled with the Tripo pucker shape (which also pouts the lips forward over the teeth). On "o"
    # frames the Tripo lips stayed wide and thin and showed the upper teeth (rounding frames sheet, 2026-11-14).
    ROUND = float(os.environ.get("ROUND_GAIN", 1.0))
    cM = [mouth[np.argmin(A0[mouth][:, 0])], mouth[np.argmax(A0[mouth][:, 0])]]
    _lv = [v for v, (i0, i1, t0, q) in snap.items() if np.linalg.norm(q - mc) < 0.03]
    cT = [min(_lv, key=lambda v: P_full[v, 0]), max(_lv, key=lambda v: P_full[v, 0])] if _lv else None
    kP = NAMES.index("MouthPucker")
    wM0 = np.linalg.norm(A0[cM[0]] - A0[cM[1]])
    wT0 = np.linalg.norm(P_full[cT[0]] - P_full[cT[1]]) if cT else 0
    wP = (np.linalg.norm((P_full[cT[0]] + Ds[kP][cT[0]]) - (P_full[cT[1]] + Ds[kP][cT[1]])) - wT0) if cT else 0
    # the width already matched on the "o" frames (top-up fired on 1 of 4); what differs is the pout: the MetaHuman's
    # lips come forward over the teeth, the Tripo's less (pucker 84 %, funnel 58 % of the forward motion, DIAG)
    lipT_ = (np.linalg.norm(P_full - mc, axis=1) < 0.016) & (P_full[:, 1] < mc[1] + 0.004)
    lipM_ = skin_v & (np.linalg.norm(A0 - mc, axis=1) < 0.016) & (A0[:, 1] < mc[1] + 0.004)
    fP = float(-Ds[kP][lipT_, 1].mean())
    PUCKER_BOOST = float(os.environ.get("PUCKER_BOOST", 0.0))
    POUT_GAIN = float(os.environ.get("POUT_GAIN", 0.0))
    u_p = ((P_full[:, 0] - mc[0]) / 0.030) ** 2 + ((P_full[:, 2] - mc[2]) / 0.018) ** 2
    t_p = np.clip(1.0 - u_p, 0.0, 1.0)
    w_pout = t_p * t_p * (3 - 2 * t_p)
    kF = NAMES.index("MouthFunnel")
    B_pf = np.c_[deltas[kP][lipM_].ravel(), deltas[kF][lipM_].ravel()]
    round_log = []
    # opening boost (OPEN_GAIN, 1.0 = off): the Tripo lips open 0.71 to 0.76 of the Unreal height while the width
    # matches (MediaPipe, 450 frames), so "o" and "u" read as a wide flat slit. Per frame the centre opening above its
    # rest value is scaled by OPEN_GAIN: the upper lip moves up and the lower lip down, full at the slit, fading to zero
    # OPEN_R from it and toward the mouth corners. Which lip a vertex belongs to comes from a geodesic flood over the
    # cut mesh from the labelled slit edges, so the two lips cannot swap (the lip snap tore the lower lip, 2026-11-15).
    OPEN_GAIN = float(os.environ.get("OPEN_GAIN", 1.0))
    open_w = None
    ce0 = [v for v in lip_edge if abs(P_full[v, 0] - mc[0]) < 0.004]
    up0 = [v for v in ce0 if not lower_corner[v]] if lip_edge else []
    lo0 = [v for v in ce0 if lower_corner[v]] if lip_edge else []
    gap0 = (P_full[up0, 2].mean() - P_full[lo0, 2].mean()) if up0 and lo0 else 0.0
    if OPEN_GAIN != 1.0 and lip_edge:
        import heapq
        R_o = float(os.environ.get("OPEN_R", 0.012))
        Pw_ = np.zeros((nw, 3))
        Pw_[weld] = P_full
        fa_ = weld[faces_full[~kill]]
        near_ = np.linalg.norm(Pw_ - mc, axis=1) < 0.035
        ee_ = np.r_[fa_[:, [0, 1]], fa_[:, [1, 2]], fa_[:, [2, 0]]]
        ee_ = ee_[(ee_[:, 0] != ee_[:, 1]) & near_[ee_[:, 0]] & near_[ee_[:, 1]]]
        ln_ = np.linalg.norm(Pw_[ee_[:, 0]] - Pw_[ee_[:, 1]], axis=1)
        adj_ = defaultdict(list)
        for (a_o, b_o), l_o in zip(ee_.tolist(), ln_.tolist()):
            adj_[a_o].append((b_o, l_o))
            adj_[b_o].append((a_o, l_o))
        dist_o = np.full(nw, np.inf)
        lab_o = np.zeros(nw)
        hp_ = []
        for v in lip_edge:
            if keepv[v]:
                w_o = int(weld[v])
                dist_o[w_o] = 0.0
                lab_o[w_o] = -1.0 if lower_corner[v] else 1.0
                hp_.append((0.0, w_o, lab_o[w_o]))
        heapq.heapify(hp_)
        while hp_:
            d_o, a_o, s_o = heapq.heappop(hp_)
            if d_o > dist_o[a_o] or d_o > R_o:
                continue
            for b_o, l_o in adj_[a_o]:
                if d_o + l_o < dist_o[b_o]:
                    dist_o[b_o] = d_o + l_o
                    lab_o[b_o] = s_o
                    heapq.heappush(hp_, (d_o + l_o, b_o, s_o))
        xs_o = P_full[[v for v in lip_edge if keepv[v]], 0]
        xc_o, hw_o = 0.5 * (xs_o.max() + xs_o.min()), 0.5 * (xs_o.max() - xs_o.min())
        prof_o = np.clip(1.0 - ((Pw_[:, 0] - xc_o) / hw_o) ** 2, 0.0, 1.0)
        t_o = np.clip(1.0 - dist_o / R_o, 0.0, 1.0)
        open_w = (lab_o * t_o * t_o * (3 - 2 * t_o) * prof_o)[weld]
        print("OPEN gain", OPEN_GAIN, "R mm", R_o * 1000, "rest gap mm", round(float(gap0) * 1000, 2),
              "weld ids up/low", int(((lab_o > 0) & (t_o > 0)).sum()), int(((lab_o < 0) & (t_o > 0)).sum()),
              "half width mm", round(hw_o * 1000, 1), flush=True)
    # fuller lips (design options, LIP_SETS empty = off): "name:upper:lower:forward_mm:tint:gloss;..." renders every
    # set on every variant frame. The painted lips (texture red minus green, sampled under each vertex) give the
    # vermilion; per 1.5 mm column across the mouth its height above and below the slit sets how far the lip grows:
    # the vermilion stretches away from the slit by upper/lower times its own height, the skin beyond it is pushed
    # along and the push fades to zero 8 mm further out (monotone, so nothing folds), and the vermilion comes forward
    # by forward_mm. tint mixes the painted lip colour toward a more saturated coral (Unreal lips measured sat 0.52,
    # Tripo 0.33 on the paint render, 2026-11-15) and gloss lowers the lip roughness, both only where the texture is lip.
    LIP_SETS = [x for x in os.environ.get("LIP_SETS", "").split(";") if x]
    lip_sets = []
    if LIP_SETS and lip_edge:
        vuv_ = np.zeros((n, 2))
        for j_ in range(3):
            vuv_[faces_full[:, j_]] = tri_uv[:, j_]
        im_ = img_h.image
        w_i, h_i = im_.size
        px_ = np.empty(w_i * h_i * 4, np.float32)
        im_.pixels.foreach_get(px_)
        px_ = px_.reshape(h_i, w_i, 4)
        col_ = px_[np.clip((vuv_[:, 1] % 1.0) * h_i, 0, h_i - 1).astype(int),
                   np.clip((vuv_[:, 0] % 1.0) * w_i, 0, w_i - 1).astype(int), :3].astype(np.float64)
        del px_
        LIP_LO, LIP_HI = float(os.environ.get("LIP_LO", 0.17)), float(os.environ.get("LIP_HI", 0.28))
        front_ = P_full[:, 1] < mc[1] + 0.01
        reg_u = ((P_full[:, 0] - mc[0]) / 0.030) ** 2 + ((P_full[:, 2] - mc[2]) / 0.016) ** 2
        lm_ = np.clip((col_[:, 0] - col_[:, 1] - LIP_LO) / (LIP_HI - LIP_LO), 0.0, 1.0) * ((reg_u < 1.0) & front_)

        def wsmooth_(f_, it_):
            fw_ = np.bincount(weld, weights=f_, minlength=nw) / np.maximum(cnt_w2, 1)
            for _ in range(it_):
                acc_ = (np.bincount(e_[:, 0], weights=fw_[e_[:, 1]], minlength=nw) +
                        np.bincount(e_[:, 1], weights=fw_[e_[:, 0]], minlength=nw))
                fw_ = np.where(deg > 0, 0.5 * fw_ + 0.5 * acc_ / np.maximum(deg, 1), fw_)
            return fw_[weld]

        lms_ = wsmooth_(lm_, 2)
        # which lip a vertex belongs to: a geodesic flood over the cut mesh from the labelled slit edges. The sign of the
        # height above one mean slit line put the lower lip's inner surface, which rises behind the slit, on the upper
        # lip, so it was pulled up while the lip around it went down: a fold on open frames (T41 frame 90, 2026-11-15).
        import heapq
        Pl_ = np.zeros((nw, 3))
        Pl_[weld] = P_full
        fl_ = weld[faces_full[~kill]]
        el_ = np.r_[fl_[:, [0, 1]], fl_[:, [1, 2]], fl_[:, [2, 0]]]
        nl_ = np.linalg.norm(Pl_ - mc, axis=1) < 0.045
        el_ = el_[(el_[:, 0] != el_[:, 1]) & nl_[el_[:, 0]] & nl_[el_[:, 1]]]
        adjl_ = defaultdict(list)
        for (a_l, b_l), l_l in zip(el_.tolist(), np.linalg.norm(Pl_[el_[:, 0]] - Pl_[el_[:, 1]], axis=1).tolist()):
            adjl_[a_l].append((b_l, l_l))
            adjl_[b_l].append((a_l, l_l))
        dl_ = np.full(nw, np.inf)
        labw_ = np.zeros(nw)
        hpl_ = []
        le_ = np.array([v for v in lip_edge if keepv[v]])
        for v in le_:
            dl_[weld[v]] = 0.0
            labw_[weld[v]] = -1.0 if lower_corner[v] else 1.0
            hpl_.append((0.0, int(weld[v]), labw_[weld[v]]))
        heapq.heapify(hpl_)
        while hpl_:
            d_l, a_l, s_l = heapq.heappop(hpl_)
            if d_l > dl_[a_l]:
                continue
            for b_l, l_l in adjl_[a_l]:
                if d_l + l_l < dl_[b_l]:
                    dl_[b_l] = d_l + l_l
                    labw_[b_l] = s_l
                    heapq.heappush(hpl_, (d_l + l_l, b_l, s_l))
        lab_ = labw_[weld]

        def edge_line(vs_):
            xs_, zs_ = P_full[vs_, 0], P_full[vs_, 2]
            xb_ = np.arange(xs_.min(), xs_.max() + 1e-4, 0.0015)
            zb_ = np.array([zs_[np.abs(xs_ - x_) < 0.0015].mean() if (np.abs(xs_ - x_) < 0.0015).any() else np.nan
                            for x_ in xb_])
            return xb_[~np.isnan(zb_)], zb_[~np.isnan(zb_)]

        xu_, zu_ = edge_line(le_[~lower_corner[le_]])
        xl_, zl_ = edge_line(le_[lower_corner[le_]])
        # height of every vertex away from its own lip's edge (0 behind the edge, where the lip turns inward)
        a_ = np.where(lab_ > 0, np.maximum(P_full[:, 2] - np.interp(P_full[:, 0], xu_, zu_), 0.0),
                      np.where(lab_ < 0, np.maximum(np.interp(P_full[:, 0], xl_, zl_) - P_full[:, 2], 0.0), 0.0))
        xb_ = np.arange(max(xu_.min(), xl_.min()), min(xu_.max(), xl_.max()) + 1e-4, 0.0015)
        hu_, hl_ = np.zeros(len(xb_)), np.zeros(len(xb_))
        for i_, x_ in enumerate(xb_):
            cs_ = (np.abs(P_full[:, 0] - x_) < 0.0012) & front_ & (a_ < 0.012) & (lms_ > 0.5)
            hu_[i_] = a_[cs_ & (lab_ > 0)].max() if (cs_ & (lab_ > 0)).any() else 0.0
            hl_[i_] = a_[cs_ & (lab_ < 0)].max() if (cs_ & (lab_ < 0)).any() else 0.0
        hu_ = np.convolve(hu_, np.ones(3) / 3, "same")
        hl_ = np.convolve(hl_, np.ones(3) / 3, "same")
        hv_ = np.where(lab_ > 0, np.interp(P_full[:, 0], xb_, hu_, left=0.0, right=0.0),
                       np.interp(P_full[:, 0], xb_, hl_, left=0.0, right=0.0))
        uf_ = np.clip(1.0 - np.maximum(a_ - hv_, 0.0) / 0.008, 0.0, 1.0)
        base_ = np.sign(lab_) * np.minimum(a_, hv_) * uf_ * uf_ * (3 - 2 * uf_) * front_
        t_ = lab_
        print("LIPS vermilion height mm upper max/mean", round(float(hu_.max()) * 1000, 2), round(float(hu_[hu_ > 0].mean()) * 1000, 2),
              "lower", round(float(hl_.max()) * 1000, 2), round(float(hl_[hl_ > 0].mean()) * 1000, 2),
              "lip verts", int((lms_ > 0.5).sum()), "columns", len(xb_), "upper/lower/unlabelled verts near mouth",
              int(((lab_ > 0) & (np.linalg.norm(P_full - mc, axis=1) < 0.03)).sum()),
              int(((lab_ < 0) & (np.linalg.norm(P_full - mc, axis=1) < 0.03)).sum()),
              int(((lab_ == 0) & (np.linalg.norm(P_full - mc, axis=1) < 0.03)).sum()), flush=True)
        # lip colour and gloss nodes, driven per set; the region attribute keeps them off the cheeks and the nose
        ca_ = me.color_attributes.new("lipreg", "FLOAT_COLOR", "POINT")
        rg_ = (np.sqrt(np.clip(1.0 - reg_u, 0.0, 1.0)) * front_)[keepv]
        ca_.data.foreach_set("color", np.c_[rg_, rg_, rg_, np.ones_like(rg_)].ravel())
        # gloss stays off the slit edge: the cut edge is jagged at the scale of one triangle, and a glossy lip turned it
        # into a row of white specks on open frames (T41 frame 90); 0 within 1 mm of the edge, full from 2.5 mm
        from mathutils.kdtree import KDTree as _KDe
        kde_ = _KDe(len(le_))
        for j_, v in enumerate(le_):
            kde_.insert(Vector(P_full[v]), j_)
        kde_.balance()
        Pk_ = P_full[keepv]
        de_ = np.array([kde_.find(Vector(p_))[2] for p_ in Pk_])
        ge_ = np.clip((de_ - 0.001) / 0.0015, 0.0, 1.0)
        ge_ = rg_ * ge_ * ge_ * (3 - 2 * ge_)
        cg_ = me.color_attributes.new("lipgloss", "FLOAT_COLOR", "POINT")
        cg_.data.foreach_set("color", np.c_[ge_, ge_, ge_, np.ones_like(ge_)].ravel())
        cso_ = img_h.outputs["Color"]
        to_ = [l_.to_socket for l_ in hn_.links if l_.from_socket == cso_]
        gm_ = hn_.nodes.new("ShaderNodeGamma")
        gm_.inputs["Gamma"].default_value = 1.0 / 2.2
        hn_.links.new(cso_, gm_.inputs["Color"])
        sp_ = hn_.nodes.new("ShaderNodeSeparateColor")
        hn_.links.new(gm_.outputs["Color"], sp_.inputs["Color"])
        sb_ = hn_.nodes.new("ShaderNodeMath")
        sb_.operation = "SUBTRACT"
        hn_.links.new(sp_.outputs[0], sb_.inputs[0])
        hn_.links.new(sp_.outputs[1], sb_.inputs[1])
        mrn_ = hn_.nodes.new("ShaderNodeMapRange")
        mrn_.clamp = True
        mrn_.inputs["From Min"].default_value, mrn_.inputs["From Max"].default_value = LIP_LO, LIP_HI
        hn_.links.new(sb_.outputs[0], mrn_.inputs["Value"])
        va_ = hn_.nodes.new("ShaderNodeVertexColor")
        va_.layer_name = "lipreg"
        lmask_ = hn_.nodes.new("ShaderNodeMath")
        lmask_.operation = "MULTIPLY"
        hn_.links.new(mrn_.outputs["Result"], lmask_.inputs[0])
        hn_.links.new(va_.outputs["Color"], lmask_.inputs[1])
        tf_ = hn_.nodes.new("ShaderNodeMath")
        tf_.operation = "MULTIPLY"
        hn_.links.new(lmask_.outputs[0], tf_.inputs[0])
        hs_ = hn_.nodes.new("ShaderNodeHueSaturation")
        hs_.inputs["Hue"].default_value = 0.5 + float(os.environ.get("LIP_HUE", 0.012))
        hs_.inputs["Saturation"].default_value = float(os.environ.get("LIP_SAT", 1.6))
        hs_.inputs["Value"].default_value = float(os.environ.get("LIP_VAL", 1.0))
        hn_.links.new(cso_, hs_.inputs["Color"])
        mxc_ = hn_.nodes.new("ShaderNodeMix")
        mxc_.data_type = "RGBA"
        hn_.links.new(tf_.outputs[0], mxc_.inputs[0])
        hn_.links.new(cso_, mxc_.inputs[6])
        hn_.links.new(hs_.outputs["Color"], mxc_.inputs[7])
        for to_s in to_:
            hn_.links.new(mxc_.outputs[2], to_s)
        vg_ = hn_.nodes.new("ShaderNodeVertexColor")
        vg_.layer_name = "lipgloss"
        gm2_ = hn_.nodes.new("ShaderNodeMath")
        gm2_.operation = "MULTIPLY"
        hn_.links.new(mrn_.outputs["Result"], gm2_.inputs[0])
        hn_.links.new(vg_.outputs["Color"], gm2_.inputs[1])
        gf_ = hn_.nodes.new("ShaderNodeMath")
        gf_.operation = "MULTIPLY"
        hn_.links.new(gm2_.outputs[0], gf_.inputs[0])
        mxr_ = hn_.nodes.new("ShaderNodeMix")
        mxr_.data_type = "FLOAT"
        hn_.links.new(gf_.outputs[0], mxr_.inputs[0])
        r_in = bsdf_h.inputs["Roughness"]
        if r_in.links:
            hn_.links.new(r_in.links[0].from_socket, mxr_.inputs[2])
        else:
            mxr_.inputs[2].default_value = r_in.default_value
        mxr_.inputs[3].default_value = float(os.environ.get("LIP_ROUGH", 0.2))
        hn_.links.new(mxr_.outputs[0], r_in)
        for spec_ in LIP_SETS:
            nm_s, gu_s, gl_s, fw_s, ti_s, gs_s = spec_.split(":")
            Dl_ = np.zeros((n, 3))
            Dl_[:, 2] = np.where(lab_ > 0, float(gu_s), float(gl_s)) * base_
            Dl_[:, 1] = -float(fw_s) / 1000.0 * lms_
            Dl_[:, 1], Dl_[:, 2] = wsmooth_(Dl_[:, 1], 3), wsmooth_(Dl_[:, 2], 3)
            lip_sets.append({"name": nm_s, "D": Dl_, "tint": float(ti_s), "gloss": float(gs_s)})
            print("LIPS set", nm_s, "max up/down/forward mm", round(float(Dl_[:, 2].max()) * 1000, 2),
                  round(float(-Dl_[:, 2].min()) * 1000, 2), round(float(-Dl_[:, 1].min()) * 1000, 2), flush=True)

        def set_lip(ls_):
            tf_.inputs[1].default_value = ls_["tint"]
            gf_.inputs[1].default_value = ls_["gloss"]
    # corner seal (SEAL, 0 = off): the Tripo slit is cut in the outer surface, so where the MetaHuman's lips part 1 to 2
    # cm inside the mouth, ours part at the surface and the open corners showed the dark side wall of the mouth as black
    # wedges (dark corner area 7.7x Unreal's over the song, 2026-11-15). Per frame, every slit edge vertex within SEAL_W
    # of either end moves toward the midline between the two lips, SEAL at the very end fading to 0 at SEAL_W, never
    # past it; the shift spreads into the lip over SEAL_R (geodesic, from the nearest edge vertex).
    SEAL = float(os.environ.get("SEAL", 0.0))
    seal_ = None
    if SEAL > 0 and lip_edge:
        import heapq
        SEAL_W = float(os.environ.get("SEAL_W", 0.008))
        SEAL_R = float(os.environ.get("SEAL_R", 0.005))
        les_ = np.array([v for v in lip_edge if keepv[v]])
        Ps_ = np.zeros((nw, 3))
        Ps_[weld] = P_full
        fs_ = weld[faces_full[~kill]]
        es_ = np.r_[fs_[:, [0, 1]], fs_[:, [1, 2]], fs_[:, [2, 0]]]
        ns_ = np.linalg.norm(Ps_ - mc, axis=1) < 0.045
        es_ = es_[(es_[:, 0] != es_[:, 1]) & ns_[es_[:, 0]] & ns_[es_[:, 1]]]
        adjs_ = defaultdict(list)
        for (a_s, b_s), l_s in zip(es_.tolist(), np.linalg.norm(Ps_[es_[:, 0]] - Ps_[es_[:, 1]], axis=1).tolist()):
            adjs_[a_s].append((b_s, l_s))
            adjs_[b_s].append((a_s, l_s))
        dsw_ = np.full(nw, np.inf)
        srcw_ = -np.ones(nw, int)
        hps_ = []
        for j_, v in enumerate(les_):
            w_s = int(weld[v])
            if dsw_[w_s] > 0:
                dsw_[w_s] = 0.0
                srcw_[w_s] = j_
                hps_.append((0.0, w_s, j_))
        heapq.heapify(hps_)
        while hps_:
            d_s, a_s, j_s = heapq.heappop(hps_)
            if d_s > dsw_[a_s] or d_s > SEAL_R:
                continue
            for b_s, l_s in adjs_[a_s]:
                if d_s + l_s < dsw_[b_s]:
                    dsw_[b_s] = d_s + l_s
                    srcw_[b_s] = j_s
                    heapq.heappush(hps_, (d_s + l_s, b_s, j_s))
        ts_ = np.clip(1.0 - dsw_ / SEAL_R, 0.0, 1.0)
        seal_ = (les_, ~lower_corner[les_], srcw_[weld], (ts_ * ts_ * (3 - 2 * ts_))[weld], SEAL_W)
        # fully closed over the last SEAL_C (a seal fading from the very end left hairline slits that showed the dark
        # mouth as specks), and the shift is smoothed over the skin with the slit edge held, because the nearest-edge
        # spread switched between the upper and the lower lip beyond the corner and creased the skin there (T50)
        SEAL_C = float(os.environ.get("SEAL_C", 0.002))
        SEAL_SMOOTH = int(os.environ.get("SEAL_SMOOTH", 4))
        print("SEAL gain", SEAL, "W mm", SEAL_W * 1000, "R mm", SEAL_R * 1000, "edge verts", len(les_),
              "verts moved", int((srcw_[weld] >= 0).sum()), flush=True)
    if os.environ.get("LIP_DUMP"):
        # lip design probe: rest geometry, the painted colour under every vertex and the mouth labels, for offline work
        vuv_ = np.zeros((n, 2))
        for j_ in range(3):
            vuv_[faces_full[:, j_]] = tri_uv[:, j_]
        im_ = img_h.image
        w_i, h_i = im_.size
        px_ = np.empty(w_i * h_i * 4, np.float32)
        im_.pixels.foreach_get(px_)
        px_ = px_.reshape(h_i, w_i, 4)
        xi_ = np.clip((vuv_[:, 0] % 1.0) * w_i, 0, w_i - 1).astype(int)
        yi_ = np.clip((vuv_[:, 1] % 1.0) * h_i, 0, h_i - 1).astype(int)
        np.savez_compressed(os.environ["LIP_DUMP"], P_full=P_full, faces=faces_full, kill=kill, keepv=keepv, weld=weld,
                            vuv=vuv_, col=px_[yi_, xi_, :3], lip_edge=np.array(lip_edge), lower=lower_corner, mc=mc,
                            tex=(np.clip(px_[..., :3], 0, 1) * 255).astype(np.uint8), cs=im_.colorspace_settings.name)
        print("LIP_DUMP", os.environ["LIP_DUMP"], "tex", w_i, h_i, im_.colorspace_settings.name, flush=True)
    for fi_, fp in enumerate(frames):
        X = np.fromfile(fp, dtype=np.float32).reshape(-1, 3).astype(np.float64)
        X = np.c_[X[:, 0], -X[:, 1], X[:, 2]] / 100.0
        Xa = apply(T, X)
        if LM:
            Xw = np.vstack([tps_apply(src, Cw, Xa[i_:i_ + 4000]) for i_ in range(0, len(Xa), 4000)])
        else:
            Xw = Xa
        dlt = Xw - A0
        D = np.zeros((n, 3))
        D[on] = (dlt[tt[on, 0]] * bc[on, 0:1] + dlt[tt[on, 1]] * bc[on, 1:2] + dlt[tt[on, 2]] * bc[on, 2:3]) * wgt[on, None]
        Dw = np.zeros((nw, 3))
        for ax in range(3):
            Dw[:, ax] = np.bincount(weld, weights=D[:, ax], minlength=nw) / np.maximum(cnt_w2, 1)
        act = np.linalg.norm(Dw, axis=1) > 1e-6
        for _ in range(SMOOTH):
            acc = np.zeros((nw, 3))
            for ax in range(3):
                acc[:, ax] = (np.bincount(e_[:, 0], weights=Dw[e_[:, 1], ax], minlength=nw) +
                              np.bincount(e_[:, 1], weights=Dw[e_[:, 0], ax], minlength=nw))
            avg = acc / np.maximum(deg, 1)[:, None]
            upd = act & ~pin_w & (deg > 0)
            Dw[upd] = 0.5 * Dw[upd] + 0.5 * avg[upd]
        D = Dw[weld]
        for v, (i0, i1, t0, q) in snap.items():
            D[v] = (1 - t0) * dlt[i0] + t0 * dlt[i1]
        for kname, (corr, up_mh, ref_dz) in blink_corr.items():
            amt = float(np.clip(dlt[up_mh][:, 2].mean() / ref_dz, 0.0, 1.1)) if ref_dz < -1e-6 else 0.0
            D += amt * corr
        # lip opening at the centre: Tripo cut edge vertices within 4 mm of the middle, upper half against lower
        Xs_ = P_full + D
        up_, lo_ = up0, lo0
        gap_ = (Xs_[up_, 2].mean() - Xs_[lo_, 2].mean()) if up_ and lo_ else 0.01
        if open_w is not None:
            D[:, 2] += 0.5 * (OPEN_GAIN - 1.0) * max(gap_ - gap0, 0.0) * open_w
            if VARIANTS:
                Xb_ = P_full + D
                print("OPEN", fp.stem, "gap mm", round(float(gap_) * 1000, 2), "->",
                      round(float(Xb_[up_, 2].mean() - Xb_[lo_, 2].mean()) * 1000, 2), flush=True)
        if os.environ.get("SEAL_DIAG") == "1" and lip_edge:
            # opening along the mouth, MetaHuman inner lip loop against the Tripo slit edge, each from corner to corner
            # at 9 points, divided by its own centre opening (MediaPipe returned one template profile for both)
            def open_prof(pts_up, pts_lo):
                x0_, x1_ = min(pts_up[:, 0].min(), pts_lo[:, 0].min()), max(pts_up[:, 0].max(), pts_lo[:, 0].max())
                fx_ = x0_ + (x1_ - x0_) * np.linspace(0.05, 0.95, 9)
                ou_ = np.argsort(pts_up[:, 0])
                ol_ = np.argsort(pts_lo[:, 0])
                g_p = np.interp(fx_, pts_up[ou_, 0], pts_up[ou_, 2]) - np.interp(fx_, pts_lo[ol_, 0], pts_lo[ol_, 2])
                return g_p, x1_ - x0_
            Xm_ = Xw[mouth]
            cl_, cr_ = Xm_[np.argmin(Xm_[:, 0])], Xm_[np.argmax(Xm_[:, 0])]
            zl_ = cl_[2] + (Xm_[:, 0] - cl_[0]) / max(cr_[0] - cl_[0], 1e-6) * (cr_[2] - cl_[2])
            gm_p, wm_ = open_prof(Xm_[Xm_[:, 2] >= zl_], Xm_[Xm_[:, 2] < zl_])
            Xt_ = (P_full + D)
            leu_ = [v for v in lip_edge if keepv[v] and not lower_corner[v]]
            lel_ = [v for v in lip_edge if keepv[v] and lower_corner[v]]
            gt_p, wt_ = open_prof(Xt_[leu_], Xt_[lel_])
            print("SEAL", fp.stem, "centre gap mm MH", round(float(gm_p[4]) * 1000, 2), "T", round(float(gt_p[4]) * 1000, 2),
                  "width mm MH", round(float(wm_) * 1000, 1), "T", round(float(wt_) * 1000, 1),
                  "profile MH", np.round(gm_p / max(gm_p[4], 1e-6), 2).tolist(), "T", np.round(gt_p / max(gt_p[4], 1e-6), 2).tolist(), flush=True)
        if teeth_gain_node is not None and lip_edge:
            # the teeth light follows the opening before the boost, as tested on T26
            g_ = float(np.clip((gap_ - 0.0015) / float(os.environ.get("TEETH_OPEN", 0.006)), float(os.environ.get("TEETH_MIN", 0.35)), 1.0))
            # TEETH_TINT: ivory instead of neutral grey; the whitened bake read as grey next to Unreal's warm teeth
            # (teeth pixels R:B 1.05 against Unreal's 1.29, song T56, 2026-11-15)
            tt_ = [float(c_) for c_ in os.environ.get("TEETH_TINT", "1,1,1").split(",")]
            teeth_gain_node.inputs[7].default_value = (g_ * tt_[0], g_ * tt_[1], g_ * tt_[2], 1)
            if VARIANTS:
                print("TEETH", fp.stem, "gap mm", round(float(gap_) * 1000, 2), "gain", round(g_, 2), "edge verts up/low", len(up_), len(lo_), flush=True)
        if POUT_GAIN > 0:
            # rounding gain (design option, 0 = off): the frame's own lip motion toward the mouth's midline and forward
            # is amplified by POUT_GAIN around the mouth (elliptical falloff, 30 mm across, 18 mm up and down). The
            # transfer already narrows and pouts as much as the MetaHuman (rest to "o": width -7.7 % against -8.2 %);
            # this goes past it, because the Tripo mouth is 12 % wider and 14 % lower at rest by design.
            side_ = np.sign(P_full[:, 0] - mc[0])
            D[:, 0] += POUT_GAIN * w_pout * np.minimum(D[:, 0] * side_, 0.0) * side_
            D[:, 1] += POUT_GAIN * w_pout * np.minimum(D[:, 1], 0.0)
        if PUCKER_BOOST > 0:
            # pout boost (design option, 0 = off): the MetaHuman's pucker and funnel amounts on this frame, fitted by
            # least squares to its lip motion, add PUCKER_BOOST times the same amounts of the Tripo pucker and funnel
            # shapes. Measured on the paint render: rest to "o" narrows as much as Unreal, but the lips pout less
            # (MediaPipe pucker 60 % of Unreal, upper lip thickening 6 % against 9 %).
            y_ = dlt[lipM_].ravel()
            a_pf = np.clip(np.linalg.lstsq(B_pf, y_, rcond=None)[0], 0.0, 1.5)
            D += PUCKER_BOOST * (a_pf[0] * Ds[kP] + a_pf[1] * Ds[kF])
            if VARIANTS:
                print("POUT", fp.stem, "pucker", round(float(a_pf[0]), 2), "funnel", round(float(a_pf[1]), 2), flush=True)
        if ROUND > 0 and fP > 1e-4:
            fM = float(-dlt[lipM_, 1].mean())
            fT = float(-D[lipT_, 1].mean())
            amt = float(np.clip(ROUND * (fM - fT) / fP, 0.0, 1.0)) if fM > 0 else 0.0
            D += amt * Ds[kP]
            round_log.append((round(fM * 1000, 2), round(fT * 1000, 2), round(amt, 3)))
        if seal_ is not None:
            les_, ups_, srcv_, fallv_, SEAL_W = seal_
            Xe_ = P_full[les_] + D[les_]
            ou_ = np.argsort(Xe_[ups_, 0])
            ol_ = np.argsort(Xe_[~ups_, 0])
            zm_ = 0.5 * (np.interp(Xe_[:, 0], Xe_[ups_, 0][ou_], Xe_[ups_, 2][ou_]) +
                         np.interp(Xe_[:, 0], Xe_[~ups_, 0][ol_], Xe_[~ups_, 2][ol_]))
            dc_ = np.minimum(Xe_[:, 0] - Xe_[:, 0].min(), Xe_[:, 0].max() - Xe_[:, 0])
            u_s = np.clip((dc_ - SEAL_C) / max(SEAL_W - SEAL_C, 1e-6), 0.0, 1.0)
            dze_ = SEAL * (1.0 - u_s * u_s * (3 - 2 * u_s)) * (zm_ - Xe_[:, 2])
            dze_ = np.where(ups_, np.minimum(dze_, 0.0), np.maximum(dze_, 0.0))   # close, never open
            # the two lips also meet in depth: sealed in height only, the upper lip's corner hung in front of the
            # lower one and showed as a thin red spike from 35 degrees (T54)
            ym_ = 0.5 * (np.interp(Xe_[:, 0], Xe_[ups_, 0][ou_], Xe_[ups_, 1][ou_]) +
                         np.interp(Xe_[:, 0], Xe_[~ups_, 0][ol_], Xe_[~ups_, 1][ol_]))
            dye_ = float(os.environ.get("SEAL_Y", 1.0)) * SEAL * (1.0 - u_s * u_s * (3 - 2 * u_s)) * (ym_ - Xe_[:, 1])
            ok_s = srcv_ >= 0
            pin_s = weld[les_]
            for ax_s, de_s in ((2, dze_), (1, dye_)):
                fz_ = np.zeros(n)
                fz_[ok_s] = de_s[srcv_[ok_s]] * fallv_[ok_s]
                fzw_ = np.bincount(weld, weights=fz_, minlength=nw) / np.maximum(cnt_w2, 1)
                pv_s = fzw_[pin_s].copy()
                for _ in range(SEAL_SMOOTH):
                    acc_s = (np.bincount(e_[:, 0], weights=fzw_[e_[:, 1]], minlength=nw) +
                             np.bincount(e_[:, 1], weights=fzw_[e_[:, 0]], minlength=nw))
                    fzw_ = np.where(deg > 0, 0.5 * fzw_ + 0.5 * acc_s / np.maximum(deg, 1), fzw_)
                    fzw_[pin_s] = pv_s
                D[:, ax_s] += fzw_[weld]
        if k_song_i is not None:
            Xi_ = A0[idx] + dlt[idx]
            if teeth_sim:
                for g_, sc_, R_, t_s in teeth_sim:
                    Xi_[g_] = (sc_ * (R_ @ Xa[idx][g_].T)).T + t_s
            k_song_i.data.foreach_set("co", (Xi_ + off).ravel())
        for ls_ in (lip_sets if VARIANTS else lip_sets[:1]) or [None]:
            if ls_ is not None:
                set_lip(ls_)
            k_song.data.foreach_set("co", (P + (D if ls_ is None else D + ls_["D"])[keepv]).ravel())
            dr.data.update()
            for nm in VARIANTS:
                set_look(nm)
                scene.render.filepath = str(SONG_OUT / f"look_{nm}{'' if ls_ is None else '_' + ls_['name']}_{fp.stem}.png")
                bpy.ops.render.render(write_still=True)
        if VARIANTS:
            continue
        scene.render.filepath = str(SONG_OUT / f"{fi_:05d}.png")
        bpy.ops.render.render(write_still=True)
        if fi_ % 25 == 0:
            print("SONG frame", fi_, "of", len(frames), flush=True)
    if round_log:
        rl = np.array(round_log)
        print("ROUND frames topped up", int((rl[:, 2] > 0.02).sum()), "of", len(rl), "mean amount", round(float(rl[:, 2].mean()), 3),
              "max", round(float(rl[:, 2].max()), 3), flush=True)
    print("SONG done", len(frames), flush=True)

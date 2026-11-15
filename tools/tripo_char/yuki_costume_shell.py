"""Yuki's costume built from her own MetaHuman body mesh, so it fits and deforms exactly like the body.

    HEAD_FBX=<head.fbx> ./blender_headless.sh yuki_costume_shell.py -- <yuki_fullbody.fbx> <yuki_body.fbx> <out_dir>

<yuki_fullbody.fbx> is the complete body (ue_export_yuki_fullbody), <yuki_body.fbx> the built Body mesh, which lacks
what the default T-shirt and shorts covered. The costume mesh therefore also carries the missing skin (material
yuki_skin): the faces of the complete body that the built mesh does not have.

The concept's costume is skin tight except for the skirt: a black latex corset with a sweetheart top, a choker with a
bell, two bands on each upper arm, wrist cuffs, fingerless gloves, thigh-high boots, a pleated skirt, and pink neon
lines along the edges. Each tight piece is a copy of the body's own faces in that region (regions from the bone a
vertex follows most and its place along that bone), pushed out along the normals; the copy keeps the body's skin
weights. The border of every piece is smoothed along the body's surface (whole faces alone gave staircase edges).
Neon is thin ribbons laid on the pieces, as in the concept: along the corset's top edge and the boot tops, down the
corset's centre front and two side seams, and down the front of each boot. Arm bands, cuffs and the choker are a matt
strap material. The skirt is a pleated ring with a tight waistband; it follows the pelvis and, by distance, the
thighs; the bell follows the neck.
Writes yuki_costume.fbx (armature + one mesh, materials yuki_latex / yuki_neon / yuki_gold / yuki_skin / yuki_strap),
a report and check renders."""
import json
import math
import os
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

src, built_p, out = str(Path(sys.argv[-3]).resolve()), str(Path(sys.argv[-2]).resolve()), Path(sys.argv[-1]).resolve()
out.mkdir(parents=True, exist_ok=True)
OFF = float(os.environ.get("OFFSET", 0.003))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=src)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
body = max((o for o in bpy.data.objects if o.type == "MESH"), key=lambda o: len(o.data.vertices))
bpy.context.view_layer.update()
me = body.data
MW = body.matrix_world
W = np.array([MW @ v.co for v in me.vertices])
NW = np.array([(MW.to_3x3() @ v.normal).normalized() for v in me.vertices])
gname = {g.index: g.name for g in body.vertex_groups}
dom = []
for v in me.vertices:
    dom.append(gname[max(v.groups, key=lambda g: g.weight).group] if v.groups else "")
dom = np.array(dom)


def J(name):
    b = arm.data.bones[name]
    return np.array(arm.matrix_world @ b.head_local)


def region(n):
    n = n.lower()
    side = "_l" if n.endswith("_l") or "_l_" in n else "_r" if n.endswith("_r") or "_r_" in n else ""
    if "toe" in n:
        return "foot" + side
    for key, r in (("thumb", "finger"), ("index", "finger"), ("middle", "finger"), ("ring", "finger"), ("pinky", "finger"), ("thigh", "thigh"), ("calf", "calf"),
                   ("foot", "foot"), ("ball", "foot"), ("toe", "foot"), ("upperarm", "upperarm"), ("lowerarm", "lowerarm"), ("hand", "hand"), ("clavicle", "clavicle"),
                   ("neck", "neck"), ("head", "head"), ("spine", "spine"), ("pelvis", "pelvis")):
        if key in n:
            if r == "finger" and "metacarpal" in n:
                return "hand" + side
            return r + (side if r not in ("neck", "head", "spine", "pelvis") else "")
    return "other"


reg = np.array([region(n) for n in dom])
fwd = J("ball_l") - J("foot_l")
fwd[2] = 0
fwd /= np.linalg.norm(fwd)
up = np.array([0.0, 0.0, 1.0])
side = np.cross(up, fwd)                       # to the character's left if fwd is her front
c0 = J("pelvis")
U, D, Z = (W - c0) @ side, (W - c0) @ fwd, W[:, 2]
pel_z, neck_z, head_z = J("pelvis")[2], J("neck_01")[2], J("head")[2]
rep = {"vertices": len(W), "pelvis_z": round(float(pel_z), 3), "neck_z": round(float(neck_z), 3), "head_z": round(float(head_z), 3), "height": round(float(Z.max() - Z.min()), 3),
       "regions": {r: int((reg == r).sum()) for r in sorted(set(reg))}}


def along(a, b):
    A, B = J(a), J(b)
    d = B - A
    return ((W - A) @ d) / float(d @ d)


# the built body, read early: where its upper arm begins is where the costume's skin patch meets it, and the first arm
# band is put on that seam (a faint line showed there in Unreal, stills c2)
before_b = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=built_p)
bobjs = [o for o in bpy.data.objects if o not in before_b]
bm_ = max((o for o in bobjs if o.type == "MESH"), key=lambda o: len(o.data.vertices))
bpy.context.view_layer.update()
Bw = np.array([bm_.matrix_world @ v.co for v in bm_.data.vertices])
seam = {}
for s_ in ("l", "r"):
    A_, B_ = J("upperarm_" + s_), J("lowerarm_" + s_)
    d_ = B_ - A_
    al = ((Bw - A_) @ d_) / float(d_ @ d_)
    dist = np.linalg.norm((Bw - A_) - np.outer(al, d_), axis=1)
    k_ = (dist < 0.08) & (al > 0.02) & (al < 0.9)
    seam[s_] = float(al[k_].min()) if k_.any() else 0.32
rep["arm_seam_along"] = {k: round(v, 3) for k, v in seam.items()}
torso = np.isin(reg, ["spine", "pelvis", "clavicle_l", "clavicle_r"])
base_top = pel_z + float(os.environ.get("BUST_TOP", 0.60)) * (neck_z - pel_z)
top = np.where(D > 0, base_top + 0.028 * np.exp(-((np.abs(U) - 0.075) / 0.045) ** 2) - 0.022 * np.exp(-(U / 0.022) ** 2), base_top - 0.035)
BOOT_TOP = float(os.environ.get("BOOT_TOP", 0.50))   # along the thigh; the concept leaves bare thigh under the skirt
piece = np.zeros(len(W), int)                  # 0 none, 1 corset, 2 choker, 3 bands and cuffs, 4 gloves, 5 boots
piece[torso & (Z < top) & (Z > pel_z + float(os.environ.get("CORSET_BOTTOM", -0.30))) & (np.abs(U) < 0.21)] = 1
# the neck is part of the face mesh, not of the body: the choker is built further down as its own ring
for s_ in ("l", "r"):
    a_ = along("upperarm_" + s_, "lowerarm_" + s_)
    sm_ = seam[s_]
    piece[(reg == "upperarm_" + s_) & (((a_ > sm_ - 0.045) & (a_ < sm_ + 0.045)) | ((a_ > sm_ + 0.10) & (a_ < sm_ + 0.18)))] = 3
    f_ = along("lowerarm_" + s_, "hand_" + s_)
    piece[(reg == "lowerarm_" + s_) & (f_ > 0.80)] = 3
    piece[reg == "hand_" + s_] = 4
    t_ = along("thigh_" + s_, "calf_" + s_)
    piece[((reg == "thigh_" + s_) & (t_ > BOOT_TOP)) | (reg == "calf_" + s_) | (reg == "foot_" + s_)] = 5
rep["piece_vertices"] = {str(k): int((piece == k).sum()) for k in (1, 3, 4, 5)}

# ---- the tight pieces: a copy of the body with only the kept faces
cos = body.copy()
cos.data = me.copy()
cos.name = cos.data.name = "yuki_costume"
bpy.context.scene.collection.objects.link(cos)
bm = bmesh.new()
bm.from_mesh(cos.data)
bm.verts.ensure_lookup_table()
# The corset takes every torso face that touches its region; the vertices above its top line are then slid down onto
# the line along the body's surface. Whole faces only gave a staircase edge (first build, 2026-11-14).
torso_any = torso & (Z > pel_z + float(os.environ.get("CORSET_BOTTOM", -0.30))) & (np.abs(U) < 0.21)
def keep_face(f):
    ps = {piece[v.index] for v in f.verts}
    if 1 in ps and all(torso_any[v.index] for v in f.verts) and ps <= {0, 1}:
        return True
    return len(ps) == 1 and 0 not in ps
kill = [f for f in bm.faces if not keep_face(f)]
pid = {v: (piece[v.index] if piece[v.index] else 1) for v in bm.verts}
from mathutils.bvhtree import BVHTree as _BT
full_bvh = _BT.FromPolygons([MW @ v.co for v in me.vertices], [tuple(q.vertices) for q in me.polygons])
slid = 0
for v in bm.verts:
    i = v.index
    if piece[i] == 0 and torso_any[i] and Z[i] > top[i]:
        w = np.array(MW @ v.co)
        w[2] = top[i]
        hit = full_bvh.find_nearest(Vector(w), 0.08)
        if hit[0] is not None:
            v.co = MW.inverted() @ hit[0]
            slid += 1
rep["corset_top_vertices_slid"] = slid
bmesh.ops.delete(bm, geom=kill, context="FACES")
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
bm.normal_update()
# Border smoothing: a piece made of whole faces ends in a staircase (render full6, 2026-11-14). Every border vertex is
# moved toward the mean of its border neighbours and put back on the body's surface, a few times for the corset (its
# top is a drawn curve), more for the rings round arms, wrists, fingers and thighs.
MWi = MW.inverted()
bnb = {}
for e in bm.edges:
    if len(e.link_faces) == 1:
        a_, b_ = e.verts
        bnb.setdefault(a_, []).append(b_)
        bnb.setdefault(b_, []).append(a_)
for it in range(int(os.environ.get("EDGE_SMOOTH", 14))):
    new = {}
    for v, nb in bnb.items():
        if pid[v] == 1 and it >= 3:
            continue
        m_ = sum((n_.co for n_ in nb), Vector()) / len(nb)
        hit = full_bvh.find_nearest(MW @ (v.co * 0.5 + m_ * 0.5), 0.05)
        if hit[0] is not None:
            new[v] = MWi @ hit[0]
    for v, co in new.items():
        v.co = co
bm.normal_update()
rep["border_vertices_smoothed"] = len(bnb)
for f in bm.faces:
    f.material_index = 4 if all(pid[v] == 3 for v in f.verts) else 0
inv3 = MW.to_3x3().inverted()
for v in bm.verts:
    v.co += (inv3 @ (MW.to_3x3() @ v.normal).normalized()) * (OFF * (1.6 if pid[v] in (2, 3) else 1.0))
bm.normal_update()
# neon ribbons along chosen borders: the corset's top edge and the boot tops. Two vertices per border vertex, the
# ribbon lies on the piece from its edge inward.
NEON_W, NEON_LIFT = float(os.environ.get("NEON_W", 0.004)), 0.0008
rib_v, rib_f, rib_src = [], [], []
rmap = {}
mid_corset = pel_z + 0.35 * (neck_z - pel_z)
for v in bnb:
    w = MW @ v.co
    if not ((pid[v] == 1 and w.z > mid_corset) or (pid[v] == 5 and w.z > J("calf_l")[2] + 0.05)):
        continue
    n_ = (MW.to_3x3() @ v.normal).normalized()
    inw = sum(((MW @ f.calc_center_median()) - w for f in v.link_faces), Vector())
    inw = inw - n_ * inw.dot(n_)
    if inw.length < 1e-6:
        continue
    inw.normalize()
    rmap[v] = len(rib_v)
    rib_v.append(tuple(w - inw * 0.0006 + n_ * NEON_LIFT))
    rib_v.append(tuple(w + inw * NEON_W + n_ * NEON_LIFT))
    rib_src += [tuple(w), tuple(w)]
for e in bm.edges:
    if len(e.link_faces) == 1 and e.verts[0] in rmap and e.verts[1] in rmap:
        a_, b_ = rmap[e.verts[0]], rmap[e.verts[1]]
        rib_f.append((a_, b_, b_ + 1, a_ + 1))
bm.to_mesh(cos.data)
bm.free()
shell_mi = [p_.material_index for p_ in cos.data.polygons]      # clearing the material slots resets the indices
cos.data.materials.clear()
mats = []
for p_ in cos.data.polygons:
    p_.use_smooth = True
for name, col, emit in (("yuki_latex", (0.012, 0.010, 0.014, 1), 0.0), ("yuki_neon", (1.0, 0.08, 0.55, 1), 6.0), ("yuki_gold", (0.83, 0.62, 0.18, 1), 0.0),
                        ("yuki_skin", (0.85, 0.66, 0.60, 1), 0.0), ("yuki_strap", (0.03, 0.028, 0.034, 1), 0.0)):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = col
    b.inputs["Roughness"].default_value = 0.25
    if emit:
        b.inputs["Emission Color"].default_value = col
        b.inputs["Emission Strength"].default_value = emit
    cos.data.materials.append(m)
    mats.append(m)
for p_, mi_ in zip(cos.data.polygons, shell_mi):
    p_.material_index = mi_


def add_part(name, verts, faces, mat_index, weights):
    """weights: list per vertex of {bone: weight}. The part is made in world space and joined into the costume."""
    m = bpy.data.meshes.new(name)
    m.from_pydata([tuple(MW.inverted() @ Vector(v)) for v in verts], [], faces)
    m.update()
    o = bpy.data.objects.new(name, m)
    bpy.context.scene.collection.objects.link(o)
    o.matrix_world = MW.copy()
    for mt in mats:
        m.materials.append(mt)
    for p in m.polygons:
        p.material_index = mat_index if isinstance(mat_index, int) else mat_index[p.index]
    for i, wd in enumerate(weights):
        for bone, w in wd.items():
            (o.vertex_groups.get(bone) or o.vertex_groups.new(name=bone)).add([i], float(w), "REPLACE")
    return o


from mathutils.kdtree import KDTree as _KD
_kd = _KD(len(W))
for i_, w_ in enumerate(W):
    _kd.insert(Vector(w_), i_)
_kd.balance()


def body_weights(p):
    i_ = _kd.find(Vector(p))[1]
    g = {gname[x.group]: x.weight for x in me.vertices[i_].groups if x.weight > 0.01}
    t_ = sum(g.values()) or 1.0
    return {k: w / t_ for k, w in g.items()}


neon_parts = []
if rib_f:
    neon_parts.append(add_part("neon_edges", rib_v, rib_f, 1, [body_weights(p) for p in rib_src]))


def surface_line(samples, name):
    """samples: (origin, direction) rays onto the body; a ribbon NEON_W wide is laid along the hits, lifted over the shell."""
    pts = []
    for o_, d_ in samples:
        hit = full_bvh.ray_cast(Vector(o_), Vector(d_).normalized(), 2.0)
        if hit[0] is not None:
            pts.append((np.array(hit[0]), np.array(hit[1])))
    if len(pts) < 3:
        return
    P_ = np.array([p for p, _ in pts])
    for _ in range(2):                                   # light smoothing of the path
        P_[1:-1] = 0.25 * P_[:-2] + 0.5 * P_[1:-1] + 0.25 * P_[2:]
    vs, fs, ws = [], [], []
    for i_, (p, (_, n_)) in enumerate(zip(P_, pts)):
        tan = P_[min(i_ + 1, len(P_) - 1)] - P_[max(i_ - 1, 0)]
        ac = np.cross(n_, tan)
        ac /= (np.linalg.norm(ac) + 1e-9)
        base = p + n_ * (OFF + NEON_LIFT)
        vs += [tuple(base - ac * NEON_W / 2), tuple(base + ac * NEON_W / 2)]
        ws += [body_weights(p)] * 2
    for i_ in range(len(P_) - 1):
        fs.append((2 * i_, 2 * i_ + 1, 2 * i_ + 3, 2 * i_ + 2))
    neon_parts.append(add_part(name, vs, fs, 1, ws))
    rep.setdefault("neon_lines", {})[name] = len(P_)


waist_z = pel_z + float(os.environ.get("SKIRT_TOP", 0.005))   # the skirt sits low on the hips, as in the concept
top0 = base_top - 0.022
front_o = lambda u_, z_: (c0 + side * u_ + fwd * 0.6 + up * (z_ - c0[2]), -fwd)
zs_c = np.arange(top0 - 0.004, waist_z, -0.007)
surface_line([front_o(0.0, z_) for z_ in zs_c], "neon_centre")
for sg in (1, -1):
    zs_s = np.arange(base_top + 0.02, waist_z, -0.007)
    surface_line([front_o(sg * (0.050 + 0.028 * (z_ - waist_z) / (base_top + 0.02 - waist_z)), z_) for z_ in zs_s if True], "neon_seam_" + ("l" if sg > 0 else "r"))
for s_ in ("l", "r"):
    sam = []
    for a_, b_, t0_, t1_ in (("thigh_" + s_, "calf_" + s_, BOOT_TOP + 0.04, 1.0), ("calf_" + s_, "foot_" + s_, 0.0, 0.9)):
        A_, B_ = J(a_), J(b_)
        for tt_ in np.arange(t0_, t1_, 0.012 / float(np.linalg.norm(B_ - A_))):
            q_ = A_ + (B_ - A_) * tt_
            sam.append((q_ + fwd * 0.5, -fwd))
    surface_line(sam, "neon_boot_" + s_)

# ---- skirt: a pleated ring with a tight waistband on the corset, following pelvis and thighs
PLEATS = int(os.environ.get("PLEATS", 28))
z_top = waist_z
LEN = float(os.environ.get("SKIRT_LEN", z_top - (pel_z - 0.175)))
TT = [0.0, 0.06, 0.16, 0.34, 0.52, 0.70, 0.86, 0.978, 1.0]
RINGS = len(TT)
hipv = W[(reg == "pelvis") | (reg == "spine") | (reg == "thigh_l") | (reg == "thigh_r")]
verts, faces, wts, fm = [], [], [], []
n_ang = PLEATS * 2
axis = np.array([c0[0], c0[1]])
for r in range(RINGS):
    tt = TT[r]
    z = z_top - LEN * tt
    band = hipv[np.abs(hipv[:, 2] - max(z, pel_z - 0.065)) < 0.02]
    for k in range(n_ang):
        ang = 2 * math.pi * k / n_ang
        dvec = math.cos(ang) * side + math.sin(ang) * fwd
        proj = (band - c0) @ dvec
        perp = np.abs((band - c0) @ np.cross(up, dvec))
        near = proj[(perp < 0.03) & (proj > 0)]
        r0 = float(near.max()) if len(near) else 0.16
        # ring 0 is the waistband, tight on the corset (the first skirt stood off like a lampshade with an open top)
        pl = min(1.0, tt / 0.16)
        rad = r0 + 0.005 + (0.045 + 0.018 * (1 if k % 2 == 0 else -1)) * tt ** 0.8 + pl * (0.006 if k % 2 == 0 else -0.004)
        p = c0 + dvec * rad
        verts.append((p[0], p[1], z))
        u_side = float(dvec @ side)
        wt = float(np.clip(tt * 0.85, 0, 0.75))
        thigh = "thigh_l" if u_side > 0 else "thigh_r"
        fade = float(np.clip(abs(u_side) / 0.35, 0, 1))
        wts.append({"pelvis": 1 - wt * fade, thigh: wt * fade} if wt * fade > 0.01 else {"pelvis": 1.0})
for r in range(RINGS - 1):
    for k in range(n_ang):
        a, b = r * n_ang + k, r * n_ang + (k + 1) % n_ang
        faces.append((a, b, b + n_ang, a + n_ang))
        fm.append(1 if r == RINGS - 2 else 0)                  # the hem glows
skirt = add_part("skirt", verts, faces, fm, wts)
for p_ in skirt.data.polygons:        # flat quads mirrored the lights like tiles (stills c1)
    p_.use_smooth = True
for e_ in skirt.data.edges:           # the folds are creases: smooth down a pleat, sharp across from one pleat to the next
    a_, b_ = e_.vertices
    if a_ % n_ang == b_ % n_ang:
        e_.use_edge_sharp = True

# ---- choker: a band round the neck, its section read from the head mesh (HEAD_FBX) at that height
# the chin is 21.5 cm under the crown: the first build put the choker at mouth height (0.45 of neck_01 to head)
chin_z = float(os.environ.get("CHIN_Z", 0)) or None
zc = neck_z + float(os.environ.get("CHOKER_DZ", -0.012))
ax = J("neck_01") + (J("head") - J("neck_01")) * ((zc - neck_z) / (head_z - neck_z))
before_h = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(Path(os.environ["HEAD_FBX"]).resolve()))
hobjs = [o for o in bpy.data.objects if o not in before_h]
hm = max((o for o in hobjs if o.type == "MESH"), key=lambda o: len(o.data.vertices))
bpy.context.view_layer.update()
Hw = np.array([hm.matrix_world @ v.co for v in hm.data.vertices])
rep["head_mesh_z"] = [round(float(Hw[:, 2].min()), 3), round(float(Hw[:, 2].max()), 3)]
bandh = Hw[np.abs(Hw[:, 2] - zc) < 0.012]
CH, NA = 0.009, 40
cv, cf, cw, cm_ = [], [], [], []
radii = []
for k in range(NA):
    ang = 2 * math.pi * k / NA
    dvec = math.cos(ang) * side + math.sin(ang) * fwd
    proj = (bandh - ax) @ dvec
    perp = np.abs((bandh - ax) @ np.cross(up, dvec))
    near = proj[(perp < 0.012) & (proj > 0)]
    radii.append(float(near.max()) if len(near) else np.nan)
radii = np.array(radii)
radii[np.isnan(radii)] = np.nanmedian(radii)
radii = np.minimum(radii, 1.3 * np.nanmedian(radii))          # no jaw or collar point in the ring
radii = (np.roll(radii, 1) + 2 * radii + np.roll(radii, -1)) / 4 + 0.0035
rep["choker"] = {"z": round(float(zc), 3), "radius_cm": [round(float(radii.min()) * 100, 1), round(float(radii.max()) * 100, 1)], "band_vertices": int(len(bandh))}
for k in range(NA):
    ang = 2 * math.pi * k / NA
    dvec = math.cos(ang) * side + math.sin(ang) * fwd
    for dz in (CH, CH - 0.0022, -CH + 0.0022, -CH):
        p_ = ax + dvec * (radii[k] + (0.0 if abs(dz) == CH else 0.0025))
        cv.append((p_[0], p_[1], zc + dz))
        cw.append({"neck_01": 0.5, "neck_02": 0.5})
for k in range(NA):
    for r_ in range(3):
        a, b = k * 4 + r_, ((k + 1) % NA) * 4 + r_
        cf.append((a, b, b + 1, a + 1))
        cm_.append(1 if r_ != 1 else 4)                      # thin neon rims, strap middle
choker = add_part("choker", cv, cf, cm_, cw)
for o in hobjs:
    bpy.data.objects.remove(o)
# ---- bell: a small sphere on the front of the choker
kf = int(np.argmax([math.sin(2 * math.pi * k / NA) for k in range(NA)]))
front = ax + fwd * radii[kf] + up * (zc - ax[2])
cb = front + fwd * 0.010 - up * 0.016
bv, bf = [], []
SEG, RNG, RB = 12, 8, 0.011
for i in range(RNG + 1):
    th = math.pi * i / RNG
    for j in range(SEG):
        ph = 2 * math.pi * j / SEG
        bv.append(tuple(cb + RB * np.array([math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th)])))
for i in range(RNG):
    for j in range(SEG):
        a, b = i * SEG + j, i * SEG + (j + 1) % SEG
        bf.append((a, b, b + SEG, a + SEG))
bell = add_part("bell", bv, bf, 2, [{"neck_01": 1.0}] * len(bv))
for p_ in bell.data.polygons:
    p_.use_smooth = True
# ---- the skin the built body lacks: faces of the complete body with no built face at their place
from mathutils.bvhtree import BVHTree
bt = BVHTree.FromPolygons([bm_.matrix_world @ v.co for v in bm_.data.vertices], [tuple(q.vertices) for q in bm_.data.polygons])
skinp = body.copy()
skinp.data = me.copy()
skinp.name = "yuki_skin_patch"
bpy.context.scene.collection.objects.link(skinp)
sb = bmesh.new()
sb.from_mesh(skinp.data)
covered = {f for f in sb.faces if (lambda h: h[0] is not None and h[3] < 0.0015)(bt.find_nearest(MW @ f.calc_center_median(), 0.01))}
# The patch reaches two rings of faces under the built body, a little below its surface: where the two only met edge
# to edge, a dark hairline showed on the shoulder (stills c3, 2026-11-14).
unc = {f for f in sb.faces if f not in covered}
keep_p = set(unc)
for _ in range(int(os.environ.get("PATCH_OVERLAP", 2))):
    keep_p |= {f for v in {v for f in keep_p for v in f.verts} for f in v.link_faces}
unc_v = {v for f in unc for v in f.verts}
sb.normal_update()
for v in {v for f in keep_p for v in f.verts} - unc_v:
    v.co -= (inv3 @ (MW.to_3x3() @ v.normal).normalized()) * 0.0007
rep["skin_patch_faces"], rep["skin_patch_overlap_faces"] = len(unc), len(keep_p) - len(unc)
bmesh.ops.delete(sb, geom=[f for f in sb.faces if f not in keep_p], context="FACES")
bmesh.ops.delete(sb, geom=[v for v in sb.verts if not v.link_faces], context="VERTS")
sb.to_mesh(skinp.data)
sb.free()
skinp.data.materials.clear()
for mt in mats:
    skinp.data.materials.append(mt)
for p_ in skinp.data.polygons:
    p_.material_index = 3
    p_.use_smooth = True
for o in bobjs:
    bpy.data.objects.remove(o)
bpy.ops.object.select_all(action="DESELECT")
for o in [skirt, bell, choker, skinp, cos] + neon_parts:
    o.select_set(True)
bpy.context.view_layer.objects.active = cos
bpy.ops.object.join()
# two-sided skirt needs no flipped copy: the Unreal materials are two sided
rep["costume_vertices"], rep["costume_faces"] = len(cos.data.vertices), len(cos.data.polygons)
rep["neon_faces"] = int(sum(1 for p in cos.data.polygons if p.material_index == 1))

# ---- check renders: costume over the body
scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "MATERIAL"
scene.render.resolution_x, scene.render.resolution_y = 700, 1100
skin = bpy.data.materials.new("skin")
skin.diffuse_color = (0.85, 0.66, 0.60, 1)
body.data.materials.clear()
body.data.materials.append(skin)
for mt, col in zip(mats, ((0.02, 0.02, 0.03, 1), (1.0, 0.1, 0.6, 1), (0.85, 0.65, 0.2, 1), (0.85, 0.66, 0.60, 1), (0.12, 0.11, 0.14, 1))):
    mt.diffuse_color = col
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
cam.data.type = "ORTHO"
cam.data.ortho_scale = float(Z.max() - Z.min()) * 1.08
scene.collection.objects.link(cam)
scene.camera = cam
mid = np.array([c0[0], c0[1], (Z.max() + Z.min()) / 2])
for name, yaw in (("front", 0), ("side", 90), ("back", 180)):
    a = math.radians(yaw)
    dirv = math.cos(a) * fwd + math.sin(a) * side
    cam.location = Vector(mid + dirv * 4)
    cam.rotation_euler = (Vector(-dirv)).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(out / f"check_{name}.png")
    bpy.ops.render.render(write_still=True)

bpy.ops.object.select_all(action="DESELECT")
body.hide_set(True)
arm.select_set(True)
cos.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.fbx(filepath=str(out / "yuki_costume.fbx"), use_selection=True, object_types={"ARMATURE", "MESH"}, add_leaf_bones=False, bake_anim=False,
                         mesh_smooth_type="EDGE", path_mode="COPY", embed_textures=False)
(out / "costume_report.json").write_text(json.dumps(rep, indent=1))
print("COSTUME", json.dumps(rep), flush=True)

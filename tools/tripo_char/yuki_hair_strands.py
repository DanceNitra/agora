"""Grow fine hair strands inside HairDeck's hair cards, for a groom (Alembic) instead of flat cards.

    ./blender_headless.sh yuki_hair_strands.py -- <hair_seedN.glb> <out_dir>

Each HairDeck card is a tube of rings: 4 vertices per ring, one ring per UV v value (measured on seed 8: u in {0, 0.5,
1}, 4 vertices per v). Per ring the card has a centre, a width axis (the two farthest vertices) and a thickness axis.
A strand keeps one (s, q) position across width and thickness from root to tip, with a little drift and frizz, so
strands follow the card's flow and fill its volume. Strands per card follow the card's area; tips end at random
85-100 % of the card length. The cards are lengthened below the chin the same way as yuki_hair_fix.py (LENGTH).
Writes yuki_hair_strands.abc and Cycles renders (front, side, back) with the head proxy.
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
LENGTH = float(os.environ.get("LENGTH", 1.85))
TOTAL = int(os.environ.get("STRANDS", 40000))
NPTS = int(os.environ.get("POINTS", 64))   # 32 points on a strand over a metre long showed as straight kinks in Unreal
# Volume and locks (2026-11-13, v4 in Unreal read as flat sheets): a card is a thin ribbon, so strands also spread along
# its normal by THICK card widths; and each card splits into a few clumps whose strands close in on the clump's own
# line towards the tip, which gives the pointed lock ends of the concept.
THICK = float(os.environ.get("THICK", 0.35))
CLUMPS = float(os.environ.get("CLUMPS", 3))        # clumps per card of median width
CLUMP = float(os.environ.get("CLUMP", 0.65))       # how far a strand closes in on its clump at the tip (0..1)
EAR_DENSITY = float(os.environ.get("EAR_DENSITY", 3.0))
DRIFT = float(os.environ.get("DRIFT", 0.08))       # 0.08 read as fluffy in Unreal; the concept's locks are smooth
RGB = tuple(float(x) for x in os.environ.get("HAIR_RGB", "0.88,0.63,0.76").split(","))
# Loosening (owner 2026-11-13, "rozvolni"): strands spread past their card's edges, a wave runs along the length below
# the chin, and extra strands are interpolated between neighbouring strands of different cards to fill the gaps.
SPREAD = float(os.environ.get("SPREAD", 1.6))      # half-width range in card widths (1 = inside the card)
FILL = float(os.environ.get("FILL", 0.6))          # extra interpolated strands, as a fraction of the grown ones
WAVE_AMP = float(os.environ.get("WAVE_AMP", 0.08))  # in head heights
WAVE_LEN = float(os.environ.get("WAVE_LEN", 0.9))   # in head heights
rng = np.random.default_rng(13)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(Path(src).resolve()))
cards = bpy.data.objects["hair_cards"]
head = bpy.data.objects["head_proxy"]
for o in (cards, head):
    o.data.transform(o.matrix_world)
    o.parent = None
    o.matrix_world = Matrix.Identity(4)
HP = np.array([v.co[:] for v in head.data.vertices])
chin_z, crown_z = float(HP[:, 2].min()), float(HP[:, 2].max())
hc = HP.mean(0)
h = crown_z - chin_z

bm = bmesh.new()
bm.from_mesh(cards.data)
bm.verts.ensure_lookup_table()
uvl = bm.loops.layers.uv.active
uv = np.zeros((len(bm.verts), 2))
for f in bm.faces:
    for lp in f.loops:
        uv[lp.vert.index] = lp[uvl].uv
P = np.array([v.co[:] for v in bm.verts])
# lengthen below the chin (same stretch as yuki_hair_fix.py)
d = chin_z - P[:, 2]
nd = np.where(d < h, d + (LENGTH - 1.0) * d * d / (2 * h), h * (1 + (LENGTH - 1.0) / 2) + (d - h) * LENGTH)
P[:, 2] = np.where(d > 0, chin_z - nd, P[:, 2])
lab = -np.ones(len(bm.verts), int)
k = 0
for v in bm.verts:
    if lab[v.index] >= 0:
        continue
    st = [v]
    lab[v.index] = k
    while st:
        x = st.pop()
        for e in x.link_edges:
            y = e.other_vert(x)
            if lab[y.index] < 0:
                lab[y.index] = k
                st.append(y)
    k += 1
bm.free()

# per card: rings ordered root to tip
cardrings = []
for c in range(k):
    idx = np.nonzero(lab == c)[0]
    vs = np.round(uv[idx, 1], 5)
    rows = []
    for vv in np.unique(vs):
        r = P[idx[vs == vv]]
        if len(r) < 2:
            continue
        cen = r.mean(0)
        D = np.linalg.norm(r[:, None] - r[None], axis=2)
        i, j = np.unravel_index(np.argmax(D), D.shape)
        wax = (r[i] - r[j]) / 2
        rest = [q for q in range(len(r)) if q not in (i, j)]
        tax = (r[rest[0]] - cen) if rest else np.cross(wax, [0, 0, 1]) * 0.1
        rows.append((cen, wax, tax))
    if len(rows) < 3:
        continue
    cen = np.array([r[0] for r in rows])
    if np.linalg.norm(cen[-1] - hc) < np.linalg.norm(cen[0] - hc):
        rows = rows[::-1]
    # keep width axes pointing the same way along the card
    for q in range(1, len(rows)):
        if np.dot(rows[q][1], rows[q - 1][1]) < 0:
            rows[q] = (rows[q][0], -rows[q][1], rows[q][2])
    cen = np.array([r[0] for r in rows])
    length = float(np.linalg.norm(np.diff(cen, axis=0), axis=1).sum())
    width = float(np.mean([np.linalg.norm(r[1]) for r in rows])) * 2
    cardrings.append((rows, length, width))
# Ear cards never come down the skull: every ring sits near or above the crown and the top is well above it.
is_ear = np.array([min(r[0][2] for r in rows) > crown_z - 0.14 * h and max(r[0][2] for r in rows) > crown_z + 0.03 * h for rows, _, _ in cardrings])
area = np.array([l * w for _, l, w in cardrings]) * np.where(is_ear, EAR_DENSITY, 1.0)
counts = np.maximum(6, np.round(TOTAL * area / area.sum())).astype(int)
med_w = float(np.median([w for _, _, w in cardrings]))
print("CARDS", len(cardrings), "ear cards", int(is_ear.sum()), "median width", round(med_w, 4), flush=True)


def along(arr, n):
    """Resample a per-ring array to n points by arc length of the ring centres."""
    t = np.linspace(0, 1, len(arr))
    tt = np.linspace(0, 1, n)
    return np.stack([np.interp(tt, t, arr[:, c]) for c in range(arr.shape[1])], 1)


strands, owner = [], []
for ci, ((rows, length, width), n) in enumerate(zip(cardrings, counts)):
    cen = np.array([r[0] for r in rows])
    wax = np.array([r[1] for r in rows])
    tax = np.array([r[2] for r in rows])
    C, W, T = along(cen, NPTS), along(wax, NPTS), along(tax, NPTS)
    tt = np.linspace(0, 1, NPTS)[:, None]
    Wn = W / np.maximum(np.linalg.norm(W, axis=1, keepdims=True), 1e-9)
    Tn = np.cross(np.gradient(C, axis=0), Wn)
    Tn /= np.maximum(np.linalg.norm(Tn, axis=1, keepdims=True), 1e-9)
    arc = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(C, axis=0), axis=1))])
    below = np.clip((chin_z - C[:, 2]) / h, 0, 1)[:, None]  # no wave on the crown, the fringe or the ears
    phase = rng.uniform(0, 2 * np.pi)
    ear = bool(is_ear[ci])
    Wlen = np.linalg.norm(W, axis=1, keepdims=True)
    Tv = Tn * Wlen * (0.18 if ear else THICK)          # thickness direction scaled by the card's own width
    ncl = 1 if ear else max(1, int(round(CLUMPS * width / med_w)))
    cs, cq = rng.uniform(-SPREAD * 0.8, SPREAD * 0.8, ncl), rng.uniform(-0.6, 0.6, ncl)
    pull = (0.0 if ear else CLUMP) * tt ** 1.3
    for _ in range(n):
        kc = int(rng.integers(ncl))
        s = float(np.clip(cs[kc] + rng.normal(0, SPREAD / (1.2 * ncl)), -SPREAD, SPREAD)) if ncl > 1 else rng.uniform(-SPREAD, SPREAD)
        q = float(np.clip(cq[kc] + rng.normal(0, 0.45), -1, 1)) if ncl > 1 else rng.uniform(-0.9, 0.9)
        drift = rng.normal(0, DRIFT, 2) * tt         # strands wander a little across the card toward the tip
        frizz = rng.normal(0, 0.0004, (NPTS, 3)) * tt  # fine noise, none at the root
        ph = phase + rng.normal(0, 0.35)
        amp = WAVE_AMP * h * rng.uniform(0.7, 1.3)
        wave = amp * below * (np.sin(2 * np.pi * arc / (WAVE_LEN * h) + ph)[:, None] * Wn
                              + 0.5 * np.cos(2 * np.pi * arc / (WAVE_LEN * h) + ph)[:, None] * Tn)
        st, qt = s + (cs[kc] - s) * pull, q + (cq[kc] - q) * pull
        pts = C + (st + drift[:, 0:1]) * W + (qt + drift[:, 1:2]) * Tv + frizz + wave
        end = rng.uniform(0.85, 1.0)
        m = max(4, int(round(NPTS * end)))
        seg = pts[:m]
        strands.append(np.vstack([seg, np.repeat(seg[-1:], NPTS - m, 0)]) if m < NPTS else seg)
        owner.append(ci)
S = np.array(strands, dtype=np.float32)
owner = np.array(owner)
# The ears need a body under the fur: strands alone read as a wire cage. Each ear's cards are wrapped in a convex hull,
# shrunk a little and smoothed; it is exported beside the groom and stands in Unreal as a static mesh.
ear_pts = [np.concatenate([np.array([r[0] + sg * r[1] for r in rows for sg in (-1, 1)]) for (rows, _, _), e in zip(cardrings, is_ear) if e and (np.mean([r[0][0] for r in rows]) > hc[0]) == right])
           for right in (False, True)] if is_ear.any() else []
ear_objs = []
for pts_e in ear_pts:
    bme = bmesh.new()
    for q_ in pts_e:
        bme.verts.new(q_)
    hull = bmesh.ops.convex_hull(bme, input=bme.verts)
    bmesh.ops.delete(bme, geom=[v for v in bme.verts if not v.link_faces], context="VERTS")
    cen_e = pts_e.mean(0)
    for v in bme.verts:
        v.co = Vector(cen_e) + (v.co - Vector(cen_e)) * 0.86
    bmesh.ops.subdivide_edges(bme, edges=bme.edges[:], cuts=2, use_grid_fill=True)
    for _ in range(6):
        bmesh.ops.smooth_vert(bme, verts=bme.verts[:], factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bmesh.ops.recalc_face_normals(bme, faces=bme.faces[:])
    me_e = bpy.data.meshes.new("yuki_ear")
    bme.to_mesh(me_e)
    bme.free()
    oe = bpy.data.objects.new("yuki_ear", me_e)
    bpy.context.scene.collection.objects.link(oe)
    ear_objs.append(oe)
print("EARS solids", len(ear_objs), [len(o.data.vertices) for o in ear_objs], flush=True)
# fill: blend each new strand from a random strand and a strand of a neighbouring card. Strands of one card share their
# root area, so the nearest roots are almost always the same card (v3 filled 1,370 of 24,000): neighbours are found
# among the cards' mean roots instead.
from mathutils import kdtree
ncard = int(owner.max()) + 1
croot = np.array([S[owner == c, 0].mean(0) if (owner == c).any() else np.full(3, 1e3) for c in range(ncard)])
kd = kdtree.KDTree(ncard)
for c_, r in enumerate(croot):
    kd.insert(Vector(r), c_)
kd.balance()
members = [np.nonzero(owner == c_)[0] for c_ in range(ncard)]
extra = []
for _ in range(int(FILL * len(S))):
    i = int(rng.integers(len(S)))
    near = [c_ for _, c_, _ in kd.find_n(Vector(croot[owner[i]]), 5) if c_ != owner[i] and len(members[c_])]
    if not near:
        continue
    cj = near[int(rng.integers(len(near)))]
    j = int(members[cj][int(rng.integers(len(members[cj])))])
    w = rng.uniform(0.2, 0.8)
    extra.append((1 - w) * S[i] + w * S[j] + rng.normal(0, 0.0005, (NPTS, 3)) * np.linspace(0, 1, NPTS)[:, None])
filled = len(extra)
if extra:
    S = np.concatenate([S, np.array(extra, dtype=np.float32)])
rep = {"cards": len(cardrings), "strands": int(len(S)), "filled": filled, "spread": SPREAD, "wave_amp": WAVE_AMP, "points_per_strand": NPTS,
       "length_heads": round(float((crown_z - S[:, :, 2].min()) / h), 2)}
print("STRANDS", json.dumps(rep), flush=True)

# Fit onto a MetaHuman head (MH_HEAD = head FBX exported from Unreal; in Blender it faces -Y like the hair, metres).
# HairDeck's head proxy is an egg 0.104 wide and 0.128 deep; the hair is scaled by the mean of the width and depth
# ratios of the skull above the ears, and the crowns and skull centres are put together.
unit = 1.0
if os.environ.get("MH_HEAD"):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(Path(os.environ["MH_HEAD"]).resolve()))
    new_objs = [o for o in bpy.data.objects if o not in before]
    mh = max((o for o in new_objs if o.type == "MESH"), key=lambda o: len(o.data.vertices))
    bpy.context.view_layer.update()
    M = np.array([mh.matrix_world @ v.co for v in mh.data.vertices])
    mcrown = float(M[:, 2].max())
    band = M[M[:, 2] > mcrown - 0.11]
    mw, md_ = float(np.ptp(band[:, 0])), float(np.ptp(band[:, 1]))
    mc = np.array([(band[:, 0].max() + band[:, 0].min()) / 2, (band[:, 1].max() + band[:, 1].min()) / 2])
    pw, pd = float(np.ptp(HP[:, 0])), float(np.ptp(HP[:, 1]))
    unit = float(os.environ.get("HAIR_FIT", 1.04)) * (mw / pw + md_ / pd) / 2
    pc_ = np.array([(HP[:, 0].max() + HP[:, 0].min()) / 2, (HP[:, 1].max() + HP[:, 1].min()) / 2, crown_z])
    S = ((S - pc_) * unit + np.array([mc[0], mc[1], mcrown + 0.004])).astype(np.float32)
    for oe in ear_objs:
        oe.data.transform(Matrix.Translation(Vector((mc[0], mc[1], mcrown + 0.004))) @ Matrix.Scale(unit, 4) @ Matrix.Translation(-Vector(pc_)))
    # Fringe: in Unreal it hung over the eyes to the mouth (reports/yuki_ue_hair). The concept's fringe ends at the
    # brows. Strands in front of the face (|x| < 5 cm, front half of the skull) are cut where they pass below the brow
    # line, each at its own height within FRINGE_VAR. Brows sit about 9.2 cm under the crown on a 21.5 cm head.
    brow_z = mcrown - float(os.environ.get("BROW_BELOW_CROWN", 0.092))
    chin_mh = mcrown - 0.215
    # How low hair may hang in front of the face, by distance from the middle (x, metres; -x is the picture's left).
    # Read off the concept: a tip between the brows, both eyes free, one lock over the outer corner of the picture-left
    # eye, and from the outer eye corners outward the locks that frame the face run down freely. A flat cut at the brow
    # line (v11) read as a bowl fringe.
    def low_of(dx):
        a_ = np.abs(dx)
        low = np.full(dx.shape, brow_z + 0.004)
        low = np.where(a_ < 0.012, brow_z - 0.012, low)
        low = np.where((dx > -0.060) & (dx < -0.040), brow_z - 0.040, low)
        side = brow_z - np.clip((a_ - 0.046) / 0.016, 0, 1) * 0.25
        return np.where(a_ >= 0.046, np.minimum(low, side), low)

    FV = float(os.environ.get("FRINGE_VAR", 0.012))
    cut = low_of(S[:, :, 0] - mc[0]) - rng.uniform(0, FV, len(S))[:, None]
    infront = (np.abs(S[:, :, 0] - mc[0]) < 0.062) & (S[:, :, 1] < mc[1] - 0.02) & (S[:, :, 2] < cut) & (S[:, :, 2] > chin_mh - 0.03)
    first = np.where(infront.any(1), infront.argmax(1), NPTS)
    trimmed = 0
    for i in np.nonzero(first < NPTS)[0]:
        k_ = max(int(first[i]), 2)
        S[i, k_:] = S[i, k_ - 1]
        trimmed += 1
    # The fringe is thin: HairDeck gives it few cards (2,369 of 120,000 strands on seed 8) and the forehead shows through.
    # Each fringe strand gets FRINGE_COPIES neighbours, moved sideways and a little in depth, each with its own length.
    FC = int(os.environ.get("FRINGE_COPIES", 5))
    fidx = np.nonzero(first < NPTS)[0]
    if FC and len(fidx):
        add = []
        for i in fidx:
            for _ in range(FC):
                off = np.array([rng.normal(0, 0.006), rng.normal(0, 0.002), 0.0])
                c_ = S[i] + off
                kk = max(3, int(first[i]) - int(rng.integers(0, 4)))
                c_[kk:] = c_[kk - 1]
                add.append(c_)
        S = np.concatenate([S, np.array(add, dtype=np.float32)])
        rep["fringe_copies"] = len(add)
        print("FRINGE copies", len(add), flush=True)
    # Strands inside the head are pushed 3 mm above the skin.
    from mathutils.bvhtree import BVHTree
    hb_ = BVHTree.FromPolygons([Vector(q) for q in M], [tuple(pl.vertices) for pl in mh.data.polygons])
    flat = S.reshape(-1, 3)
    pushed = 0
    for i in np.nonzero(flat[:, 2] > chin_mh - 0.08)[0]:
        loc, nrm, _, dist = hb_.find_nearest(Vector(flat[i]), 0.04)
        if loc is not None and (Vector(flat[i]) - loc).dot(nrm) < 0.003:
            flat[i] = loc + nrm * 0.003
            pushed += 1
    S = flat.reshape(S.shape)
    # Last pass over everything, copies included: the push-out sends a point that sat deep inside the head to the nearest
    # surface, and the head mesh has surfaces inside (eye sockets, mouth), so strands came to lie across the eyes and the
    # nose bridge (seen in Unreal, reports/yuki_ue_v11). Whatever is in front of the face below the brows is cut there.
    cut2 = low_of(S[:, :, 0] - mc[0]) - rng.uniform(0, FV, len(S))[:, None]
    bad = (np.abs(S[:, :, 0] - mc[0]) < 0.062) & (S[:, :, 1] < mc[1] - 0.015) & (S[:, :, 2] < cut2) & (S[:, :, 2] > chin_mh - 0.03)
    f2 = np.where(bad.any(1), bad.argmax(1), NPTS)
    cut_n = 0
    for i in np.nonzero(f2 < NPTS)[0]:
        k_ = int(f2[i])
        S[i, k_:] = S[i, max(k_ - 1, 0)]
        cut_n += 1
    seg_len = np.linalg.norm(np.diff(S, axis=1), axis=2).sum(1)
    keep_s = seg_len > 0.012                        # a stub shorter than 12 mm is dropped
    S = S[keep_s]
    print("FACE CLEAN cut", cut_n, "dropped stubs", int((~keep_s).sum()), flush=True)
    # Fringe locks. The cut strands in front of the face are gathered into locks about LOCK_W wide: each strand moves
    # towards its lock's middle more and more towards its tip, and strands at the edge of a lock end sooner, so every
    # lock closes to a point like the concept's.
    LOCK_W = float(os.environ.get("LOCK_W", 0.012))
    seg_ = np.linalg.norm(np.diff(S, axis=1), axis=2)
    npts = (seg_ > 1e-7).sum(1) + 1
    end = S[np.arange(len(S)), npts - 1]
    fr = (np.abs(end[:, 0] - mc[0]) < 0.066) & (end[:, 1] < mc[1] - 0.015) & (end[:, 2] > chin_mh - 0.03) & (end[:, 2] < brow_z + 0.03) & (npts < NPTS)
    centres = np.arange(-0.072, 0.0721, LOCK_W) + rng.uniform(-0.3, 0.3, len(np.arange(-0.072, 0.0721, LOCK_W))) * LOCK_W + mc[0]
    styled = 0
    for i in np.nonzero(fr)[0]:
        n_ = int(npts[i])
        if n_ < 4:
            continue
        xc = centres[np.argmin(np.abs(centres - end[i, 0]))]
        d_ = float(np.clip((end[i, 0] - xc) / (LOCK_W / 2), -1, 1))
        n2 = max(3, n_ - int(round(abs(d_) * 0.4 * max(n_ - 2, 0))))     # edge strands end sooner
        tt_ = np.linspace(0, 1, n2)
        wt = np.clip((tt_ - 0.3) / 0.7, 0, 1) ** 1.3
        S[i, :n2, 0] -= (S[i, n2 - 1, 0] - xc) * 0.85 * wt
        S[i, n2:] = S[i, n2 - 1]
        styled += 1
    print("FRINGE locks", len(centres), "strands styled", styled, flush=True)
    rep["fringe"] = {"brow_z_m": round(brow_z, 4), "strands_trimmed": trimmed, "points_pushed_out": pushed, "face_clean_cut": cut_n, "stubs_dropped": int((~keep_s).sum())}
    print("FRINGE", json.dumps(rep["fringe"]), flush=True)
    rep["fit"] = {"mh_skull_w_d_cm": [round(mw * 100, 1), round(md_ * 100, 1)], "proxy_w_d": [round(pw, 4), round(pd, 4)],
                  "scale": round(unit, 4), "mh_crown_m": round(mcrown, 4), "hair_low_m": round(float(S[:, :, 2].min()), 3)}
    print("FIT", json.dumps(rep["fit"]), flush=True)
    bpy.data.objects.remove(head)
    head = mh
    for o in new_objs:
        if o.type == "MESH" and o is not mh:
            o.hide_render = True

# Shortened strands (random tip length, fringe cut) were padded by repeating their last point. Unreal's groom builder
# then reports "Computed number of knots would exceed the number available from the groom". Each strand is resampled
# to NPTS points evenly along the length it really has, so no two points coincide.
resampled = 0
tgrid = np.linspace(0, 1, NPTS)
for i in range(len(S)):
    seg = np.linalg.norm(np.diff(S[i], axis=0), axis=1)
    if (seg < 1e-7).any():
        keep_n = int(np.nonzero(seg >= 1e-7)[0].max()) + 2 if (seg >= 1e-7).any() else 2
        pts = S[i, :keep_n].astype(np.float64)
        arc = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))])
        if arc[-1] < 1e-6:
            continue
        S[i] = np.stack([np.interp(tgrid * arc[-1], arc, pts[:, c]) for c in range(3)], 1)
        resampled += 1
# A strand with no length at all (cut at its root by the fringe rule) cannot be resampled: it is dropped.
seg_all = np.linalg.norm(np.diff(S, axis=1), axis=2)
good = ~(seg_all < 1e-7).any(1)
rep["dropped_degenerate_strands"] = int((~good).sum())
S = S[good]
seg_all = np.linalg.norm(np.diff(S, axis=1), axis=2)
rep["resampled_strands"] = resampled
rep["zero_length_segments_left"] = int((seg_all < 1e-7).sum())
print("RESAMPLE", resampled, "zero segments left", rep["zero_length_segments_left"], flush=True)

hc_ = bpy.data.hair_curves.new("yuki_hair")
hc_.add_curves([NPTS] * len(S))
hc_.position_data.foreach_set("vector", S.reshape(-1))
rad = hc_.attributes.get("radius") or hc_.attributes.new("radius", "FLOAT", "POINT")
r0 = float(os.environ.get("RADIUS", 0.00018)) * (0.6 if unit != 1.0 else 1.0) * unit
taper = np.linspace(1.0, 0.25, NPTS)
rad.data.foreach_set("value", np.tile(r0 * taper, len(S)).astype(np.float32))
ho = bpy.data.objects.new("yuki_hair", hc_)
bpy.context.scene.collection.objects.link(ho)
bpy.data.objects.remove(cards)

mat = bpy.data.materials.new("hair")
mat.use_nodes = True
nt = mat.node_tree
for nd_ in list(nt.nodes):
    if nd_.type != "OUTPUT_MATERIAL":
        nt.nodes.remove(nd_)
hb = nt.nodes.new("ShaderNodeBsdfHairPrincipled")
hb.parametrization = "COLOR"
hb.inputs["Color"].default_value = (*[c ** 2.2 for c in RGB], 1)
hb.inputs["Roughness"].default_value = 0.35
nt.links.new(hb.outputs[0], next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL").inputs["Surface"])
hc_.materials.append(mat)

bpy.ops.object.select_all(action="DESELECT")
ho.select_set(True)
bpy.context.view_layer.objects.active = ho
try:
    bpy.ops.wm.alembic_export(filepath=str(out / "yuki_hair_strands.abc"), selected=True, start=1, end=1, export_hair=True)
    rep["alembic_bytes"] = (out / "yuki_hair_strands.abc").stat().st_size
except Exception as e:  # noqa: BLE001
    rep["alembic_error"] = str(e)[:200]
# A second Alembic in Unreal's axes and centimetres, for a groom import with identity conversion. Blender writes
# (X, Z, -Y) of the object's (X, Y, Z); Unreal wants (x, -y, z) * 100 of Blender's metres, so the object holds
# (x, -z, -y) * 100.
if unit != 1.0:
    U = np.stack([S[:, :, 0], -S[:, :, 2], -S[:, :, 1]], 2) * 100.0
    hu = bpy.data.hair_curves.new("yuki_hair_ue")
    hu.add_curves([NPTS] * len(U))
    hu.position_data.foreach_set("vector", U.astype(np.float32).reshape(-1))
    ru = hu.attributes.get("radius") or hu.attributes.new("radius", "FLOAT", "POINT")
    ru.data.foreach_set("value", np.tile(r0 * 100 * taper, len(U)).astype(np.float32))
    ou = bpy.data.objects.new("yuki_hair_ue", hu)
    bpy.context.scene.collection.objects.link(ou)
    bpy.ops.object.select_all(action="DESELECT")
    ou.select_set(True)
    bpy.context.view_layer.objects.active = ou
    bpy.ops.wm.alembic_export(filepath=str(out / "yuki_hair_ue.abc"), selected=True, start=1, end=1, export_hair=True)
    rep["ue_abc_bytes"] = (out / "yuki_hair_ue.abc").stat().st_size
    rep["ue_bounds_cm"] = [[round(float(x), 1) for x in (S[:, :, 0].min() * 100, -S[:, :, 1].max() * 100, S[:, :, 2].min() * 100)],
                           [round(float(x), 1) for x in (S[:, :, 0].max() * 100, -S[:, :, 1].min() * 100, S[:, :, 2].max() * 100)]]
    bpy.data.objects.remove(ou)
if ear_objs:
    em = bpy.data.materials.new("ear")
    em.use_nodes = True
    next(n for n in em.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"].default_value = (*[c ** 2.2 for c in RGB], 1)
    bpy.ops.object.select_all(action="DESELECT")
    for oe in ear_objs:
        oe.data.materials.append(em)
        for pl in oe.data.polygons:
            pl.use_smooth = True
        oe.select_set(True)
    bpy.context.view_layer.objects.active = ear_objs[0]
    bpy.ops.object.join()
    ears = bpy.context.view_layer.objects.active
    ears.name = ears.data.name = "yuki_ears"
    bpy.ops.export_scene.fbx(filepath=str(out / "yuki_ears.fbx"), use_selection=True, object_types={"MESH"}, apply_scale_options="FBX_SCALE_UNITS",
                             mesh_smooth_type="FACE", add_leaf_bones=False)
    E = np.array([v.co[:] for v in ears.data.vertices])
    rep["ears"] = {"vertices": len(E), "lo_m": E.min(0).round(4).tolist(), "hi_m": E.max(0).round(4).tolist()}
(out / "strands.json").write_text(json.dumps(rep, indent=1))
print("ABC", json.dumps(rep), flush=True)

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
scene.cycles.samples = int(os.environ.get("SAMPLES", 64))
scene.render.resolution_x = scene.render.resolution_y = 800
scene.view_settings.view_transform = "Standard"
world = bpy.data.worlds.new("w")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.25, 0.25, 0.25, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.6
scene.world = world
for name, rot, e in (("key", (50, 0, -30), 4.0), ("rim", (60, 0, 160), 3.0)):
    L = bpy.data.objects.new(name, bpy.data.lights.new(name, "SUN"))
    L.data.energy = e
    L.rotation_euler = [math.radians(a) for a in rot]
    scene.collection.objects.link(L)
lo, hi = S.reshape(-1, 3).min(0), S.reshape(-1, 3).max(0)
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

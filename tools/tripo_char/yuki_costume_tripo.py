"""Yuki's costume cut from her dressed Tripo model and fitted on her MetaHuman body (route M, docs/TRIPO_UE_WORKFLOW 5.5).

    ./blender_headless.sh yuki_costume_tripo.py -- <dressed.glb> <mh_fullbody.fbx> <out_dir>

STAGE=classify stops after the cut and writes check renders of what is kept: the pieces of the dressed mesh that are
costume by texture colour (black latex, magenta neon, grey metal) plus the tail. Skin (peach: blue under green) and
hair (pink: blue over green, light) are removed, and everything above the choker. The dressed model stands facing -Y
with its soles on z = 0, at its own size (1.75 m with heels and ears)."""
import json
import math
import os
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

glb_p, mh_p = (str(Path(a).resolve()) for a in sys.argv[-3:-1])
out = Path(sys.argv[-1]).resolve()
out.mkdir(parents=True, exist_ok=True)
STAGE = os.environ.get("STAGE", "all")
rep = {}
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb_p)
dr = max((o for o in bpy.data.objects if o.type == "MESH"), key=lambda o: len(o.data.vertices))
for o in list(bpy.data.objects):
    if o is not dr:
        bpy.data.objects.remove(o)
dr.data.transform(dr.matrix_world)
dr.matrix_world = Matrix.Identity(4)
me = dr.data
# Tripo splits the vertices on every UV seam: without welding, each UV chart is an island of its own and the scrap
# filter below throws small charts of the costume away (first run 2026-11-14: 2,841 islands, 35,000 faces lost).
_bm = bmesh.new()
_bm.from_mesh(me)
bmesh.ops.remove_doubles(_bm, verts=_bm.verts, dist=1e-6)
_bm.to_mesh(me)
_bm.free()


def co(m):
    a = np.zeros(len(m.vertices) * 3)
    m.vertices.foreach_get("co", a)
    return a.reshape(-1, 3)


P = co(me)
if np.ptp(P[:, 0]) < np.ptp(P[:, 1]):                       # arms along Y: turn them onto X (the model faces +X)
    me.transform(Matrix.Rotation(-math.pi / 2, 4, "Z"))
    P = co(me)
me.transform(Matrix.Translation((0, 0, -P[:, 2].min())))
P = co(me)
_ft = P[P[:, 2] < 0.04]                                       # centre on the soles: the tail hangs to one side
me.transform(Matrix.Translation((-(_ft[:, 0].max() + _ft[:, 0].min()) / 2, 0, 0)))
P = co(me)
legs = P[(P[:, 2] > 0.3) & (P[:, 2] < 0.5)]
feet = P[P[:, 2] < 0.05]
if feet[:, 1].mean() > legs[:, 1].mean():                  # toes point to +Y: turn round
    me.transform(Matrix.Rotation(math.pi, 4, "Z"))
    P = co(me)
me.transform(Matrix.Translation((0, -float(legs[:, 1].mean()) * (1 if feet[:, 1].mean() <= legs[:, 1].mean() else -1), 0)))
P = co(me)
H = float(P[:, 2].max())
rep["dressed"] = {"height": round(H, 3), "vertices": len(P), "faces": len(me.polygons)}

# ---- colour of every face from the base colour texture
mat = me.materials[0]
mat.use_backface_culling = False
img = next(i for i in bpy.data.images if i.size[0] and i.name.lower().startswith("base"))
w, h = img.size
px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[:, :, :3]
px = np.where(px <= 0.0031308, px * 12.92, 1.055 * np.power(np.maximum(px, 1e-9), 1 / 2.4) - 0.055)
nl = len(me.loops)
uv = np.zeros(nl * 2)
me.uv_layers.active.data.foreach_get("uv", uv)
uv = uv.reshape(-1, 2)
ls = np.zeros(len(me.polygons), dtype=np.int64)
lt = np.zeros(len(me.polygons), dtype=np.int64)
me.polygons.foreach_get("loop_start", ls)
me.polygons.foreach_get("loop_total", lt)
assert (lt == 3).all(), "triangles expected"
fuv = uv[ls[:, None] + np.arange(3)[None, :]].mean(1)
FCOL = px[np.clip((fuv[:, 1] % 1.0 * h).astype(int), 0, h - 1), np.clip((fuv[:, 0] % 1.0 * w).astype(int), 0, w - 1)]
lv = np.zeros(nl, dtype=np.int64)
me.loops.foreach_get("vertex_index", lv)
FV = lv[ls[:, None] + np.arange(3)[None, :]]
FC = P[FV].mean(1)
r, g, b = FCOL[:, 0], FCOL[:, 1], FCOL[:, 2]
lum = FCOL.mean(1)
sat = FCOL.max(1) - FCOL.min(1)
dark = lum < float(os.environ.get("DARK", 0.33))
neon = (r - g > 0.22) & (b - g > 0.05) & (sat > 0.3)          # magenta lines
# The bright cores of the neon lines are pink-white in the base colour and were cut away as hair: rows of holes on the
# boots (seen 2026-11-14). The emissive texture says where neon is, whatever the base colour.
_em = next((i for i in bpy.data.images if i.size[0] and i.name.lower().startswith("neon")), None)
if _em is not None:
    ew, eh = _em.size
    epx = np.array(_em.pixels[:], dtype=np.float32).reshape(eh, ew, 4)[:, :, :3]
    FEM = epx[np.clip((fuv[:, 1] % 1.0 * eh).astype(int), 0, eh - 1), np.clip((fuv[:, 0] % 1.0 * ew).astype(int), 0, ew - 1)].max(1)
    neon |= FEM > float(os.environ.get("EMIT_MIN", 0.12))
    rep["emissive_faces"] = int((FEM > float(os.environ.get("EMIT_MIN", 0.12))).sum())
skin = ~dark & ~neon & (g - b > 0.015) & (r > 0.5) & (r - b > float(os.environ.get("SKIN_WARM", 0.07)))    # warm: light grey metal is not skin
# light pink: hair, ears, tail. A light neutral grey is metal (the boots' top bands, the knee guards' straps), not hair:
# without the tint test those were cut away and skin showed in their place (seen 2026-11-14).
hair = ~dark & ~neon & ~skin & (lum > 0.45) & ((r - g > float(os.environ.get("HAIR_TINT", 0.035))) | (sat > 0.10))
grey = ~dark & ~neon & ~skin & ~hair                          # metal plates, buckles, blended texels
rep["colour_faces"] = {k: int(v.sum()) for k, v in (("dark", dark), ("neon", neon), ("skin", skin), ("hair", hair), ("grey", grey))}
# a texel of plain black latex, for the underlayer and the choker: the corset's front, the dark face of median brightness
_cf = np.nonzero(dark & (np.abs(FC[:, 0]) < 0.10) & (FC[:, 2] > 0.60 * H) & (FC[:, 2] < 0.72 * H) & (FC[:, 1] < 0))[0]
STOCK_UV = tuple(float(x) for x in fuv[_cf[np.argsort(lum[_cf])[len(_cf) // 2]]])
_nf = np.nonzero(neon)[0]
NEON_UV = tuple(float(x) for x in fuv[_nf[np.argmax((r - g)[_nf])]])
# the choker: dark faces round the neck. Nothing of the costume is above it.
ax = np.abs(FC[:, 0])
neck = dark & (ax < 0.07) & (np.abs(FC[:, 1]) < 0.10) & (FC[:, 2] > 0.74 * H) & (FC[:, 2] < 0.86 * H)
zs = FC[neck, 2]
hist, edges = np.histogram(zs, bins=40)
zc = float(edges[int(hist.argmax())])
ch = zs[np.abs(zs - zc) < 0.03]
choker_top, choker_bot = float(ch.max()), float(ch.min())
rep["choker_z"] = [round(choker_bot, 3), round(choker_top, 3)]
# the tail: hair-coloured faces below the waist and behind the body, grown over what they touch
waist_z = 0.56 * H
tail_seed = hair & (FC[:, 2] < waist_z - 0.03) & (FC[:, 1] > 0.06)
# The choker comes out of the cut in scraps (hair lies on it). Everything from 2 cm under it upward is dropped; a clean
# ring is built on the neck later.
cost = (dark | neon | grey) & (FC[:, 2] < choker_bot - float(os.environ.get("NECK_CUT", 0.0)))
# Inside the boots everything is boot. Highlights on the grey top bands and knee straps read as skin or hair by
# colour and left speckled holes (seen 2026-11-14). Below the boots' own top, in the two leg columns, every face is kept.
_leg = cost & dark & (FC[:, 2] < 0.50 * H) & (np.abs(FC[:, 1]) < 0.20) & (np.abs(FC[:, 0]) > 0.02) & (np.abs(FC[:, 0]) < 0.30)
if _leg.sum() > 1000:
    # the boots' top: dark faces end 1 to 1.5 cm under the grey band's upper edge (99.8 % of all kept faces went 4 cm
    # too high and took a ring of thigh skin with it)
    _zt = float(np.percentile(FC[_leg, 2], 99.7)) + float(os.environ.get("BOOT_BAND", 0.012))
    _ax = np.abs(FC[_leg, 0])
    _force = (FC[:, 2] < _zt - 0.004) & (FC[:, 1] < float(np.percentile(FC[_leg, 1], 99.9)) + 0.008) & (FC[:, 1] > float(np.percentile(FC[_leg, 1], 0.1)) - 0.008)         & (np.abs(FC[:, 0]) > float(np.percentile(_ax, 0.1)) - 0.005) & (np.abs(FC[:, 0]) < float(np.percentile(_ax, 99.9)) + 0.005) & ~tail_seed
    rep["boot_zone"] = {"top_z": round(_zt, 3), "faces_restored": int((_force & ~cost).sum())}
    cost |= _force
# Hair and cat ears come from the Tripo model as well (owner's direction of 2026-11-14: the Tripo model is the look;
# the strand groom was flat, striped over the eye and its ears were fuzzy lumps, seen in the full-song render). They
# are a sculpted, painted mesh. Kept: everything above the hairline (hair, ears, also the ears' skin-coloured inside);
# on the head below it, what is not skin, except the face's own features (eyes, lashes, brows, lips, nostrils: inside
# the face box only pink faces are hair) and the choker; below the choker, the hair-coloured faces lying on chest and back.
EY = json.load(open(os.environ.get("EYES_JSON", str(Path(__file__).parent / "models/yuki/dressed_head_probe/eyes.json"))))
PRB = json.load(open(str(Path(os.environ.get("EYES_JSON", str(Path(__file__).parent / "models/yuki/dressed_head_probe/eyes.json"))).parent / "probe.json")))
xe_d, ze_d = EY["mid"]
_dk = min(PRB["front_depth_y"], key=lambda k_: (float(k_.split(",")[0]) - xe_d) ** 2 + (float(k_.split(",")[1]) - (ze_d - 0.03)) ** 2)
ye_d = PRB["front_depth_y"][_dk]                              # depth of the face's front (cheek under the eyes)
HAIR_MODE = os.environ.get("TRIPO_HAIR", "1")                # "1": hair and ears, "ears": the cat ears only (our strand groom is the hair), "0": none
HAIR_ON = HAIR_MODE != "0"
pink = (b - g > 0.02) & (r > 0.3) & ~neon
head_zone = FC[:, 2] >= choker_bot
top_zone = FC[:, 2] > ze_d + 0.065
face_box = (np.abs(FC[:, 0] - xe_d) < 0.078) & (FC[:, 2] > EY["chin_z"] - 0.004) & (FC[:, 2] < ze_d + 0.05) & (FC[:, 1] < ye_d + 0.09)
neck_box = (FC[:, 2] < choker_top + 0.006) & (np.abs(FC[:, 0] - xe_d) < 0.085) & (np.abs(FC[:, 1] - (ye_d + 0.07)) < 0.10)
# Colour alone cannot tell the peach fringe from skin (first cut: the fringe ended in a straight line), and a depth
# map of the Tripo skin did not either (the fringe itself read as skin and became the surface). So in front of the
# face everything light is kept here, the Tripo face's own skin included, and after the alignment whatever lies ON
# the MetaHuman's head is removed: what is left stands off the face and is hair.
# on the chest above the bust (skin there lies in the hair's pink shadow) only clearly light faces are hair
_chest = ~head_zone & (FC[:, 2] > 0.66 * H) & (FC[:, 1] < ye_d + 0.10)
by_colour = (~head_zone & hair & ~tail_seed & (~_chest | (lum > 0.55))) | (head_zone & ~skin & np.where(neck_box, pink, True))
face_zone = head_zone & ~top_zone & (np.abs(FC[:, 0] - xe_d) < 0.095) & (FC[:, 1] < ye_d + 0.10) & (FC[:, 2] > EY["chin_z"] - 0.005)
hair_keep = (head_zone & top_zone) | (~face_zone & by_colour) | (face_zone & (lum > 0.35) & ~neon)
rep["hair_face_zone_faces"] = int((face_zone & hair_keep).sum())
if HAIR_MODE == "ears":                                       # the ears stand above the sides of the crown
    hair_keep &= (lum > 0.42) & head_zone & (FC[:, 2] > ze_d + float(os.environ.get("EAR_Z", 0.078))) & (np.abs(FC[:, 0] - xe_d) > float(os.environ.get("EAR_X", 0.055)))
if not HAIR_ON:
    hair_keep[:] = False
rep["hair_faces_kept"] = int(hair_keep.sum())
DFULL = P.copy()
tail_v = np.zeros(len(P), bool)
tail_v[FV[tail_seed].ravel()] = True
keep = cost | tail_seed | hair_keep
rep["keep_faces_before_islands"] = int(keep.sum())
bm = bmesh.new()
bm.from_mesh(me)
bm.faces.ensure_lookup_table()
# Hair lies on the corset and shares vertices with it. It is taken out into its own object here, before anything is
# deleted, and joined back after the costume has been split into its pieces. (Cutting it loose inside one mesh failed
# twice: split edges left the two joined at single vertices, and a face split fused boots, gloves and corset.)
_hk = hair_keep & ~cost & keep
hr = None
if _hk.any():
    bmh = bm.copy()
    bmh.faces.ensure_lookup_table()
    bmesh.ops.delete(bmh, geom=[bmh.faces[i] for i in np.nonzero(~_hk)[0]], context="FACES")
    bmesh.ops.delete(bmh, geom=[v for v in bmh.verts if not v.link_faces], context="VERTS")
    hme = bpy.data.meshes.new("yuki_hair_tripo")
    bmh.to_mesh(hme)
    bmh.free()
    hr = bpy.data.objects.new("yuki_hair_tripo", hme)
    bpy.context.scene.collection.objects.link(hr)
    if not hme.materials:
        hme.materials.append(mat)
    keep = keep & ~_hk
    GROOM_HULL = os.environ.get("GROOM_HULL", "")
    if HAIR_MODE == "ears" and GROOM_HULL:
        _hidx0 = np.nonzero(_hk)[0]
        _pk = _hidx0[hair[_hidx0]] if hair[_hidx0].any() else _hidx0
        ear_uv = tuple(float(x) for x in fuv[_pk[np.argsort(lum[_pk])[int(len(_pk) * 0.6)]]])
    elif HAIR_MODE == "ears":
        # Only the ears themselves. The height-and-side test also kept the Tripo hair lying behind and below each ear
        # (20 cm deep where an ear is 6 to 7 cm), open, jagged sheets that showed as dark ribbons from behind in the
        # editor (owner, 2026-11-14: "toto co tam robi zo zadu? ked bude tancovat tak amen"). Kept per side: faces
        # within a cone under the ear tip (EAR_R0 + EAR_SLOPE * depth below the tip, in the horizontal plane) and
        # less than EAR_H below it. Then the ear gets a back: EAR_T thick, the new shell coloured with the ears' own
        # pink (one texel), so the ear is a solid from every side.
        hidx = np.nonzero(_hk)[0]
        hfc = FC[hidx]
        R0, SL, EH = (float(os.environ.get("EAR_R0", 0.024)), float(os.environ.get("EAR_SLOPE", 0.45)),
                      float(os.environ.get("EAR_H", 0.058)))
        ear_ok = np.zeros(len(hidx), bool)
        for side in (hfc[:, 0] > xe_d, hfc[:, 0] <= xe_d):
            if not side.any():
                continue
            tip = hfc[side][np.argmax(hfc[side][:, 2])]
            dz = tip[2] - hfc[:, 2]
            rh = np.linalg.norm(hfc[:, :2] - tip[:2], axis=1)
            ear_ok |= side & (dz < EH) & (rh < R0 + SL * np.maximum(dz, 0))
        bme = bmesh.new()
        bme.from_mesh(hme)
        bme.faces.ensure_lookup_table()
        bmesh.ops.delete(bme, geom=[bme.faces[i] for i in np.nonzero(~ear_ok)[0]], context="FACES")
        bmesh.ops.delete(bme, geom=[v for v in bme.verts if not v.link_faces], context="VERTS")
        # drop small loose bits left at the cone's edge
        bme.faces.ensure_lookup_table()
        comp = {}
        cid = 0
        for f0 in bme.faces:
            if f0.index in comp:
                continue
            stack = [f0]
            comp[f0.index] = cid
            while stack:
                ff = stack.pop()
                for e in ff.edges:
                    for g in e.link_faces:
                        if g.index not in comp:
                            comp[g.index] = cid
                            stack.append(g)
            cid += 1
        sizes = np.bincount(np.array([comp[f.index] for f in bme.faces]), minlength=cid)
        small = [f for f in bme.faces if sizes[comp[f.index]] < 0.05 * sizes.max()]
        bmesh.ops.delete(bme, geom=small, context="FACES")
        bmesh.ops.delete(bme, geom=[v for v in bme.verts if not v.link_faces], context="VERTS")
        bme.to_mesh(hme)
        bme.free()
        hme.update()
        # pink texel: the median-bright hair-coloured face among the kept ear faces
        hk_ear = hidx[ear_ok]
        pinkish = hk_ear[hair[hk_ear]] if hair[hk_ear].any() else hk_ear
        ear_uv = tuple(float(x) for x in fuv[pinkish[np.argsort(lum[pinkish])[int(len(pinkish) * 0.6)]]])
        for pl in hme.polygons:
            pl.material_index = 0
        mod = hr.modifiers.new("ear_back", "SOLIDIFY")
        mod.thickness = float(os.environ.get("EAR_T", 0.0025))
        mod.offset = 1.0
        mod.use_rim = True
        mod.material_offset = 1
        mod.material_offset_rim = 1
        if len(hme.materials) < 2:
            hme.materials.append(hme.materials[0])
        bpy.context.view_layer.objects.active = hr
        for o_ in bpy.context.selected_objects:
            o_.select_set(False)
        hr.select_set(True)
        bpy.ops.object.modifier_apply(modifier=mod.name)
        uvl_ = hme.uv_layers.active.data
        n_back = 0
        for pl in hme.polygons:
            if pl.material_index == 1:
                for li in pl.loop_indices:
                    uvl_[li].uv = ear_uv
                pl.material_index = 0
                n_back += 1
        hme.materials.pop(index=1)
        rep["ear_faces_kept"] = int(ear_ok.sum())
        rep["ear_back_faces"] = n_back
rep["hair_faces_taken_out"] = int(_hk.sum())
bmesh.ops.delete(bm, geom=[bm.faces[i] for i in np.nonzero(~keep)[0]], context="FACES")
bm.faces.ensure_lookup_table()
seen, small, sizes = set(), [], []
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
    sizes.append(len(comp))
    if len(comp) < int(os.environ.get("MIN_ISLAND", 400)):
        small += comp
rep["islands"] = {"count": len(sizes), "largest": sorted(sizes, reverse=True)[:12], "scrap_faces": len(small)}
bmesh.ops.delete(bm, geom=small, context="FACES")
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
bm.to_mesh(me)
bm.free()
me.update()
# 890,000 triangles are far more than a skinned garment needs; the texture carries the detail
TARGET = int(os.environ.get("TARGET_FACES", 420000 + (240000 if HAIR_ON else 0)))       # 160,000 flattened the boots' plates and guards (owner 2026-11-14)
if len(me.polygons) > TARGET:
    bpy.context.view_layer.objects.active = dr
    md = dr.modifiers.new("dec", "DECIMATE")
    md.ratio = TARGET / len(me.polygons)
    bpy.ops.object.modifier_apply(modifier="dec")
    me = dr.data
rep["kept"] = {"vertices": len(me.vertices), "faces": len(me.polygons)}
print("CUT", json.dumps(rep), flush=True)

scene = bpy.context.scene
# check renders show the base colour as it is: an emission material (the workbench drew this material black)
chk = bpy.data.materials.new("check")
chk.use_nodes = True
chk.use_backface_culling = False
_nt = chk.node_tree
for _n in list(_nt.nodes):
    if _n.type != "OUTPUT_MATERIAL":
        _nt.nodes.remove(_n)
_t = _nt.nodes.new("ShaderNodeTexImage")
_t.image = img
_e = _nt.nodes.new("ShaderNodeEmission")
_nt.links.new(_t.outputs["Color"], _e.inputs["Color"])
_nt.links.new(_e.outputs[0], next(n for n in _nt.nodes if n.type == "OUTPUT_MATERIAL").inputs["Surface"])
me.materials.append(chk)
for p_ in me.polygons:
    p_.material_index = 1
try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError:
    scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x, scene.render.resolution_y = 800, 1400
scene.view_settings.view_transform = "Standard"
world = bpy.data.worlds.new("w")
world.color = (0.35, 0.55, 0.35)
scene.world = world
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
cam.data.type = "ORTHO"
cam.data.ortho_scale = H * 1.04
scene.collection.objects.link(cam)
scene.camera = cam


def shots(tag):
    for name, yaw in (("front", 0), ("side", 90), ("back", 180), ("q", -40)):
        a = math.radians(yaw)
        cam.location = (4 * math.sin(a), -4 * math.cos(a), H / 2)
        cam.rotation_euler = (math.pi / 2, 0, a)
        scene.render.filepath = str(out / f"{tag}_{name}.png")
        bpy.ops.render.render(write_still=True)


shots("cut")


def components(mesh):
    n = len(mesh.vertices)
    Ed = np.array([e.vertices[:] for e in mesh.edges])
    adj = [[] for _ in range(n)]
    for a_, b_ in Ed:
        adj[a_].append(b_)
        adj[b_].append(a_)
    lab = -np.ones(n, dtype=np.int64)
    k = 0
    for i in range(n):
        if lab[i] >= 0:
            continue
        st = [i]
        lab[i] = k
        while st:
            q = st.pop()
            for j in adj[q]:
                if lab[j] < 0:
                    lab[j] = k
                    st.append(j)
        k += 1
    return lab, k, Ed


LAB, NLAB, E = components(me)
CPd = co(me)
comp_tab = []
for k in range(NLAB):
    m_ = LAB == k
    if m_.sum() < 120:
        continue
    q = CPd[m_]
    comp_tab.append({"id": k, "verts": int(m_.sum()), "c": [round(float(x), 3) for x in q.mean(0)], "lo": [round(float(x), 3) for x in q.min(0)], "hi": [round(float(x), 3) for x in q.max(0)]})
comp_tab.sort(key=lambda d_: -d_["verts"])
rep["components"] = comp_tab
for d_ in comp_tab:
    print("COMP", json.dumps(d_), flush=True)
if STAGE == "islands":
    sys.exit()
# roles: boots reach the floor, the tail is light, the largest other piece is corset and skirt (with the upper-arm
# straps), and on each side the lower small piece is the glove, the upper the cuff. Pieces under 900 vertices are scraps.
_nl = len(me.loops)
_uv = np.zeros(_nl * 2)
me.uv_layers.active.data.foreach_get("uv", _uv)
_uv = _uv.reshape(-1, 2)
_lv = np.zeros(_nl, dtype=np.int64)
me.loops.foreach_get("vertex_index", _lv)
_vuv = np.zeros((len(CPd), 2))
_vuv[_lv] = _uv
_vc = px[np.clip((_vuv[:, 1] % 1.0 * h).astype(int), 0, h - 1), np.clip((_vuv[:, 0] % 1.0 * w).astype(int), 0, w - 1)]
_light = _vc.mean(1) > 0.45
ROLE = {}
big = [d_ for d_ in comp_tab if d_["verts"] >= 900]
for d_ in big:
    k = d_["id"]
    _ls = float(_light[LAB == k].mean())
    print("PIECE", k, d_["verts"], d_["c"], "top", d_["hi"][2], "light share", round(_ls, 2), flush=True)
    if _ls > 0.5:
        ROLE[k] = "tail"
    elif d_["lo"][2] < 0.05 and d_["hi"][2] > 0.45:
        ROLE[k] = "boot_l" if d_["c"][0] > 0 else "boot_r"
# several light pieces may be hair (loose locks); only one role name is kept per piece id
rest_ = [d_ for d_ in big if d_["id"] not in ROLE]
ROLE[rest_[0]["id"]] = "torso"
for sfx, side in (("l", 1), ("r", -1)):
    arm_c = sorted([d_ for d_ in rest_[1:] if d_["c"][0] * side > 0.15], key=lambda d_: d_["c"][2])
    if len(arm_c) >= 2:
        ROLE[arm_c[0]["id"]], ROLE[arm_c[1]["id"]] = "glove_" + sfx, "cuff_" + sfx
rep["roles"] = {str(k): v for k, v in ROLE.items()}
print("ROLES", rep["roles"], flush=True)
assert all(r_ in ROLE.values() for r_ in ("torso", "boot_l", "boot_r", "tail", "glove_l", "glove_r", "cuff_l", "cuff_r")), "a piece is missing: %s" % sorted(set(ROLE.values()))
_bm = bmesh.new()
_bm.from_mesh(me)
_bm.verts.ensure_lookup_table()
bmesh.ops.delete(_bm, geom=[_bm.verts[i] for i in np.nonzero(~np.isin(LAB, list(ROLE)))[0]], context="VERTS")
_bm.to_mesh(me)
_bm.free()
me.update()
LAB, NLAB, E = components(me)
CPd = co(me)
ROLE2 = {}
for k in range(NLAB):
    c_ = CPd[LAB == k].mean(0)
    ROLE2[k] = min(ROLE.items(), key=lambda kv: np.linalg.norm(np.array(next(d_["c"] for d_ in comp_tab if d_["id"] == kv[0])) - c_))[1]
VROLE = np.array([ROLE2[k] for k in LAB])
# Corset and skirt are made symmetric from one half (owner 2026-11-14: the bust must be symmetric). Hair lay on the
# figure's left cup in the Tripo model, so its right half (x < 0, MIRROR_KEEP=-1) is kept and mirrored. The cut runs
# on the plane through the middle of the soles.
MK = float(os.environ.get("MIRROR_KEEP", -1))
if MK:
    _bm = bmesh.new()
    _bm.from_mesh(me)
    _bm.verts.ensure_lookup_table()
    tv_ = [_bm.verts[i] for i in np.nonzero(VROLE == "torso")[0]]
    tset = set(tv_)
    geom = tv_ + [e for e in _bm.edges if e.verts[0] in tset and e.verts[1] in tset] + [f for f in _bm.faces if all(v in tset for v in f.verts)]
    res = bmesh.ops.bisect_plane(_bm, geom=geom, dist=1e-5, plane_co=(0, 0, 0), plane_no=(-MK, 0, 0), clear_outer=True, clear_inner=False)
    half = [g_ for g_ in res["geom"] if isinstance(g_, (bmesh.types.BMVert, bmesh.types.BMEdge, bmesh.types.BMFace)) and g_.is_valid]
    dup = bmesh.ops.duplicate(_bm, geom=half)
    dv = [g_ for g_ in dup["geom"] if isinstance(g_, bmesh.types.BMVert)]
    for v in dv:
        v.co.x = -v.co.x
    bmesh.ops.reverse_faces(_bm, faces=[g_ for g_ in dup["geom"] if isinstance(g_, bmesh.types.BMFace)])
    seam = [v for v in _bm.verts if abs(v.co.x) < 0.0008 and (v in dv or v.is_valid)]
    bmesh.ops.remove_doubles(_bm, verts=seam, dist=0.0012)
    _bm.to_mesh(me)
    _bm.free()
    me.update()
    LAB, NLAB, E = components(me)
    CPd = co(me)
    ROLE2 = {}
    for k in range(NLAB):
        c_ = CPd[LAB == k].mean(0)
        c_[0] = c_[0] if abs(c_[0]) > 0.12 else next(d_["c"][0] for d_ in comp_tab if ROLE.get(d_["id"]) == "torso")   # the mirrored torso's centre moved onto x = 0
        ROLE2[k] = min(ROLE.items(), key=lambda kv: np.linalg.norm(np.array(next(d_["c"] for d_ in comp_tab if d_["id"] == kv[0])) - c_))[1]
    VROLE = np.array([ROLE2[k] for k in LAB])
    rep["mirrored_torso_vertices"] = int((VROLE == "torso").sum())
rep["role_vertices"] = {r_: int((VROLE == r_).sum()) for r_ in sorted(set(VROLE))}
for p_ in me.polygons:
    p_.material_index = 0
me.materials.pop(index=1)
# the hair comes back: decimated on its own, only the pieces that reach the head (flakes elsewhere are dropped)
if hr is not None:
    HT = int(os.environ.get("HAIR_FACES", 240000))
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = hr
    hr.select_set(True)
    if len(hr.data.polygons) > HT:
        md = hr.modifiers.new("dec", "DECIMATE")
        md.ratio = HT / len(hr.data.polygons)
        bpy.ops.object.modifier_apply(modifier="dec")
    labh, nh_, _eh = components(hr.data)
    Ph = co(hr.data)
    cnt_ = np.bincount(labh, minlength=nh_)
    topz = np.array([Ph[labh == k, 2].max() if cnt_[k] else -1 for k in range(nh_)])
    good = (topz > EY["chin_z"]) & (cnt_ > 300)
    _bm = bmesh.new()
    _bm.from_mesh(hr.data)
    _bm.verts.ensure_lookup_table()
    bmesh.ops.delete(_bm, geom=[_bm.verts[i] for i in np.nonzero(~good[labh])[0]], context="VERTS")
    _bm.to_mesh(hr.data)
    _bm.free()
    for p_ in hr.data.polygons:
        p_.material_index = 0
    rep["hair"] = {"pieces": int(nh_), "pieces_kept": int(good.sum()), "vertices": len(hr.data.vertices), "faces": len(hr.data.polygons)}
    print("HAIR", json.dumps(rep["hair"]), flush=True)
(out / "cut_report.json").write_text(json.dumps(rep, indent=1))
if STAGE == "classify":
    sys.exit()

# ================================================================================================================
# 2. the dressed mesh into the MetaHuman's frame, the MetaHuman's limbs onto the dressed mesh
from mathutils.bvhtree import BVHTree

before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=mh_p)
new = [o for o in bpy.data.objects if o not in before]
arm = next(o for o in new if o.type == "ARMATURE")
body = max((o for o in new if o.type == "MESH"), key=lambda o: len(o.data.vertices))
bpy.context.view_layer.update()
A = arm.matrix_world.copy()
Ai = A.inverted()


def joint(n):
    bpy.context.view_layer.update()
    return np.array(A @ arm.pose.bones[n].head)


def body_pts():
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    e = body.evaluated_get(dg)
    m = e.to_mesh()
    Pb = np.array([e.matrix_world @ v.co for v in m.vertices])
    e.to_mesh_clear()
    return Pb


# Bust (owner 2026-11-14: fuller, symmetric, pushed up). The built MetaHuman body has no torso; its skin there comes
# from this mesh's skin patch, so the shape is ours to set. Two mirrored domes are added to the body's chest: forward
# by BUST_AMP, the centre BUST_LIFT higher and BUST_IN nearer the middle than the body's own apex, fuller above the
# centre than below (the push-up line). Underlayer, skin patch and the corset's fit all follow the changed body.
BUST_AMP = float(os.environ.get("BUST_AMP", 0.026))
if BUST_AMP:
    _MW = body.matrix_world.copy()
    _MWi = _MW.inverted()
    Wb = np.array([_MW @ v.co for v in body.data.vertices])
    _gn = [g_.name for g_ in body.vertex_groups]
    tw = np.zeros(len(Wb))
    for v in body.data.vertices:
        tw[v.index] = sum(g_.weight for g_ in v.groups if ("spine" in _gn[g_.group] or "clavicle" in _gn[g_.group]))
    xc_ = float(joint("pelvis")[0])
    ua_z = float(joint("upperarm_l")[2])
    band_ = (tw > 0.8) & (Wb[:, 2] > ua_z - 0.24) & (Wb[:, 2] < ua_z - 0.06) & (np.abs(Wb[:, 0] - xc_) > 0.06) & (np.abs(Wb[:, 0] - xc_) < 0.11)      # from 3.5 cm the search found the breastbone (x = 4.8 cm) and the two domes merged
    ia_ = np.nonzero(band_)[0][np.argmin(Wb[band_, 1])]
    apex = Wb[ia_]
    yc_ = float(np.median(Wb[(tw > 0.8) & (np.abs(Wb[:, 2] - apex[2]) < 0.03), 1]))
    LIFT, INW, RX, RZ = float(os.environ.get("BUST_LIFT", 0.014)), float(os.environ.get("BUST_IN", 0.010)), float(os.environ.get("BUST_RX", 0.062)), float(os.environ.get("BUST_RZ", 0.058))
    cx_, cz_ = float(os.environ.get("BUST_CX", 0)) or (abs(float(apex[0] - xc_)) - INW), float(apex[2]) + LIFT
    ax_ = np.abs(Wb[:, 0] - xc_)
    du = (ax_ - cx_) / RX
    dzv = (Wb[:, 2] - cz_) / np.where(Wb[:, 2] > cz_, RZ * 1.4, RZ)
    wgt = np.exp(-(du ** 2 + dzv ** 2)) * np.clip((yc_ - Wb[:, 1]) / 0.05, 0, 1) * np.clip(tw, 0, 1)
    Wb[:, 1] -= BUST_AMP * wgt
    Wb[:, 2] += 0.35 * LIFT * wgt
    Wb[:, 0] -= np.sign(Wb[:, 0] - xc_) * 0.5 * INW * wgt
    for v in body.data.vertices:
        v.co = _MWi @ Vector(Wb[v.index])
    body.data.update()
    rep["bust"] = {"apex_before": [round(float(x), 3) for x in apex], "centre_x_z": [round(cx_, 3), round(cz_, 3)], "amp_m": BUST_AMP, "vertices_moved_over_2mm": int((BUST_AMP * wgt > 0.002).sum())}
    print("BUST", json.dumps(rep["bust"]), flush=True)
B0 = body_pts()
joint_rest = {n: joint(n) for n in ("upperarm_l", "upperarm_r", "pelvis", "neck_01", "head", "spine_03")}
sole_mh = float(B0[:, 2].min())
midb = B0[(np.abs(B0[:, 0] - joint("pelvis")[0]) < 0.012) & (B0[:, 2] > sole_mh + 0.3) & (B0[:, 2] < joint("pelvis")[2])]
crotch_mh = float(midb[:, 2].min())
x0_mh = float(joint("pelvis")[0])
y0_mh = float(B0[(B0[:, 2] > sole_mh + 0.3) & (B0[:, 2] < sole_mh + 0.5), 1].mean())
# dressed landmarks, on the whole dressed mesh without the tail
Dn = DFULL[~tail_v]
# crotch of the dressed figure: the lowest skin on the midline (all points gave the skirt's hem instead)
_sk = FC[skin]
midd = _sk[(np.abs(_sk[:, 0]) < 0.015) & (_sk[:, 2] > 0.38 * H) & (_sk[:, 2] < 0.60 * H)]
crotch_dr = float(np.percentile(midd[:, 2], 2))
print("CROTCH skin midline faces", len(midd), "z p2 p50", round(crotch_dr, 3), round(float(np.median(midd[:, 2])), 3), flush=True)


def arm_line(Pts, side, x_lo, x_hi):
    C = []
    for a in np.arange(x_lo, x_hi, 0.015):
        q = Pts[(Pts[:, 0] * side >= a) & (Pts[:, 0] * side < a + 0.015)]
        if len(q) > 20:
            C.append([side * (a + 0.0075), (q[:, 1].max() + q[:, 1].min()) / 2, (q[:, 2].max() + q[:, 2].min()) / 2])
    C = np.array(C)
    c = C.mean(0)
    d = np.linalg.svd(C - c)[2][0]
    return C, c, d * np.sign(d[0] * side)


# ---- alignment and proportions (design of 2026-11-14, after the owner's "how is it right on the Tripo model?")
# The costume is NOT bent onto the MetaHuman any more. The head is the anchor: the dressed model is scaled so that its
# eyes are as far apart as the MetaHuman's (yuki_dressed_head_probe, eyes.json) and stood with its eyes at the
# MetaHuman's eye height. With the heads equal, the Tripo figure's hips are higher, its legs longer and its arms a
# little shorter than the preset body's. The skeleton takes those proportions as a pose P made only of bone
# translations and aims (no scale): the pelvis rises until the crotch is HEM_OVER above the skirt's front hem and the
# spine's joints close up by the same amount, so neck and head stay where they are; thigh, calf and arm segments
# take the lengths read from the costume's own pieces (knee guard, ankle, wrist). The same translations are played in
# Unreal as a constant layer, and there the costume has exactly the Tripo model's shape.
SK = FC[skin]
sh_x = abs(float(joint("upperarm_l")[0] - x0_mh))
sh_top_mh = float(B0[(np.abs(np.abs(B0[:, 0] - x0_mh) - sh_x) < 0.1 * sh_x), 2].max())
EY = json.load(open(os.environ.get("EYES_JSON", str(Path(__file__).parent / "models/yuki/dressed_head_probe/eyes.json"))))
S_ = float(os.environ.get("COSTUME_SCALE", EY["scale"]))
T_ = Matrix.Translation((x0_mh, y0_mh, EY["mh_eye_mid"][2] - S_ * EY["mid"][1])) @ Matrix.Scale(S_, 4)
me.transform(T_)
Tn = np.array(T_)
Dn = Dn @ Tn[:3, :3].T + Tn[:3, 3]
SKm = SK @ Tn[:3, :3].T + Tn[:3, 3]
_band = SKm[(np.abs(np.abs(SKm[:, 0] - x0_mh) - sh_x) < 0.1 * sh_x) & (SKm[:, 2] < float(joint("head")[2]) - 0.06)]
sh_top_dr = float(np.percentile(_band[:, 2], 99.5))
rep["align"] = {"scale_from_eyes": round(S_, 4), "dressed_sole_z": round(float(Dn[:, 2].min()), 3), "mh_sole_z": round(sole_mh, 3),
                "shoulder_top_dressed_minus_mh_m": round(sh_top_dr - sh_top_mh, 3)}
# The hair object: into the MetaHuman's frame, onto the head, and cleaned against the MetaHuman's own head.
if hr is not None:
    hr.data.transform(T_)
    Hc = co(hr.data)
    # The body is stood on the legs' line; the head may sit a centimetre off it (posture). Hair is moved so that the
    # Tripo face's front and eye line lie on the MetaHuman's: fully above the chin, fading out down to the shoulders.
    _eye_now = np.array([x0_mh + S_ * xe_d, y0_mh + S_ * ye_d])
    _eye_mh = np.array([EY["mh_eye_mid"][0], EY["mh_eye_mid"][1] - float(os.environ.get("CORNEA", 0.006))])
    _dh = _eye_mh - _eye_now
    _zc, _zs = float(joint("head")[2]) - 0.062, sh_top_mh
    _wh = np.clip((Hc[:, 2] - _zs) / (_zc - _zs), 0, 1)
    _wh = _wh * _wh * (3 - 2 * _wh)
    Hc[:, 0] += _wh * _dh[0]
    Hc[:, 1] += _wh * _dh[1]
    hr.data.vertices.foreach_set("co", Hc.ravel())
    hr.data.update()
    rep["hair_head_shift_mm"] = [round(float(x) * 1000, 1) for x in _dh]
    if HAIR_MODE == "ears" and GROOM_HULL:
        # The ears are what sticks out of OUR hair. Everything of the Tripo hair mesh inside the groom's outer hull
        # (yuki_groom_hull.py: largest strand radius per 3-degree direction around the head) is hidden by our strands
        # anyway, and from below or behind it showed as dark open sheets (owner's editor screenshot, 2026-11-14).
        # A cone under each ear tip (t6f, t6g) also tore the ears' own wide bases. Kept: faces further out than the
        # hull minus EAR_IN; then the largest connected piece per side; then a back EAR_T thick in the ears' pink.
        _G = np.load(GROOM_HULL)
        _c, _st, _hull = _G["centre"], float(_G["step"]), _G["hull"]
        # Sink each ear into our hair: the Tripo ears were made for the Tripo hair, which stands higher than our strands,
        # so their wide bases lay 0 to 1.5 cm ABOVE our hair as dark jagged plates (t6k, full-resolution crops,
        # 2026-11-14). Each side moves EAR_SINK toward the head centre along the line to its own centroid.
        EAR_SINK = float(os.environ.get("EAR_SINK", 0.012))
        _V = co(hr.data)
        for _sdv in (_V[:, 0] > x0_mh, _V[:, 0] <= x0_mh):
            if _sdv.any():
                _dir = _V[_sdv].mean(0) - _c
                _dir /= np.linalg.norm(_dir)
                _V[_sdv] -= EAR_SINK * _dir
        hr.data.vertices.foreach_set("co", _V.ravel())
        hr.data.update()
        _fc = np.array([hr.data.polygons[i].center[:] for i in range(len(hr.data.polygons))])
        _d = _fc - _c
        _r = np.linalg.norm(_d, axis=1)
        _el = np.degrees(np.arcsin(np.clip(_d[:, 2] / np.maximum(_r, 1e-9), -1, 1)))
        _az = np.degrees(np.arctan2(_d[:, 1], _d[:, 0]))
        _ie = np.clip(((_el + 90) / _st).astype(int), 0, _hull.shape[0] - 1)
        _ia = np.clip(((_az + 180) / _st).astype(int), 0, _hull.shape[1] - 1)
        _hr = _hull[_ie, _ia]
        # PRISM (2026-11-14, after the owner circled flat dark plates at the ear bases and flaps behind them in t6j):
        # the hull cut left Tripo hair pieces that stand out of our strands, and its cut edges at the hair surface
        # became flat solidified plates. Now each ear is the clean top of the ear (the faces within EAR_TOP of the
        # tip), extended straight down as a vertical prism of its own outline (convex, EAR_PAD wider), down to
        # EAR_H below the tip, deep in our hair where the cut edge and its rim are hidden. Nothing outside the
        # prism is kept, so the curls behind and in front of each ear go.
        EAR_IN = float(os.environ.get("EAR_IN", 0.004))      # kept below our hair's outer surface (hidden)
        EAR_TOP, EAR_PAD, EH = (float(os.environ.get("EAR_TOP", 0.035)), float(os.environ.get("EAR_PAD", 0.004)),
                                float(os.environ.get("EAR_H", 0.075)))

        def _hull2(pts):
            pts = sorted(map(tuple, pts))
            def cross(o, a, b):
                return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
            lo, up = [], []
            for p_ in pts:
                while len(lo) >= 2 and cross(lo[-2], lo[-1], p_) <= 0:
                    lo.pop()
                lo.append(p_)
            for p_ in reversed(pts):
                while len(up) >= 2 and cross(up[-2], up[-1], p_) <= 0:
                    up.pop()
                up.append(p_)
            return np.array(lo[:-1] + up[:-1])

        def _inside_convex(poly, xy, pad):
            c_ = poly.mean(0)
            poly = c_ + (poly - c_) * (1 + pad / np.maximum(np.linalg.norm(poly - c_, axis=1, keepdims=True), 1e-9))
            ok = np.ones(len(xy), bool)
            for i_ in range(len(poly)):
                a_, b_ = poly[i_], poly[(i_ + 1) % len(poly)]
                ok &= ((b_[0] - a_[0]) * (xy[:, 1] - a_[1]) - (b_[1] - a_[1]) * (xy[:, 0] - a_[0])) >= 0
            return ok

        _out = np.zeros(len(_fc), bool)
        rep["ear_prism"] = {}
        for _nm, _sd in (("left", _fc[:, 0] > x0_mh), ("right", _fc[:, 0] <= x0_mh)):
            if not _sd.any():
                continue
            _tz = _fc[_sd][:, 2].max()
            _top = _sd & (_fc[:, 2] > _tz - EAR_TOP)
            _poly = _hull2(_fc[_top][:, :2])
            _in = _sd & (_fc[:, 2] > _tz - EH) & _inside_convex(_poly, _fc[:, :2], EAR_PAD) & (_r > _hr - EAR_IN)
            _out |= _in
            rep["ear_prism"][_nm] = {"tip_z": round(float(_tz), 4), "outline_cm": [round(float(x) * 100, 1) for x in np.ptp(_poly, axis=0)],
                                     "faces": int(_in.sum())}
        _bme = bmesh.new()
        _bme.from_mesh(hr.data)
        _bme.faces.ensure_lookup_table()
        bmesh.ops.delete(_bme, geom=[_bme.faces[i] for i in np.nonzero(~_out)[0]], context="FACES")
        bmesh.ops.delete(_bme, geom=[v for v in _bme.verts if not v.link_faces], context="VERTS")
        _bme.faces.ensure_lookup_table()
        _comp, _cid = {}, 0
        for _f0 in _bme.faces:
            if _f0.index in _comp:
                continue
            _stack = [_f0]
            _comp[_f0.index] = _cid
            while _stack:
                _ff = _stack.pop()
                for _e in _ff.edges:
                    for _g in _e.link_faces:
                        if _g.index not in _comp:
                            _comp[_g.index] = _cid
                            _stack.append(_g)
            _cid += 1
        _side = {}
        for _f in _bme.faces:
            k_ = (_comp[_f.index], _f.calc_center_median().x > x0_mh)
            _side[k_] = _side.get(k_, 0) + 1
        _best = {}
        for (k_, sd), nfc in _side.items():
            if nfc > _best.get(sd, (0, None))[0]:
                _best[sd] = (nfc, k_)
        _keepc = {k_ for _, k_ in _best.values()}
        bmesh.ops.delete(_bme, geom=[f for f in _bme.faces if _comp[f.index] not in _keepc], context="FACES")
        bmesh.ops.delete(_bme, geom=[v for v in _bme.verts if not v.link_faces], context="VERTS")
        _bme.to_mesh(hr.data)
        _bme.free()
        hr.data.update()
        # EAR_MAP (owner 2026-11-15: "namapuj ich presne na parochnove usi"): each Tripo ear is fitted onto the ear of
        # our wig, the hull of the wig's ear cards that yuki_hair_strands exports as yuki_ears.fbx. The Tripo ears had
        # been sunk 12 mm and stood lower and smaller than the wig's ears, so the wig's ear fur stood beside them.
        # Per side, the parts of both ears outside our hair (GROOM_HULL) get their own frame: up = the long axis, out =
        # the thin axis away from the head centre, side = across. The Tripo ear is scaled along side and up to the wig
        # ear's 5 to 95 % extents (thickness kept), turned into the wig ear's frame, centred on it, and its tip put on
        # the wig ear's tip. Use with EAR_SINK=0.
        EAR_MAP = os.environ.get("EAR_MAP", "")
        if EAR_MAP:
            _pre = set(bpy.data.objects)
            bpy.ops.import_scene.fbx(filepath=str(Path(EAR_MAP).resolve()))
            _new = [o_ for o_ in bpy.data.objects if o_ not in _pre and o_.type == "MESH"]
            _HV = np.concatenate([np.array([(o_.matrix_world @ v_.co)[:] for v_ in o_.data.vertices]) for o_ in _new])
            for o_ in list(bpy.data.objects):
                if o_ not in _pre:
                    bpy.data.objects.remove(o_, do_unlink=True)
            _V = co(hr.data)

            def _vis(P):
                d_ = P - _c
                r_ = np.linalg.norm(d_, axis=1)
                el_ = np.degrees(np.arcsin(np.clip(d_[:, 2] / np.maximum(r_, 1e-9), -1, 1)))
                az_ = np.degrees(np.arctan2(d_[:, 1], d_[:, 0]))
                h_ = _hull[np.clip(((el_ + 90) / _st).astype(int), 0, _hull.shape[0] - 1),
                           np.clip(((az_ + 180) / _st).astype(int), 0, _hull.shape[1] - 1)]
                return r_ > h_

            def _frame(P):
                # up = from the centre of the lowest fifth of the ear to its tip; out = the thin axis away from the
                # head centre; side = across. (Plain PCA axes left the tips 1.3 to 2.9 cm apart, t6o.)
                tip_ = P[np.argmax(P[:, 2])]
                z0_, z1_ = P[:, 2].min(), P[:, 2].max()
                base_ = P[P[:, 2] < z0_ + 0.2 * (z1_ - z0_)].mean(0)
                up_ = tip_ - base_
                up_ /= np.linalg.norm(up_)
                _u, _s, vt_ = np.linalg.svd(P - P.mean(0), full_matrices=False)
                out_ = vt_[2] - up_ * (vt_[2] @ up_)
                out_ /= np.linalg.norm(out_)
                if out_ @ (P.mean(0) - _c) < 0:
                    out_ = -out_
                sd_ = np.cross(up_, out_)
                return tip_, base_, np.stack([sd_, up_, out_])

            from mathutils.kdtree import KDTree as _KDm
            rep["ear_map"] = {}
            for _nm, _mT, _mH in (("left", _V[:, 0] > x0_mh, _HV[:, 0] > x0_mh), ("right", _V[:, 0] <= x0_mh, _HV[:, 0] <= x0_mh)):
                if not _mT.any() or not _mH.any():
                    continue
                PT, PH = _V[_mT], _HV[_mH]
                vT, vH = PT[_vis(PT)], PH[_vis(PH)]
                if len(vT) < 20 or len(vH) < 20:
                    vT, vH = PT, PH
                tT, bT, BT = _frame(vT)
                tH, bH, BH = _frame(vH)
                LT, LH = (vT - tT) @ BT.T, (vH - tH) @ BH.T
                ext = lambda a: np.percentile(a, 95) - np.percentile(a, 5)
                sx = ext(LH[:, 0]) / max(ext(LT[:, 0]), 1e-6)
                sy = np.linalg.norm(tH - bH) / max(np.linalg.norm(tT - bT), 1e-6)
                L_ = (PT - tT) @ BT.T
                L_[:, 0] *= sx
                L_[:, 1] *= sy
                newP = tH + L_ @ BH                       # tip on tip, then the ear in the wig ear's frame
                # centred in the wig ear's depth: tip on tip left the Tripo sheet at the back of the wig ear, and its
                # back stood about 1 cm behind the fur in the side views (ears_t6r, Unreal, 2026-11-15)
                _vn = _vis(newP)
                _pn = newP[_vn] if _vn.any() else newP
                _dout = float(((vH - tH) @ BH[2]).mean() - ((_pn - tH) @ BH[2]).mean())
                if os.environ.get("EAR_MAP_CENTRE", "1") != "1":
                    _dout = 0.0
                newP = newP + _dout * BH[2]
                _kdh = _KDm(len(PH))
                for _j, _q in enumerate(PH):
                    _kdh.insert(Vector(_q), _j)
                _kdh.balance()
                nv_ = newP[_vis(newP)] if _vis(newP).any() else newP
                dd_ = np.array([_kdh.find(Vector(q_))[2] for q_ in nv_])
                _V[_mT] = newP
                rep["ear_map"][_nm] = {"scale_side": round(float(sx), 3), "scale_up": round(float(sy), 3), "out_shift_mm": round(_dout * 1000, 1),
                                       "wig_tip_m": tH.round(4).tolist(), "tip_after_m": newP[np.argmax(newP[:, 2])].round(4).tolist(),
                                       "turn_deg": round(float(np.degrees(np.arccos(np.clip(BT[1] @ BH[1], -1, 1)))), 1),
                                       "visible_to_wig_mm_mean": round(float(dd_.mean()) * 1000, 1),
                                       "visible_to_wig_mm_p95": round(float(np.percentile(dd_, 95)) * 1000, 1)}
            hr.data.vertices.foreach_set("co", _V.ravel())
            hr.data.update()
            # Outside our hair, nothing of the Tripo ear may stand away from the wig ear: turned onto the wig ear, the
            # part that used to reach down into the hair (the prism of the ear's outline) hung out behind the head as
            # flaps (t6p side and back views, 2026-11-15). A face goes when its centre is outside the hair hull AND
            # farther than EAR_MAP_FAR from the wig ear (its hull vertices). Cutting below the wig ear's lowest point
            # removed nothing (t6q): the wig ear's cards reach deep into the hair.
            FAR_ = float(os.environ.get("EAR_MAP_FAR", 0.012))
            _fcm = np.array([hr.data.polygons[i].center[:] for i in range(len(hr.data.polygons))])
            _kdw = _KDm(len(_HV))
            for _j, _q in enumerate(_HV):
                _kdw.insert(Vector(_q), _j)
            _kdw.balance()
            _dw = np.array([_kdw.find(Vector(q_))[2] for q_ in _fcm])
            _drop = _vis(_fcm) & (_dw > FAR_)
            for _nm, _sdf in (("left", _fcm[:, 0] > x0_mh), ("right", _fcm[:, 0] <= x0_mh)):
                rep["ear_map"].setdefault(_nm, {})["faces_cut_far_from_wig_ear"] = int((_drop & _sdf).sum())
            if _drop.any():
                _bmc = bmesh.new()
                _bmc.from_mesh(hr.data)
                _bmc.faces.ensure_lookup_table()
                bmesh.ops.delete(_bmc, geom=[_bmc.faces[i] for i in np.nonzero(_drop)[0]], context="FACES")
                bmesh.ops.delete(_bmc, geom=[v for v in _bmc.verts if not v.link_faces], context="VERTS")
                _bmc.to_mesh(hr.data)
                _bmc.free()
                hr.data.update()
            print("EAR_MAP", rep["ear_map"], flush=True)
        # Dive: where an ear comes within EAR_BLEND of our hair's outer surface, its vertices bend in toward the head
        # centre (EAR_DIVE x the shortfall), so the cut bottom edge ends about 2 cm deep in the strands instead of
        # showing as a jagged dark edge where the hair is thin (t6l crops, 2026-11-14).
        EAR_BLEND, EAR_DIVE = float(os.environ.get("EAR_BLEND", 0.010)), float(os.environ.get("EAR_DIVE", 1.4))
        _V = co(hr.data)
        _dv = _V - _c
        _rv = np.linalg.norm(_dv, axis=1)
        _elv = np.degrees(np.arcsin(np.clip(_dv[:, 2] / np.maximum(_rv, 1e-9), -1, 1)))
        _azv = np.degrees(np.arctan2(_dv[:, 1], _dv[:, 0]))
        _hv = _hull[np.clip(((_elv + 90) / _st).astype(int), 0, _hull.shape[0] - 1),
                    np.clip(((_azv + 180) / _st).astype(int), 0, _hull.shape[1] - 1)]
        _short = np.clip(EAR_BLEND - (_rv - _hv), 0, None) * (_hv > 0)
        _V -= (EAR_DIVE * _short)[:, None] * _dv / np.maximum(_rv, 1e-9)[:, None]
        hr.data.vertices.foreach_set("co", _V.ravel())
        hr.data.update()
        rep["ear_dive_max_mm"] = round(float((EAR_DIVE * _short).max()) * 1000, 1)
        for _pl in hr.data.polygons:
            _pl.material_index = 0
        _mod = hr.modifiers.new("ear_back", "SOLIDIFY")
        _mod.thickness = float(os.environ.get("EAR_T", 0.0025))
        # the new shell grows BEHIND the Tripo sheet (whose normals face the front): with +1 it grew in front and the
        # ear's back stayed the sheet's back face, black from behind in Unreal (t6i, 2026-11-14)
        _mod.offset = float(os.environ.get("EAR_OFFSET", -1.0))
        _mod.use_rim = True
        _mod.material_offset = 1
        _mod.material_offset_rim = 1
        if len(hr.data.materials) < 2:
            hr.data.materials.append(hr.data.materials[0])
        bpy.context.view_layer.objects.active = hr
        for _o in bpy.context.selected_objects:
            _o.select_set(False)
        hr.select_set(True)
        bpy.ops.object.modifier_apply(modifier=_mod.name)
        _uvl = hr.data.uv_layers.active.data
        _nb = 0
        for _pl in hr.data.polygons:
            if _pl.material_index == 1:
                for _li in _pl.loop_indices:
                    _uvl[_li].uv = ear_uv
                _pl.material_index = 0
                _nb += 1
        hr.data.materials.pop(index=1)
        Hc = co(hr.data)
        rep["ear_hull_cut"] = {"faces_out": int(_out.sum()), "faces_kept": len(hr.data.polygons), "back_faces": _nb}
    # what lies on the MetaHuman's face is the Tripo face's skin (and its eyes, lips, brows): removed
    _hp = os.environ.get("HEAD_FBX", "")
    n_face = 0
    if _hp:
        _b4 = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=str(Path(_hp).resolve()))
        _ho = [o for o in bpy.data.objects if o not in _b4]
        _hm = max((o for o in _ho if o.type == "MESH"), key=lambda o: len(o.data.vertices))
        bpy.context.view_layer.update()
        _hb = BVHTree.FromPolygons([_hm.matrix_world @ v.co for v in _hm.data.vertices], [tuple(q.vertices) for q in _hm.data.polygons])
        z_chin_mh = EY["mh_eye_mid"][2] - S_ * (ze_d - EY["chin_z"])
        z_top_mh = EY["mh_eye_mid"][2] + S_ * 0.065
        cand = np.nonzero((Hc[:, 2] > z_chin_mh - 0.012) & (Hc[:, 2] < z_top_mh) & (np.abs(Hc[:, 0] - EY["mh_eye_mid"][0]) < 0.10) & (Hc[:, 1] < EY["mh_eye_mid"][1] + 0.11))[0]
        FACE_MM = float(os.environ.get("FACE_MM", 4.5)) / 1000
        # On the forehead the MetaHuman's skull stands a few millimetres prouder than the Tripo head's, and the test
        # "lies on the face" took the whole fringe (second build with hair). There the Tripo mesh itself decides: its
        # forehead skin shows only in the gaps between locks, recessed behind them. A vertex above the brow line is
        # skin if it is warm in colour and lies more than 4 mm behind the front-most hair within 2 cm of it; everything
        # else there is fringe and is kept (the push out of the head, later, lays it on the MetaHuman's forehead).
        z_brow_mh = EY["mh_eye_mid"][2] + S_ * float(os.environ.get("BROW_UP", 0.014))
        _nl = len(hr.data.loops)
        _uvh = np.zeros(_nl * 2)
        hr.data.uv_layers.active.data.foreach_get("uv", _uvh)
        _uvh = _uvh.reshape(-1, 2)
        _lvh = np.zeros(_nl, dtype=np.int64)
        hr.data.loops.foreach_get("vertex_index", _lvh)
        _vuvh = np.zeros((len(Hc), 2))
        _vuvh[_lvh] = _uvh
        _ch = px[np.clip((_vuvh[:, 1] % 1.0 * h).astype(int), 0, h - 1), np.clip((_vuvh[:, 0] % 1.0 * w).astype(int), 0, w - 1)]
        warm = (_ch[:, 0] - _ch[:, 2]) > float(os.environ.get("FORE_WARM", 0.13))
        gx0, gz0, cell_ = EY["mh_eye_mid"][0] - 0.11, z_chin_mh - 0.02, 0.004
        gi_ = np.clip(((Hc[:, 0] - gx0) / cell_).astype(int), 0, 59)
        gj_ = np.clip(((Hc[:, 2] - gz0) / cell_).astype(int), 0, 79)
        fronth = (Hc[:, 1] < EY["mh_eye_mid"][1] + 0.11) & (np.abs(Hc[:, 0] - EY["mh_eye_mid"][0]) < 0.11) & (Hc[:, 2] > z_chin_mh - 0.02)
        ymin = np.full((60, 80), np.inf)
        np.minimum.at(ymin, (gi_[fronth], gj_[fronth]), Hc[fronth, 1])
        ymn = ymin.copy()
        for _ in range(5):                                    # the front-most hair within 2 cm
            t_ = ymn.copy()
            t_[1:, :] = np.minimum(t_[1:, :], ymn[:-1, :]); t_[:-1, :] = np.minimum(t_[:-1, :], ymn[1:, :])
            t_[:, 1:] = np.minimum(t_[:, 1:], ymn[:, :-1]); t_[:, :-1] = np.minimum(t_[:, :-1], ymn[:, 1:])
            ymn = t_
        kill, n_fore = [], 0
        for i in cand:
            if Hc[i, 2] > z_brow_mh:
                if warm[i] and Hc[i, 1] > ymn[gi_[i], gj_[i]] + 0.004:
                    kill.append(int(i))
                    n_fore += 1
                continue
            loc, no, fi, dd_ = _hb.find_nearest(Vector(Hc[i]))
            if loc is not None and float((Vector(Hc[i]) - loc).dot(no)) < FACE_MM:
                kill.append(int(i))
        rep["hair_forehead_skin_removed"] = n_fore
        n_face = len(kill)
        for o in _ho:
            bpy.data.objects.remove(o)
        _bm = bmesh.new()
        _bm.from_mesh(hr.data)
        _bm.verts.ensure_lookup_table()
        bmesh.ops.delete(_bm, geom=[_bm.verts[i] for i in kill], context="VERTS")
        _bm.to_mesh(hr.data)
        _bm.free()
        # flakes the removal leaves: pieces under 200 vertices
        labh, nh_, _eh = components(hr.data)
        cnt_ = np.bincount(labh, minlength=nh_)
        _sm = np.nonzero(cnt_[labh] < 200)[0]
        if len(_sm):
            _bm = bmesh.new()
            _bm.from_mesh(hr.data)
            _bm.verts.ensure_lookup_table()
            bmesh.ops.delete(_bm, geom=[_bm.verts[i] for i in _sm], context="VERTS")
            _bm.to_mesh(hr.data)
            _bm.free()
        rep["hair_cleaned_on_face"] = {"candidates": int(len(cand)), "removed_on_face": n_face, "flake_vertices": int(len(_sm))}
    n0_ = len(me.vertices)
    for p_ in hr.data.polygons:
        p_.material_index = 0
    bpy.ops.object.select_all(action="DESELECT")
    hr.select_set(True)
    dr.select_set(True)
    bpy.context.view_layer.objects.active = dr
    bpy.ops.object.join()
    me = dr.data
    VROLE = np.concatenate([VROLE.astype("<U8"), np.array(["hair"] * (len(me.vertices) - n0_), dtype="<U8")])
    # the hair's faces are marked: they get a material slot of their own at the end (tint and gloss differ in Unreal)
    _at = me.attributes.new("is_hair", "BOOLEAN", "FACE")
    _vh = VROLE == "hair"
    _pv = np.zeros(len(me.loops), dtype=np.int64)
    me.loops.foreach_get("vertex_index", _pv)
    _ps = np.zeros(len(me.polygons), dtype=np.int64)
    me.polygons.foreach_get("loop_start", _ps)
    _at.data.foreach_set("value", _vh[_pv[_ps]].tolist())
    hr = None
CPm = co(me)                                                  # the pieces, now in the MetaHuman's frame
_hv = np.zeros(len(CPm), bool)                                # (the hair was moved onto the head above)
if _hv.any():
    _eye_now = np.array([x0_mh + S_ * xe_d, y0_mh + S_ * ye_d])
    _eye_mh = np.array([EY["mh_eye_mid"][0], EY["mh_eye_mid"][1] - float(os.environ.get("CORNEA", 0.006))])
    _dh = _eye_mh - _eye_now
    _zc, _zs = float(joint("head")[2]) - 0.062, sh_top_mh
    _wh = np.clip((CPm[_hv, 2] - _zs) / (_zc - _zs), 0, 1)
    _wh = _wh * _wh * (3 - 2 * _wh)
    CPm[_hv, 0] += _wh * _dh[0]
    CPm[_hv, 1] += _wh * _dh[1]
    rep["hair_head_shift_mm"] = [round(float(x) * 1000, 1) for x in _dh]

# bone tables of the whole skeleton, parents first
AB = arm.data.bones
order = []


def _walk(b_):
    order.append(b_.name)
    for c_ in b_.children:
        _walk(c_)


for b_ in AB:
    if b_.parent is None:
        _walk(b_)
An = np.array(A)
RW = {n: An @ np.array(AB[n].matrix_local) for n in order}                      # rest, world
PAR = {n: (AB[n].parent.name if AB[n].parent else None) for n in order}
LOC = {n: (np.linalg.inv(RW[PAR[n]]) @ RW[n] if PAR[n] else RW[n]) for n in order}
jr = lambda n: RW[n][:3, 3].copy()

# landmarks of the costume
_tor = VROLE == "torso"
_fr = _tor & (np.abs(CPm[:, 0] - x0_mh) < 0.06) & (CPm[:, 1] < y0_mh)
zh = float(np.percentile(CPm[_fr, 2], 0.5))
RISE = float(np.clip(zh + float(os.environ.get("HEM_OVER", 0.012)) - crotch_mh, 0.0, 0.22))
# How the pose P is carried: by a scale of each bone along its own axis (X in Unreal; measured: every child of these
# bones lies on its parent's X). Unreal ignores animated bone translations on this skeleton (translation retargeting),
# but not scale. A bone's scale stretches its own skin along the bone and moves its children's origins along it; a
# child takes the parent's scale along its OWN X, so the next joint down is given the reciprocal where the stretch must
# stop (spine_05, hands, feet; the calf gets calf/thigh). The model below is that rule in world space: every bone has a
# stretch (factor k along direction u), twist and corrective bones share their limb's.
L123 = float(np.linalg.norm(jr("spine_02") - jr("spine_01")) + np.linalg.norm(jr("spine_03") - jr("spine_02")) + np.linalg.norm(jr("spine_04") - jr("spine_03")))
L4 = float(np.linalg.norm(jr("spine_05") - jr("spine_04")))
k_sp4 = float(os.environ.get("SPINE4", 0.72))                 # the chest segment gives less: the bust sits on it
k_sp = max(0.3, 1.0 - (RISE - (1 - k_sp4) * L4) / L123)
RISE = (1 - k_sp) * L123 + (1 - k_sp4) * L4
STRETCH = {}                                                  # bone -> (k, u) in the rest pose, world


def _dir(a_, b_):
    v = jr(b_) - jr(a_)
    return v / np.linalg.norm(v)


def _assign(bone, k, u, stop=()):
    STRETCH[bone] = (k, u)
    for c_ in AB[bone].children:
        if c_.name not in stop and c_.name not in STRETCH:
            _assign(c_.name, k, u, stop)


UE_SCALE = {"spine_01": k_sp, "spine_04": k_sp4 / k_sp, "spine_05": 1.0 / k_sp4}
for a_, b_ in (("spine_01", "spine_02"), ("spine_02", "spine_03"), ("spine_03", "spine_04")):
    STRETCH[a_] = (k_sp, _dir(a_, b_))
STRETCH["spine_04"] = (k_sp4, _dir("spine_04", "spine_05"))
aims, ankle_z = {}, {}
pose_rep = {"pelvis_rise_m": round(RISE, 3), "spine_01_03_factor": round(k_sp, 3), "spine_04_factor": k_sp4, "front_hem_z": round(zh, 3), "crotch_mh_z": round(crotch_mh, 3)}
for sfx, side in (("l", 1.0), ("r", -1.0)):
    cuff, glove = CPm[VROLE == "cuff_" + sfx], CPm[VROLE == "glove_" + sfx]
    d = glove.mean(0) - cuff.mean(0)
    d /= np.linalg.norm(d)
    wrist = cuff.mean(0) + d * (float(((glove - cuff.mean(0)) @ d).min()) + float(os.environ.get("WRIST_IN_GLOVE", 0.012)))
    sh = jr("upperarm_" + sfx)
    L_arm = float(np.linalg.norm(jr("lowerarm_" + sfx) - sh) + np.linalg.norm(jr("hand_" + sfx) - jr("lowerarm_" + sfx)))
    f_a = float(np.linalg.norm(wrist - sh) / L_arm)
    _assign("lowerarm_" + sfx, f_a, _dir("lowerarm_" + sfx, "hand_" + sfx), stop=("hand_" + sfx,))
    _assign("upperarm_" + sfx, f_a, _dir("upperarm_" + sfx, "lowerarm_" + sfx), stop=("lowerarm_" + sfx,))
    UE_SCALE["upperarm_" + sfx], UE_SCALE["hand_" + sfx] = f_a, 1.0 / f_a
    aims["upperarm_" + sfx] = ("lowerarm_" + sfx, wrist)
    aims["lowerarm_" + sfx] = ("hand_" + sfx, wrist)
    aims["hand_" + sfx] = ("middle_01_" + sfx, None, d)
    # leg: the boot's axis from its own slabs; the knee is at the knee guard (the boot's foremost band in its middle
    # third), the ankle ANKLE_H over the boot's sole
    L = CPm[VROLE == "boot_" + sfx]
    sole, btop = float(L[:, 2].min()), float(L[:, 2].max())
    cen = []
    for z in np.arange(sole + 0.05, btop - 0.02, 0.012):
        q = L[(L[:, 2] >= z) & (L[:, 2] < z + 0.012)]
        if len(q) > 20:
            cen.append([(q[:, 0].max() + q[:, 0].min()) / 2, (q[:, 1].max() + q[:, 1].min()) / 2, z + 0.006, q[:, 1].min()])
    cen = np.array(cen)
    mid_ = (cen[:, 2] > sole + 0.38 * (btop - sole)) & (cen[:, 2] < sole + 0.72 * (btop - sole))
    prot = cen[:, 1] - cen[:, 3]                                # how far the front stands before the axis
    kz = float(np.average(cen[mid_, 2], weights=np.clip(prot[mid_] - np.percentile(prot[mid_], 60), 0, None) + 1e-6))
    knee = cen[int(np.argmin(np.abs(cen[:, 2] - kz))), :3].copy()
    ankle = cen[int(np.argmin(np.abs(cen[:, 2] - (sole + float(os.environ.get("ANKLE_H", 0.15)))))), :3].copy()
    ankle_z[sfx] = float(ankle[2])
    hip = jr("thigh_" + sfx) + np.array([0, 0, RISE])
    f_t = float(np.linalg.norm(knee - hip) / np.linalg.norm(jr("calf_" + sfx) - jr("thigh_" + sfx)))
    f_c = float(np.linalg.norm(ankle - knee) / np.linalg.norm(jr("foot_" + sfx) - jr("calf_" + sfx)))
    _assign("calf_" + sfx, f_c, _dir("calf_" + sfx, "foot_" + sfx), stop=("foot_" + sfx,))
    _assign("thigh_" + sfx, f_t, _dir("thigh_" + sfx, "calf_" + sfx), stop=("calf_" + sfx,))
    UE_SCALE["thigh_" + sfx], UE_SCALE["calf_" + sfx], UE_SCALE["foot_" + sfx] = f_t, f_c / f_t, 1.0 / f_c
    aims["thigh_" + sfx] = ("calf_" + sfx, knee)
    aims["calf_" + sfx] = ("foot_" + sfx, ankle)
    pose_rep[sfx] = {"arm_factor": round(f_a, 3), "thigh_factor": round(f_t, 3), "calf_factor": round(f_c, 3), "knee": [round(float(x), 3) for x in knee],
                     "ankle": [round(float(x), 3) for x in ankle], "wrist": [round(float(x), 3) for x in wrist], "boot_sole_z": round(sole, 3), "boot_top_z": round(btop, 3)}

MSK, QACC = {}, {}
I3 = np.eye(3)
for n in order:
    h = jr(n)
    if PAR[n]:
        Mp = MSK[PAR[n]]
        hp = Mp[:3, :3] @ h + Mp[:3, 3]
        Q = QACC[PAR[n]].copy()
    else:
        hp = h + np.array([0.0, 0.0, RISE])                    # the skeleton's root is the pelvis
        Q = I3.copy()
    k, u = STRETCH.get(n, (1.0, np.array([1.0, 0.0, 0.0])))
    St = I3 + (k - 1.0) * np.outer(u, u)
    if n in aims:
        tip = aims[n][0]
        tip_p = hp + Q @ St @ (jr(tip) - h)
        tgt = aims[n][2] if len(aims[n]) > 2 else (aims[n][1] - hp)
        Rq = Vector(tip_p - hp).normalized().rotation_difference(Vector(tgt).normalized()).to_matrix()
        Q = np.array(Rq) @ Q
    Lin = Q @ St
    M = np.eye(4)
    M[:3, :3] = Lin
    M[:3, 3] = hp - Lin @ h
    MSK[n], QACC[n] = M, Q
WP = {n: MSK[n] @ RW[n] for n in order}                        # posed bone matrices (with the stretch), for the preview
POSED_HEAD = {n: MSK[n][:3, :3] @ jr(n) + MSK[n][:3, 3] for n in order}
pose_rep["head_moved_mm"] = round(float(np.linalg.norm(POSED_HEAD["head"] - jr("head"))) * 1000, 2)
for sfx in ("l", "r"):
    pose_rep[sfx]["wrist_error_mm"] = round(float(np.linalg.norm(POSED_HEAD["hand_" + sfx] - np.array(pose_rep[sfx]["wrist"]))) * 1000, 1)
    pose_rep[sfx]["ankle_error_mm"] = round(float(np.linalg.norm(POSED_HEAD["foot_" + sfx] - np.array(pose_rep[sfx]["ankle"]))) * 1000, 1)
rep["pose"] = pose_rep
SOLE_DR = float(Dn[:, 2].min())
json.dump({"scale_x": UE_SCALE, "actor_raise_m": sole_mh - (SOLE_DR - RISE),
           "note": "local scale X of each bone (the bone's own axis); the pelvis is not moved in Unreal, so the actor is raised by actor_raise_m to stand the shoes on the floor"},
          open(out / "proportions.json", "w"), indent=1)
print("POSE", json.dumps(rep["align"]), json.dumps(pose_rep), flush=True)

# posed body by linear blend skinning of the rest body with the matrices of P
gnames = [g_.name for g_ in body.vertex_groups]
bones = [n for n in gnames if n in MSK]
if "head" not in bones:          # the body mesh has no skin on the head bone; the hair needs it
    bones.append("head")
bidx = {n: i for i, n in enumerate(bones)}
BW = np.zeros((len(B0), len(bones)), dtype=np.float32)
for v in body.data.vertices:
    for g_ in v.groups:
        n = gnames[g_.group]
        if n in bidx:
            BW[v.index, bidx[n]] = g_.weight
BW /= np.maximum(BW.sum(1), 1e-9)[:, None]
BM = np.array([MSK[n] for n in bones])
B0h = np.c_[B0, np.ones(len(B0))]
BP = np.zeros((len(B0), 3))
for bi in np.nonzero(BW.sum(0) > 1e-6)[0]:
    BP += BW[:, bi:bi + 1] * (B0h @ BM[bi].T)[:, :3]
body.data.calc_loop_triangles()
BT = np.array([t.vertices[:] for t in body.data.loop_triangles])
bvh = BVHTree.FromPolygons([Vector(p_) for p_ in BP], [tuple(int(i) for i in t) for t in BT])
dom = np.array([bones[i] for i in BW.argmax(1)])
crotch_p = crotch_mh + RISE

# Tail (owner 2026-11-14: it grows from the tailbone, above the buttocks, and must be long enough to show past the
# hair). Its end nearest the pelvis is the root; the tail is moved so the root sits just inside the back TAIL_DZ over
# the pelvis joint, leaves straight back and TAIL_UP degrees up, and over TAIL_BEND metres falls into the Tripo model's
# own sweep to the figure's left. TAIL_SCALE lengthens it.
from mathutils import Quaternion
_tv = VROLE == "tail"
_pz = float(POSED_HEAD["pelvis"][2]) + float(os.environ.get("TAIL_DZ", 0.015))
_bk = BP[(np.abs(BP[:, 0] - x0_mh) < 0.03) & (np.abs(BP[:, 2] - _pz) < 0.015)]
_tb = np.array([x0_mh, float(_bk[:, 1].max()), _pz])
_dt = np.linalg.norm(CPm[_tv] - _tb, axis=1)
_root = CPm[_tv][_dt < np.percentile(_dt, 4)].mean(0)
_rt = _tb + np.array([0.0, -0.006, 0.0])
_dv = CPm[_tv] - _root
_ds = np.linalg.norm(_dv, axis=1)
_seg = _dv[(_ds > 0.03) & (_ds < 0.10)].mean(0)
_seg /= np.linalg.norm(_seg)
_up = math.radians(float(os.environ.get("TAIL_UP", 20)))
q_full = Vector(_seg).rotation_difference(Vector((0.0, math.cos(_up), math.sin(_up))))
q_id = Quaternion()
BEND = float(os.environ.get("TAIL_BEND", 0.16))
_new = np.zeros_like(_dv)
for i_, (v_, d_) in enumerate(zip(_dv, _ds)):
    k_ = min(1.0, d_ / BEND)
    k_ = k_ * k_ * (3 - 2 * k_)
    _new[i_] = np.array(q_full.slerp(q_id, k_) @ Vector(v_))
CPm[_tv] = _rt + _new * float(os.environ.get("TAIL_SCALE", 1.4))
rep["tail"] = {"tailbone": [round(float(x), 3) for x in _tb]}
me.vertices.foreach_set("co", CPm.ravel())
me.update()

# ---- 3. fit: tight pieces keep their relief and take the MetaHuman's shape, loose pieces keep their own shape
CP = co(me)
n_c = len(CP)
near = np.zeros((n_c, 3))
nrm = np.zeros((n_c, 3))
dist = np.zeros(n_c)
nb = np.zeros(n_c, dtype=np.int64)
for i in range(n_c):
    loc, no, fi, dd_ = bvh.find_nearest(Vector(CP[i]))
    near[i], nrm[i] = loc, no
    v3 = CP[i] - np.array(loc)
    dist[i] = dd_ * (1.0 if v3 @ np.array(no) >= 0 else -1.0)
    tri = BT[fi]
    nb[i] = tri[int(np.argmin(np.linalg.norm(BP[tri] - np.array(loc), axis=1)))]
vdir = CP - near
vlen = np.maximum(np.linalg.norm(vdir, axis=1), 1e-9)
vdir = vdir / vlen[:, None] * np.sign(dist + 1e-12)[:, None]          # outward at the costume vertex
vdom = dom[nb]
E = np.array([e.vertices[:] for e in me.edges])
is_tail = VROLE == "tail"
foot = np.zeros(n_c, bool)
for sfx in ("l", "r"):
    foot |= (VROLE == "boot_" + sfx) & (CP[:, 2] < ankle_z[sfx] + 0.01)
# skirt and hip plates: between the hem and the belt, around the pelvis. Read from the dressed mesh: the band of
# heights where the costume stands more than 2.5 cm off the body near the hips.
# no limit in width: the skirt's outer folds and pouches beyond 24 cm were treated as tight and pulled onto the legs
hipband = (VROLE == "torso") & (CP[:, 2] > crotch_p - 0.12) & (CP[:, 2] < crotch_p + 0.30)
far = hipband & (dist > 0.025)
z_hem, z_belt = (float(np.percentile(CP[far, 2], 1)), float(np.percentile(CP[far, 2], 99))) if far.sum() > 200 else (crotch_p - 0.03, crotch_p + 0.14)
loose_w = np.zeros(n_c)
loose_w[hipband] = np.clip((z_belt + 0.03 - CP[hipband, 2]) / 0.03, 0, 1) * np.clip((CP[hipband, 2] - (z_hem - 0.03)) / 0.01, 0, 1)
loose_w[foot] = 1.0
loose_w[is_tail] = 1.0
is_hair = VROLE == "hair"
loose_w[is_hair] = 1.0
loose_w[np.isin(VROLE, ["boot_l", "boot_r"])] = 1.0           # the boots keep the Tripo model's shape and relief (owner 2026-11-14)
keep_shape = foot | is_tail                                   # never moved at all
rep["zones"] = {"tail_vertices": int(is_tail.sum()), "foot_vertices": int(foot.sum()), "skirt_hem_z": round(z_hem, 3), "belt_z": round(z_belt, 3), "hipband_vertices": int(hipband.sum())}
# low-pass of the standoff in space (voxels of 1.2 cm, Gaussian of SIGMA), tight vertices only
tight = loose_w < 0.5
VOX, SIG = 0.012, float(os.environ.get("SIGMA", 0.035))
lo = CP.min(0) - 3 * SIG
gi = np.floor((CP - lo) / VOX).astype(int)
shape = gi.max(0) + 1 + int(3 * SIG / VOX)
acc = np.zeros(shape)
cnt = np.zeros(shape)
np.add.at(acc, tuple(gi[tight].T), dist[tight])
np.add.at(cnt, tuple(gi[tight].T), 1.0)
rad = int(round(2.5 * SIG / VOX))
ker = np.exp(-0.5 * (np.arange(-rad, rad + 1) * VOX / SIG) ** 2)
for axis in range(3):
    acc = np.apply_along_axis(lambda m_: np.convolve(m_, ker, mode="same"), axis, acc)
    cnt = np.apply_along_axis(lambda m_: np.convolve(m_, ker, mode="same"), axis, cnt)
d_low = acc[tuple(gi.T)] / np.maximum(cnt[tuple(gi.T)], 1e-9)
CLEAR = float(os.environ.get("CLEAR", 0.007))      # 4 mm let the body through between the vertices of the decimated mesh (seen in the first fit)
d_new = np.maximum(dist - d_low + CLEAR, 0.006)
move = (1 - loose_w)[:, None] * vdir * (d_new - dist)[:, None]
# loose pieces must still clear the body
for sfx in ("l", "r"):                                        # below the knee the body is hidden in Unreal: the boot is left alone there
    keep_shape |= (VROLE == "boot_" + sfx) & (CP[:, 2] < pose_rep[sfx]["knee"][2] + 0.03)
inside = (loose_w > 0.5) & (dist < 0.006) & ~keep_shape              # skirt and shoes: pushed out where the body would show, never pulled in
move[inside] = vdir[inside] * (0.006 - dist[inside])[:, None]
for _ in range(4):                                                     # smooth the move over the costume's own edges
    a2 = move.copy()
    c2 = np.ones(n_c)
    np.add.at(a2, E[:, 0], move[E[:, 1]])
    np.add.at(a2, E[:, 1], move[E[:, 0]])
    np.add.at(c2, E[:, 0], 1)
    np.add.at(c2, E[:, 1], 1)
    move = a2 / c2[:, None]
# hair: clear of the body by 12 mm (it lies on the corset, which stands 7 mm off), and never inside the head
_hin = is_hair & (dist < 0.012)
move[_hin] = vdir[_hin] * (0.012 - dist[_hin])[:, None]
move[keep_shape] = 0
CPf = CP + move
_hp = os.environ.get("HEAD_FBX", "")
if is_hair.any() and _hp:
    _b4 = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(Path(_hp).resolve()))
    _ho = [o for o in bpy.data.objects if o not in _b4]
    _hm = max((o for o in _ho if o.type == "MESH"), key=lambda o: len(o.data.vertices))
    bpy.context.view_layer.update()
    _hb = BVHTree.FromPolygons([_hm.matrix_world @ v.co for v in _hm.data.vertices], [tuple(q.vertices) for q in _hm.data.polygons])
    _n_in = 0
    for i in np.nonzero(is_hair & (CPf[:, 2] > sh_top_mh))[0]:
        loc, no, fi, dd_ = _hb.find_nearest(Vector(CPf[i]))
        if loc is None:
            continue
        out_ = float((Vector(CPf[i]) - loc).dot(no))
        if out_ < 0.003:
            CPf[i] = np.array(loc) + np.array(no) * 0.003
            _n_in += 1
    for o in _ho:
        bpy.data.objects.remove(o)
    rep["hair_vertices_pushed_out_of_head"] = _n_in
rep["fit"] = {"standoff_before_mm_p5_50_95": [round(float(x) * 1000, 1) for x in np.percentile(dist[tight], [5, 50, 95])],
              "standoff_after_mm_p5_50_95": [round(float(x) * 1000, 1) for x in np.percentile(d_new[tight], [5, 50, 95])],
              "moved_mm_p50_95_max": [round(float(x) * 1000, 1) for x in (np.percentile(np.linalg.norm(move, axis=1), 50), np.percentile(np.linalg.norm(move, axis=1), 95), np.linalg.norm(move, axis=1).max())]}
print("FIT", json.dumps(rep["zones"]), json.dumps(rep["fit"]), flush=True)

# ---- 4. weights from the nearest body vertex, smoothed over the costume; the tail follows the pelvis
CW = BW[nb].astype(np.float64)
for _ in range(int(os.environ.get("W_SMOOTH", 25))):
    a2 = CW.copy()
    c2 = np.ones(n_c)
    np.add.at(a2, E[:, 0], CW[E[:, 1]])
    np.add.at(a2, E[:, 1], CW[E[:, 0]])
    np.add.at(c2, E[:, 0], 1)
    np.add.at(c2, E[:, 1], 1)
    CW = a2 / c2[:, None]
# Each piece follows only the bones of its own body part. The skirt's outer folds hung nearest to the hands and
# took their weights: in the rest pose they were pulled out like wings (seen in the first rest sheet).
is_arm_b = np.array([any(k_ in n for k_ in ("upperarm", "lowerarm", "hand", "index", "middle", "ring", "pinky", "thumb")) for n in bones])
is_leg_b = np.array([any(k_ in n for k_ in ("thigh", "calf", "foot", "ball", "toe")) for n in bones])
strap_v = np.zeros(n_c, bool)
for sfx, side in (("l", 1.0), ("r", -1.0)):
    strap_v |= (VROLE == "torso") & ((CP[:, 0] - x0_mh) * side > abs(float(joint_rest["upperarm_" + sfx][0] - x0_mh)) + 0.02) & (CP[:, 2] > z_belt + 0.03)
armp = np.isin(VROLE, ["cuff_l", "cuff_r", "glove_l", "glove_r"]) | strap_v
bootp = np.isin(VROLE, ["boot_l", "boot_r"])
CW[np.ix_(armp, ~is_arm_b)] = 0
CW[np.ix_(bootp, ~is_leg_b)] = 0
CW[np.ix_((VROLE == "torso") & ~strap_v, is_arm_b)] = 0
for sfx in ("l", "r"):
    fv = (VROLE == "boot_" + sfx) & foot
    CW[fv] = 0
    CW[fv, bidx["foot_" + sfx]] = 1.0
if is_hair.any():
    CW[np.ix_(is_hair, is_arm_b | is_leg_b)] = 0
    _s = CW[is_hair].sum(1, keepdims=True)
    CW[is_hair] = np.where(_s > 1e-6, CW[is_hair] / np.maximum(_s, 1e-9), 0)
    _zc, _zs = float(joint_rest["head"][2]) - 0.062, float(joint_rest["neck_01"][2]) - 0.05
    _wh = np.clip((CP[is_hair, 2] - _zs) / (_zc - _zs), 0, 1)
    _wh = (_wh * _wh * (3 - 2 * _wh))[:, None]
    _oh = np.zeros((int(is_hair.sum()), len(bones)))
    _oh[:, bidx["head"]] = 1.0
    CW[is_hair] = _wh * _oh + (1 - _wh) * CW[is_hair]
empty = CW.sum(1) < 1e-6
CW[empty, bidx["pelvis"]] = 1.0
CW[is_tail] = 0
CW[is_tail, bidx["pelvis"]] = 1.0
CW /= np.maximum(CW.sum(1), 1e-9)[:, None]
# back to the rest pose with the inverse of each vertex's own blended matrix: in the pose P the costume is then exactly
# what was fitted here, whatever the weights
Mv = np.zeros((n_c, 4, 4))
for bi in np.nonzero(CW.sum(0) > 1e-6)[0]:
    Mv += CW[:, bi][:, None, None] * BM[bi][None, :, :]
hom = np.c_[CPf, np.ones(n_c)]
rest = np.einsum("nij,nj->ni", np.linalg.inv(Mv), hom)[:, :3]
me.vertices.foreach_set("co", CPf.ravel())
me.update()
me.materials.append(chk)
for p_ in me.polygons:
    p_.material_index = 1
cam.data.ortho_scale = 1.55
_shots_h = H
H = 2 * (sole_mh + 0.74)        # the check camera's centre height
body.hide_render = True          # the body object stands in its rest pose; the costume here is in the pose P
shots("posed")
body.hide_render = False
for pb in arm.pose.bones:
    pb.matrix_basis = Matrix.Identity(4)
bpy.context.view_layer.update()
me.vertices.foreach_set("co", rest.ravel())
me.update()
shots("rest")
for p_ in me.polygons:
    p_.material_index = 0
me.materials.pop(index=1)
(out / "cut_report.json").write_text(json.dumps(rep, indent=1))
if STAGE == "fit":
    sys.exit()

# ================================================================================================================
# 5. rest pose: costume bound to the armature, black underlayer under the corset and skirt, the skin the built body
#    lacks, a choker ring with its bell
for i, n in enumerate(bones):
    col = CW[:, i]
    nz = np.nonzero(col > 1e-4)[0]
    if len(nz):
        vg = dr.vertex_groups.new(name=n)
        for v in nz:
            vg.add([int(v)], float(col[v]), "REPLACE")
for p_ in me.polygons:
    p_.use_smooth = True
mat.name = "yuki_tripo"
uvname = me.uv_layers.active.name
m_skin = bpy.data.materials.new("yuki_skin")
m_gold = bpy.data.materials.new("yuki_gold")
me.materials.append(m_skin)
me.materials.append(m_gold)
MWb = body.matrix_world.copy()
MWb3 = MWb.to_3x3()
inv3 = MWb3.inverted()
Brest = np.array([MWb @ v.co for v in body.data.vertices])
Bn = np.array([(MWb3 @ v.normal).normalized() for v in body.data.vertices])
torso_b = np.array([("spine" in n) or ("pelvis" in n) or ("clavicle" in n) or ("neck" in n) for n in dom])
thigh_b = np.array(["thigh" in n for n in dom])
yc = float(Brest[torso_b, 1].mean())
NS = 48
sec = lambda P_: (np.floor((np.arctan2(P_[:, 1] - yc, P_[:, 0] - x0_mh) + math.pi) / (2 * math.pi) * NS).astype(int)) % NS
# The corset's top edge and back come out of the cut in rags (hair lay on them in the Tripo model). A clean top line
# is read per sector round the spine, low enough to pass under the rags (80th percentile, median over 7 sectors);
# the costume is trimmed to it and the underlayer, slid onto the line, makes the edge. The same for the upper-arm
# straps: Tripo's are torn, so they are dropped and two bands are built on the arm.
tc = (VROLE == "torso") & ~strap_v & (rest[:, 2] > z_belt)
top = np.full(NS, np.nan)
sc_ = sec(rest[tc])
for k_ in range(NS):
    zz = rest[tc][sc_ == k_, 2]
    if len(zz) > 15:
        top[k_] = np.percentile(zz, float(os.environ.get("TOP_PCT", 80)))
idx_ = np.arange(NS)
good = ~np.isnan(top)
top = np.interp(idx_, np.r_[idx_[good] - NS, idx_[good], idx_[good] + NS], np.r_[top[good], top[good], top[good]])
top = np.array([np.median(top[(np.arange(k_ - 3, k_ + 4)) % NS]) for k_ in range(NS)])
top = (np.roll(top, 1) + 2 * top + np.roll(top, -1)) / 4
top = 0.5 * (top + top[(int(1.5 * NS) - 1 - np.arange(NS)) % NS])       # the same on both sides
# a deeper dip at the front centre (NECK_DIP): the neckline opens between the cups, which is what shows the push-up
_da = ((np.arange(NS) + 0.5) - NS / 4) * (2 * math.pi / NS)
top = top - float(os.environ.get("NECK_DIP", 0.018)) * np.exp(-(_da * 0.11 / 0.028) ** 2)
rep["corset_top_z_by_sector"] = [round(float(x), 3) for x in top]


def topf(P_):
    a_ = (np.arctan2(P_[:, 1] - yc, P_[:, 0] - x0_mh) + math.pi) / (2 * math.pi) * NS - 0.5
    return np.interp(a_, np.arange(-1, NS + 1), np.r_[top[-1], top, top[0]])


# Boots end BOOT_TOP over the knee joint (owner 2026-11-14: much lower, so that bare thigh shows under the mini skirt;
# on the MetaHuman's shorter legs the Tripo boots reached the crotch). A clean cuff with a neon line closes each.
BOOT_TOP = float(os.environ.get("BOOT_TOP", 0.0))             # 0: the boots keep their own top, as on the Tripo model
boot_cut = np.zeros(n_c, bool)
KNEE = {}
for sfx in ("l", "r"):
    kn, hp = np.array(A @ arm.data.bones["calf_" + sfx].head_local), np.array(A @ arm.data.bones["thigh_" + sfx].head_local)
    u_ = (hp - kn) / np.linalg.norm(hp - kn)
    KNEE[sfx] = (kn, u_)
    if BOOT_TOP > 0:
        boot_cut |= (VROLE == "boot_" + sfx) & (((rest - kn) @ u_) > BOOT_TOP)
drop_v = strap_v | (tc & (rest[:, 2] > topf(rest) + 0.002)) | boot_cut
rep["trimmed_vertices"] = {"straps": int(strap_v.sum()), "above_top_line": int((tc & (rest[:, 2] > topf(rest) + 0.002)).sum()), "boot_tops": int(boot_cut.sum())}
_bm = bmesh.new()
_bm.from_mesh(me)
_bm.verts.ensure_lookup_table()
bmesh.ops.delete(_bm, geom=[_bm.verts[i] for i in np.nonzero(drop_v)[0]], context="VERTS")
_bm.to_mesh(me)
_bm.free()
me.update()
# the trim leaves loose scraps (seen under the armpits): islands under 300 vertices go
_lab, _n, _ = components(me)
_cnt = np.bincount(_lab, minlength=_n)
_small = np.nonzero(_cnt[_lab] < 300)[0]
if len(_small):
    _bm = bmesh.new()
    _bm.from_mesh(me)
    _bm.verts.ensure_lookup_table()
    bmesh.ops.delete(_bm, geom=[_bm.verts[i] for i in _small], context="VERTS")
    _bm.to_mesh(me)
    _bm.free()
    me.update()
rep["trimmed_vertices"]["scrap_islands"] = int(len(_small))
z_hem_rest = float(np.percentile(rest[(VROLE == "torso") & (loose_w > 0.5), 2], 2))
bvh_rest = BVHTree.FromPolygons([Vector(p_) for p_ in Brest], [tuple(q.vertices) for q in body.data.polygons])
_fh = (VROLE == "torso") & (loose_w > 0.5) & (np.abs(rest[:, 0] - x0_mh) < 0.06) & (rest[:, 1] < yc)
z_hem_front = float(np.percentile(rest[_fh, 2], 1))
# black on the thighs only from 3 cm above the skirt's front hem: below it the thigh is bare
under_v = (torso_b & (Brest[:, 2] < topf(Brest))) | (thigh_b & (Brest[:, 2] > z_hem_front + 0.03))
rep["hem_front_rest_z"] = round(z_hem_front, 3)


def add_part(name, verts, faces, mi, wname, fuv=None):
    m_ = bpy.data.meshes.new(name)
    m_.from_pydata([tuple(v) for v in verts], [], faces)
    m_.update()
    o = bpy.data.objects.new(name, m_)
    bpy.context.scene.collection.objects.link(o)
    for mt in (mat, m_skin, m_gold):
        m_.materials.append(mt)
    lay = m_.uv_layers.new(name=uvname)
    for p_ in m_.polygons:
        for li in p_.loop_indices:
            lay.data[li].uv = fuv[p_.index] if fuv else STOCK_UV
        p_.material_index = mi
        p_.use_smooth = True
    if isinstance(wname, dict):
        for bn_, wv in wname.items():
            o.vertex_groups.new(name=bn_).add(list(range(len(verts))), wv, "REPLACE")
    else:                                                      # one {bone: weight} per vertex
        for vi, wd in enumerate(wname):
            for bn_, wv in wd.items():
                (o.vertex_groups.get(bn_) or o.vertex_groups.new(name=bn_)).add([vi], float(wv), "REPLACE")
    return o


def uv_sphere(c, r, seg=16, rng=10, squash=1.0):
    vs, fs = [], []
    for i in range(rng + 1):
        th = math.pi * i / rng
        for j in range(seg):
            ph = 2 * math.pi * j / seg
            vs.append(tuple(np.array(c) + r * np.array([math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), squash * math.cos(th)])))
    for i in range(rng):
        for j in range(seg):
            a_, b_ = i * seg + j, i * seg + (j + 1) % seg
            fs.append((a_, b_, b_ + seg, a_ + seg))
    return vs, fs


def body_w(i_):
    return {bones[j]: float(BW[i_, j]) for j in np.nonzero(BW[i_] > 0.01)[0]}


def body_copy(name):
    o = body.copy()
    o.data = body.data.copy()
    o.name = o.data.name = name
    bpy.context.scene.collection.objects.link(o)
    for md_ in list(o.modifiers):
        o.modifiers.remove(md_)
    o.data.materials.clear()
    for mt in (mat, m_skin, m_gold):
        o.data.materials.append(mt)
    if o.data.uv_layers:
        o.data.uv_layers[0].name = uvname
    for p_ in o.data.polygons:
        p_.use_smooth = True
    return o


ul = body_copy("underlayer")
bm = bmesh.new()
bm.from_mesh(ul.data)
bm.verts.ensure_lookup_table()
# torso faces that touch the zone are kept and their vertices above the line slid down onto it, along the body
under_f = [f for f in bm.faces if all(under_v[v.index] for v in f.verts) or (any(under_v[v.index] for v in f.verts) and (all(torso_b[v.index] for v in f.verts) or all(thigh_b[v.index] for v in f.verts)))]
under_set = {f.index for f in under_f}
# faces wholly inside the zone; the border faces are slid here and stay, unslid, in the skin patch (without them the
# strip between the line and the old face edges was a row of holes: a staircase, seen in the second build)
under_strict = {f.index for f in under_f if all(under_v[v.index] for v in f.verts)}
MWbi = MWb.inverted()
slide = {v for f in under_f for v in f.verts if not under_v[v.index]}
tz = np.where(thigh_b, z_hem_front + 0.03, topf(Brest))
for v in slide:
    w_ = Brest[v.index].copy()
    w_[2] = tz[v.index]
    hit = bvh_rest.find_nearest(Vector(w_), 0.08)
    if hit[0] is not None:
        v.co = MWbi @ hit[0]
for v in bm.verts:
    v.co += (inv3 @ Vector(Bn[v.index])) * 0.0025
orig_i = {v: v.index for v in bm.verts}
bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.index not in under_set], context="FACES")
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
# Piping along the corset's top line: a black roll with a neon line over it, on the slid border of the underlayer. It
# covers the trimmed costume's ragged triangles (seen in the check renders) and gives the top edge the concept's line.
pip_v, pip_f, pip_w, pip_uv, pmap = [], [], [], [], {}
zup = np.array([0.0, 0.0, 1.0])
for e in bm.edges:
    if len(e.link_faces) != 1 or not all((v in slide) and torso_b[orig_i[v]] for v in e.verts):
        continue
    ids = []
    for v in e.verts:
        if v not in pmap:
            pmap[v] = len(pip_v)
            pw = np.array(MWb @ v.co)
            nn = Bn[orig_i[v]]
            for dn_, dz_ in ((0.0050, -0.0055), (0.0098, -0.0015), (0.0100, 0.0030), (0.0092, 0.0058)):
                pip_v.append(tuple(pw + nn * dn_ + zup * dz_))
                pip_w.append(body_w(orig_i[v]))
        ids.append(pmap[v])
    a_, b_ = ids
    for r_ in range(3):
        pip_f.append((a_ + r_, b_ + r_, b_ + r_ + 1, a_ + r_ + 1))
        pip_uv.append(NEON_UV if r_ == 2 else STOCK_UV)
bm.to_mesh(ul.data)
bm.free()
for l_ in ul.data.uv_layers[0].data:
    l_.uv = STOCK_UV
for p_ in ul.data.polygons:
    p_.material_index = 0
rep["underlayer_faces"] = len(ul.data.polygons)
rep["piping_faces"] = len(pip_f)
parts = [ul]
# two bands on each upper arm, cut from the body's own faces, edges smoothed along the surface
jr = {n: np.array(A @ arm.data.bones[n].head_local) for n in ("upperarm_l", "lowerarm_l", "upperarm_r", "lowerarm_r")}
st_o = body_copy("straps")
bm = bmesh.new()
bm.from_mesh(st_o.data)
bm.verts.ensure_lookup_table()
band_v = np.zeros(len(Brest), bool)
for sfx in ("l", "r"):
    A_, B_ = jr["upperarm_" + sfx], jr["lowerarm_" + sfx]
    d_ = B_ - A_
    al = ((Brest - A_) @ d_) / float(d_ @ d_)
    ua = np.array([("upperarm" in n) and n.endswith("_" + sfx) for n in dom])
    for lo_, hi_ in ((0.355, 0.455), (0.53, 0.61)):
        band_v |= ua & (al > lo_) & (al < hi_)
bmesh.ops.delete(bm, geom=[f for f in bm.faces if not all(band_v[v.index] for v in f.verts)], context="FACES")
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
bnb = {}
for e in bm.edges:
    if len(e.link_faces) == 1:
        a_, b_ = e.verts
        bnb.setdefault(a_, []).append(b_)
        bnb.setdefault(b_, []).append(a_)
for it in range(14):
    new_ = {}
    for v, nb_ in bnb.items():
        m_ = sum((n_.co for n_ in nb_), Vector()) / len(nb_)
        hit = bvh_rest.find_nearest(MWb @ (v.co * 0.5 + m_ * 0.5), 0.05)
        if hit[0] is not None:
            new_[v] = MWbi @ hit[0]
    for v, c_ in new_.items():
        v.co = c_
bm.normal_update()
for v in bm.verts:
    v.co += (inv3 @ (MWb3 @ v.normal).normalized()) * 0.0045
bm.to_mesh(st_o.data)
bm.free()
for l_ in st_o.data.uv_layers[0].data:
    l_.uv = STOCK_UV
for p_ in st_o.data.polygons:
    p_.material_index = 0
rep["strap_faces"] = len(st_o.data.polygons)
parts.append(st_o)
if pip_f:
    parts.append(add_part("piping", pip_v, pip_f, 0, pip_w, pip_uv))


def ring_band(name, c, axis, rows, bvh_, na=64, neon_rows=()):
    """A band round a limb: for na directions round `axis` at `c` and every row (distance along the axis, standoff),
    a ray from the axis finds the skin. Weights come from the nearest body vertex."""
    axis = axis / np.linalg.norm(axis)
    f_ = np.array([0.0, -1.0, 0.0])
    f_ = f_ - axis * (f_ @ axis)
    f_ /= np.linalg.norm(f_)
    s_ = np.cross(axis, f_)
    R_ = np.zeros((len(rows), na))
    for ri, (t_, _) in enumerate(rows):
        for k_ in range(na):
            dv = math.cos(2 * math.pi * k_ / na) * f_ + math.sin(2 * math.pi * k_ / na) * s_
            hit = bvh_.ray_cast(Vector(c + axis * t_), Vector(dv), 0.25)
            R_[ri, k_] = hit[3] if hit[0] is not None else np.nan
        row = R_[ri]
        row[np.isnan(row)] = np.nanmedian(row)
        R_[ri] = (np.roll(row, 1) + 2 * row + np.roll(row, -1)) / 4
    vs, fs, uvs, ws = [], [], [], []
    for k_ in range(na):
        dv = math.cos(2 * math.pi * k_ / na) * f_ + math.sin(2 * math.pi * k_ / na) * s_
        for ri, (t_, off_) in enumerate(rows):
            pt = c + axis * t_ + dv * (R_[ri, k_] + off_)
            vs.append(tuple(pt))
            ws.append(body_w(int(np.argmin(((Brest - (c + axis * t_ + dv * R_[ri, k_])) ** 2).sum(1)))))
    nr_ = len(rows)
    for k_ in range(na):
        for ri in range(nr_ - 1):
            a_, b_ = k_ * nr_ + ri, ((k_ + 1) % na) * nr_ + ri
            fs.append((a_, a_ + 1, b_ + 1, b_))
            uvs.append(NEON_UV if ri in neon_rows else STOCK_UV)
    return add_part(name, vs, fs, 0, ws, uvs)


# boot cuffs: a black band over the trimmed boot top, a neon line on its upper edge
for sfx in (("l", "r") if BOOT_TOP > 0 else ()):
    kn, u_ = KNEE[sfx]
    parts.append(ring_band("boot_cuff_" + sfx, kn + u_ * BOOT_TOP, u_, [(-0.016, 0.0070), (-0.014, 0.0125), (0.006, 0.0125), (0.0105, 0.0118), (0.0125, 0.0075)], bvh_rest, 64, neon_rows=(2,)))
# the skin the built body lacks, minus what the underlayer covers; two rings reach under the built body
built_p = os.environ.get("BUILT_FBX", "")
built_obj = None
if built_p:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(Path(built_p).resolve()))
    bo = [o for o in bpy.data.objects if o not in before]
    bmo = max((o for o in bo if o.type == "MESH"), key=lambda o: len(o.data.vertices))
    bpy.context.view_layer.update()
    bt = BVHTree.FromPolygons([bmo.matrix_world @ v.co for v in bmo.data.vertices], [tuple(q.vertices) for q in bmo.data.polygons])
    sp = body_copy("skin_patch")
    sb = bmesh.new()
    sb.from_mesh(sp.data)
    sb.faces.ensure_lookup_table()
    # ALL the skin the character shows is carried by this mesh, in one piece: every face of the complete body except
    # what lies wholly under the black underlayer and the legs below the knee (calves, feet). The MetaHuman's own Body
    # component is hidden in Unreal. Reasons, seen in Unreal on 2026-11-14: the body's calves came through the boots'
    # shins and its bare feet stood out of the shoes; hiding bones on the Body hides them on this mesh too (a
    # leader-pose follower takes the leader's hidden bones); and the seams between built body and patch are gone.
    low_leg = np.array([any(k_ in n for k_ in ("calf", "foot", "ball", "toe")) for n in bones])
    wl = BW[:, low_leg].sum(1)
    unc = {f for f in sb.faces if f.index not in under_strict and not all(wl[v.index] > 0.5 for v in f.verts)}
    keep_p = set(unc)
    rep["skin_patch_faces"] = len(unc)
    bmesh.ops.delete(sb, geom=[f for f in sb.faces if f not in keep_p], context="FACES")
    bmesh.ops.delete(sb, geom=[v for v in sb.verts if not v.link_faces], context="VERTS")
    sb.to_mesh(sp.data)
    sb.free()
    for p_ in sp.data.polygons:
        p_.material_index = 1
    # the built body stays in the scene for the check renders (forearms, lower thighs: skin this mesh does not carry);
    # its calves and feet are hidden there as they are in Unreal
    built_obj = None                                           # not shown: its skin is in the costume mesh now
    bmo.hide_render = True
    for md_ in list(bmo.modifiers):
        bmo.modifiers.remove(md_)
    _mwb = bmo.matrix_world.copy()
    bmo.parent = None
    bmo.matrix_world = _mwb
    _gb = {g_.index: g_.name for g_ in bmo.vertex_groups}
    _bb = bmesh.new()
    _bb.from_mesh(bmo.data)
    _dl = _bb.verts.layers.deform.verify()
    _kill = [v for v in _bb.verts if sum(w_ for gi_, w_ in v[_dl].items() if any(k_ in _gb[gi_] for k_ in ("calf", "foot", "ball", "toe"))) > 0.5]
    bmesh.ops.delete(_bb, geom=_kill, context="VERTS")
    _bb.to_mesh(bmo.data)
    _bb.free()
    bmo.data.materials.clear()
    bmo.data.materials.append(m_skin)
    for p_ in bmo.data.polygons:
        p_.use_smooth = True
    for o in bo:
        if o is not bmo:
            bpy.data.objects.remove(o)
    parts.append(sp)


# Choker (owner 2026-11-14: it must sit on the neck, not float as a flat disc). The band is laid on the neck's own
# surface: for 72 directions round the neck's axis (neck_01 to head, so the band tilts with the neck) and six heights,
# a ray from the axis finds the skin, and the band follows it at 1 to 3 mm, thicker in the middle. Its two edges are
# neon lines, as in the concept. A small gold ring hangs from the front and holds the bell.
head_p = os.environ.get("HEAD_FBX", "")
head_obj = None
if head_p:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(Path(head_p).resolve()))
    ho = [o for o in bpy.data.objects if o not in before]
    hm = max((o for o in ho if o.type == "MESH"), key=lambda o: len(o.data.vertices))
    bpy.context.view_layer.update()
    for md_ in list(hm.modifiers):
        hm.modifiers.remove(md_)
    _mw = hm.matrix_world.copy()
    hm.parent = None
    hm.matrix_world = Matrix.Identity(4)
    hm.data.transform(_mw)
    for o in ho:
        if o is not hm:
            bpy.data.objects.remove(o)
    head_obj = hm
    hb = BVHTree.FromPolygons([v.co.copy() for v in hm.data.vertices], [tuple(q.vertices) for q in hm.data.polygons])
    n0, n1 = joint_rest["neck_01"], joint_rest["head"]
    nax = (n1 - n0) / np.linalg.norm(n1 - n0)
    cc = n0 + nax * float(os.environ.get("CHOKER_T", 0.004))          # -0.028 lay on the collarbones (radius up to 9.8 cm)        # along the neck's axis from neck_01; negative is toward the chest
    fr = np.array([0.0, -1.0, 0.0])
    fr = fr - nax * (fr @ nax)
    fr /= np.linalg.norm(fr)
    sd = np.cross(nax, fr)
    NA, HH = 72, float(os.environ.get("CHOKER_H", 0.0105))
    rows = [(HH, 0.0010), (HH - 0.0018, 0.0022), (HH - 0.0042, 0.0030), (-HH + 0.0042, 0.0030), (-HH + 0.0018, 0.0022), (-HH, 0.0010)]
    R = np.zeros((len(rows), NA))
    for ri, (t_, _) in enumerate(rows):
        for k_ in range(NA):
            ang = 2 * math.pi * k_ / NA
            dv = math.cos(ang) * fr + math.sin(ang) * sd
            hit = hb.ray_cast(Vector(cc + nax * t_), Vector(dv), 0.2)
            R[ri, k_] = hit[3] if hit[0] is not None else np.nan
        row = R[ri]
        row[np.isnan(row)] = np.nanmedian(row)
        row[:] = np.minimum(row, 1.22 * np.nanmedian(row))
        R[ri] = (np.roll(row, 1) + 2 * row + np.roll(row, -1)) / 4
    cv, cf, cuv = [], [], []
    for k_ in range(NA):
        ang = 2 * math.pi * k_ / NA
        dv = math.cos(ang) * fr + math.sin(ang) * sd
        for ri, (t_, off_) in enumerate(rows):
            cv.append(tuple(cc + nax * t_ + dv * (R[ri, k_] + off_)))
    nr = len(rows)
    for k_ in range(NA):
        for ri in range(nr - 1):
            a_, b_ = k_ * nr + ri, ((k_ + 1) % NA) * nr + ri
            cf.append((a_, a_ + 1, b_ + 1, b_))
            cuv.append(NEON_UV if ri in (0, nr - 2) else STOCK_UV)
    parts.append(add_part("choker", cv, cf, 0, {"neck_01": 0.5, "neck_02": 0.5}, cuv))
    fpt = cc + nax * (-HH) + fr * (R[-1, 0] + 0.0015)                # front, lower edge
    RB = float(os.environ.get("BELL_R", 0.0125))
    ring_c = fpt + fr * 0.002 - nax * 0.004
    tv_, tf_ = [], []
    TS, TT_, RR, rr = 14, 8, 0.0045, 0.0011
    for i in range(TS):
        a1 = 2 * math.pi * i / TS
        for j in range(TT_):
            a2 = 2 * math.pi * j / TT_
            rad = RR + rr * math.cos(a2)
            tv_.append(tuple(ring_c + sd * (rad * math.cos(a1)) - nax * (rad * math.sin(a1)) + fr * (rr * math.sin(a2))))
    for i in range(TS):
        for j in range(TT_):
            a_, b_ = i * TT_ + j, ((i + 1) % TS) * TT_ + j
            tf_.append((a_, b_, ((i + 1) % TS) * TT_ + (j + 1) % TT_, i * TT_ + (j + 1) % TT_))
    parts.append(add_part("bell_ring", tv_, tf_, 2, {"neck_01": 1.0}))
    bell_c = ring_c - nax * (RR + RB * 0.92) + fr * 0.003
    bv, bf = uv_sphere(bell_c, RB, 18, 12)
    parts.append(add_part("bell", bv, bf, 2, {"neck_01": 1.0}))
    sv_, sf_ = uv_sphere(bell_c - np.array([0, 0, RB * 0.55]) + fr * RB * 0.62, RB * 0.33, 10, 6, 0.45)      # the dark slot at the bell's front
    parts.append(add_part("bell_slot", sv_, sf_, 0, {"neck_01": 1.0}))
    rep["choker"] = {"centre": [round(float(x), 3) for x in cc], "radius_cm": [round(float(np.nanmin(R)) * 100, 1), round(float(np.nanmax(R)) * 100, 1)], "height_cm": round(HH * 200, 1)}
bpy.ops.object.select_all(action="DESELECT")
for o in parts + [dr]:
    o.select_set(True)
bpy.context.view_layer.objects.active = dr
bpy.ops.object.join()
me = dr.data
dr.name = me.name = "yuki_costume"
dr.parent = arm
dr.matrix_parent_inverse = arm.matrix_world.inverted()
mod = dr.modifiers.new("Armature", "ARMATURE")
mod.object = arm
if "is_hair" in me.attributes:
    m_hair = mat.copy()
    m_hair.name = "yuki_tripo_hair"
    me.materials.append(m_hair)
    _hi = len(me.materials) - 1
    _hv_ = np.zeros(len(me.polygons), dtype=bool)
    me.attributes["is_hair"].data.foreach_get("value", _hv_)
    _mi = np.zeros(len(me.polygons), dtype=np.int32)
    me.polygons.foreach_get("material_index", _mi)
    _mi[_hv_] = _hi
    me.polygons.foreach_set("material_index", _mi)
    me.update()
    rep["hair_faces_final"] = int(_hv_.sum())
rep["final"] = {"vertices": len(me.vertices), "faces": len(me.polygons), "materials": [m_.name for m_ in me.materials],
                "shoe_sole_under_bare_sole_m": round(sole_mh - float(co(me)[:, 2].min()), 3)}
# check render: the finished costume with its skin, the body hidden
m_skin.use_nodes = True
next(n for n in m_skin.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"].default_value = (0.86, 0.66, 0.60, 1)
m_gold.use_nodes = True
next(n for n in m_gold.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"].default_value = (0.83, 0.62, 0.18, 1)
body.hide_render = True
_b = next((n_ for n_ in mat.node_tree.nodes if n_.type == "BSDF_PRINCIPLED"), None)
if _b is not None and "Emission Strength" in _b.inputs:        # the neon lines live in the emissive texture
    _b.inputs["Emission Strength"].default_value = float(os.environ.get("CHECK_EMIT", 5.0))
    rep["check_emission_linked"] = bool(_b.inputs["Emission Color"].is_linked) if "Emission Color" in _b.inputs else None
if head_obj is not None:                                      # the head and neck, so the choker is seen where it sits
    head_obj.data.materials.clear()
    head_obj.data.materials.append(m_skin)
    for p_ in head_obj.data.polygons:
        p_.use_smooth = True
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.5, 0.5, 0.52, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 1.0
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
sun.data.energy = 3
sun.rotation_euler = (math.radians(60), 0, math.radians(-20))
scene.collection.objects.link(sun)
H = 2 * 0.90
cam.data.ortho_scale = 1.78
shots("final")
# the same in the pose P: the proportions the character has in Unreal with the proportion layer. The meshes are
# skinned here with the matrices of P (Blender's bones cannot hold a scale that children take along their own axis).
def skin_to_P(obj):
    m_ = obj.data
    Wv = np.array([obj.matrix_world @ v.co for v in m_.vertices])
    gn_ = {g_.index: g_.name for g_ in obj.vertex_groups}
    acc = np.zeros((len(Wv), 3))
    wsum = np.zeros(len(Wv))
    cols = {}
    for v in m_.vertices:
        for g_ in v.groups:
            nm_ = gn_[g_.group]
            if nm_ in MSK and g_.weight > 1e-5:
                cols.setdefault(nm_, ([], []))
                cols[nm_][0].append(v.index)
                cols[nm_][1].append(g_.weight)
    Wh = np.c_[Wv, np.ones(len(Wv))]
    for nm_, (ii, ww) in cols.items():
        ii, ww = np.array(ii), np.array(ww)
        acc[ii] += ww[:, None] * (Wh[ii] @ MSK[nm_].T)[:, :3]
        wsum[ii] += ww
    Pn = np.where(wsum[:, None] > 1e-6, acc / np.maximum(wsum[:, None], 1e-9), Wv)
    inv_ = obj.matrix_world.inverted()
    for md_ in list(obj.modifiers):
        obj.modifiers.remove(md_)
    for v in m_.vertices:
        v.co = inv_ @ Vector(Pn[v.index])
    m_.update()


_keep_rest = co(me).copy()
skin_to_P(dr)
if built_obj is not None:
    skin_to_P(built_obj)
shots("finalP")
me.vertices.foreach_set("co", _keep_rest.ravel())            # back to the rest pose for the export
me.update()
_m = dr.modifiers.new("Armature", "ARMATURE")
_m.object = arm
for img_ in bpy.data.images:
    if img_.size[0] and any(img_.name.lower().startswith(k_) for k_ in ("base", "neon", "normalgl", "orm")):
        nm = "base" if img_.name.lower().startswith("base") else "emissive" if img_.name.lower().startswith("neon") else "normal" if img_.name.lower().startswith("normal") else "orm"
        img_.filepath_raw = str(out / f"yuki_costume_{nm}.png")
        img_.file_format = "PNG"
        img_.save()
bpy.ops.object.select_all(action="DESELECT")
arm.select_set(True)
dr.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.fbx(filepath=str(out / "yuki_costume.fbx"), use_selection=True, object_types={"ARMATURE", "MESH"}, add_leaf_bones=False, bake_anim=False,
                         mesh_smooth_type="FACE", path_mode="STRIP", embed_textures=False)
(out / "costume_report.json").write_text(json.dumps(rep, indent=1, default=float))
print("DONE", json.dumps({k_: rep[k_] for k_ in ("underlayer_faces", "final") if k_ in rep}), rep.get("skin_patch_faces"), rep.get("choker"), flush=True)

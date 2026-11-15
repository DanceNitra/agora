"""Prepare Yuki's Tripo body (bald, near bare, already cleaned by clean_body) as the BODY target of a MetaHuman conform.

    ./blender_headless.sh yuki_body_prep.py -- <yuki_bare.fbx> <mh_head.fbx> <mh_fullbody.fbx> <out_dir>

The character's head is already conformed (MHC_Yuki_v5, crown to chin 21.5 cm). The Tripo body is scaled so that its
own head has the same crown-to-chin height and moved so that its chin lies on the MetaHuman head's chin. The body
then has the Tripo figure's proportions at the size the head asks for. Chin on the midline profile, as in
yuki_bald_prep: below the nose, the lowest point within 25 % of the head depth of the face front.
Writes yuki_body_target.fbx (centimetres, textures beside it are not needed), body_prep.json and a front and side
check render: the target (grey) with the present MetaHuman body (red wire) over it."""
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

bare_p, head_p, mh_p = (str(Path(a).resolve()) for a in sys.argv[-4:-1])
out = Path(sys.argv[-1]).resolve()
out.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)


def load(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    m = max((o for o in new if o.type == "MESH"), key=lambda o: len(o.data.vertices))
    for md in list(m.modifiers):
        m.modifiers.remove(md)
    bpy.context.view_layer.update()
    mw = m.matrix_world.copy()
    m.parent = None
    m.matrix_world = Matrix.Identity(4)
    m.data.transform(mw)
    for o in new:
        if o is not m:
            bpy.data.objects.remove(o)
    return m


def pts(o):
    return np.array([v.co[:] for v in o.data.vertices])


def chin_crown(P, top_share):
    """P faces -Y. top_share: the part of the height, from the crown down, that holds the head."""
    crown = float(P[:, 2].max())
    span = top_share * float(np.ptp(P[:, 2]))
    head = P[P[:, 2] > crown - span]
    x0 = float(np.median(head[head[:, 2] > crown - 0.3 * span, 0]))
    mid = head[np.abs(head[:, 0] - x0) < 0.006]
    zs = np.linspace(crown, crown - span, 300)
    step = span / 300
    front = np.array([mid[np.abs(mid[:, 2] - z) < step, 1].min() if (np.abs(mid[:, 2] - z) < step).any() else np.nan for z in zs])
    upper = zs > crown - 0.75 * 0.215 / (0.215 / (span * 0.6)) if False else zs > crown - 0.6 * span
    nose_i = int(np.nanargmin(np.where(upper, front, np.nan)))
    depth = float(np.ptp(head[head[:, 2] > zs[nose_i], 1]))
    chin_i = nose_i
    for i in range(nose_i, len(zs)):
        if np.isnan(front[i]):
            continue
        if front[i] - front[nose_i] > 0.25 * depth:
            break
        chin_i = i
    return crown, float(zs[chin_i]), float(front[chin_i]), x0, float(zs[nose_i]), depth


def skull(P):
    """Width, depth and centre of the skull: the band 4 to 12 cm under the crown (both heads are bald)."""
    crown = float(P[:, 2].max())
    q = P[(P[:, 2] < crown - 0.04) & (P[:, 2] > crown - 0.12)]
    q = q[np.abs(q[:, 0] - np.median(q[:, 0])) < 0.12]
    return crown, float(np.ptp(q[:, 0])), float(np.ptp(q[:, 1])), float((q[:, 0].max() + q[:, 0].min()) / 2), float((q[:, 1].max() + q[:, 1].min()) / 2)


bare = load(bare_p)
B = pts(bare)
if np.ptp(B[:, 0]) < np.ptp(B[:, 1]):
    bare.data.transform(Matrix.Rotation(-math.pi / 2, 4, "Z"))
    B = pts(bare)
h_b = float(np.ptp(B[:, 2]))
head = load(head_p)
H = pts(head)
# The chin finder of yuki_bald_prep read 17 cm on this body's small stylised face (10.3 heads tall: wrong). Both heads
# are bald, so the scale comes from the skull: width and depth of the band 4 to 12 cm under the crown, twice (the band
# is set in metres, so the second pass measures the body at its new size).
s = 1.0
for _ in range(3):
    cb, wb, db, xb, yb = skull(B * s)
    ch, wh, dh, xh, yh = skull(H)
    s *= math.sqrt((wh / wb) * (dh / db))
cb, wb, db, xb, yb = skull(B * s)
M = Matrix.Translation(Vector((xh - xb, yh - yb, ch - cb))) @ Matrix.Scale(s, 4)
bare.data.transform(M)
B = pts(bare)
mh = load(mh_p)
Mh = pts(mh)
crown_h = ch
rep = {"bare_height_m": round(h_b, 3), "skull_width_depth_bare_scaled_m": [round(wb, 4), round(db, 4)], "skull_width_depth_mh_m": [round(wh, 4), round(dh, 4)], "scale": round(s, 4),
       "target_height_m": round(float(np.ptp(B[:, 2])), 3), "target_sole_z": round(float(B[:, 2].min()), 4), "target_crown_z": round(float(B[:, 2].max()), 4),
       "mh_body_now_sole_z": round(float(Mh[:, 2].min()), 4), "mh_now_height_m": round(crown_h - float(Mh[:, 2].min()), 3),
       "vertices": len(B), "faces": len(bare.data.polygons)}
bare.name = bare.data.name = "yuki_body_target"
bpy.ops.object.select_all(action="DESELECT")
bare.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(out / "yuki_body_target.fbx"), use_selection=True, object_types={"MESH"}, apply_scale_options="FBX_SCALE_UNITS",
                         mesh_smooth_type="FACE", path_mode="STRIP", embed_textures=False, add_leaf_bones=False)
(out / "body_prep.json").write_text(json.dumps(rep, indent=1))
print("BODYPREP", json.dumps(rep), flush=True)

scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "OBJECT"
scene.render.resolution_x, scene.render.resolution_y = 700, 1300
world = bpy.data.worlds.new("w")
world.color = (0.55, 0.55, 0.55)
scene.world = world
bare.color = (0.75, 0.75, 0.78, 1)
mh.color = (0.9, 0.15, 0.15, 1)
head.color = (0.9, 0.15, 0.15, 1)
for o in (mh, head):
    md = o.modifiers.new("w", "WIREFRAME")
    md.thickness = 0.0015
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
cam.data.type = "ORTHO"
lo, hi = min(B[:, 2].min(), Mh[:, 2].min()), max(B[:, 2].max(), crown_h)
cam.data.ortho_scale = (hi - lo) * 1.06  # soles are not aligned here: the built body stands on z = 0
scene.collection.objects.link(cam)
scene.camera = cam
for name, yaw in (("front", 0), ("side", 90)):
    a = math.radians(yaw)
    cam.location = (3 * math.sin(a), -3 * math.cos(a), (hi + lo) / 2)
    cam.rotation_euler = (math.pi / 2, 0, a)
    scene.render.filepath = str(out / f"check_{name}.png")
    bpy.ops.render.render(write_still=True)

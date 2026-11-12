"""blender -b --factory-startup --python costume_measure.py -- <bare_clean.fbx> <dressed.glb>
Step 1 of the costume transfer: put the dressed Tripo mesh on the bare Tripo mesh (both T-pose) and print
landmark differences, so the alignment is measured before any weights are transferred."""
import math
import sys
import bpy
import numpy as np
from mathutils import Matrix

bare_p, glb_p = sys.argv[-2], sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)


def load(path):
    before = set(bpy.data.objects)
    (bpy.ops.import_scene.fbx if path.lower().endswith(".fbx") else bpy.ops.import_scene.gltf)(filepath=path)
    o = next(x for x in set(bpy.data.objects) - before if x.type == "MESH")
    P = np.array([o.matrix_world @ v.co for v in o.data.vertices])
    if np.ptp(P[:, 1]) > np.ptp(P[:, 0]):  # arm span on Y: turn to face -Y like clean_body.py
        R = np.array(Matrix.Rotation(-math.pi / 2, 3, "Z"))
        P = P @ R.T
    P[:, 0] -= (P[:, 0].max() + P[:, 0].min()) / 2
    P[:, 1] -= (P[:, 1].max() + P[:, 1].min()) / 2
    P[:, 2] -= P[:, 2].min()
    return P


def marks(P, tag):
    m = {"height": P[:, 2].max(), "span": np.ptp(P[:, 0]), "depth": np.ptp(P[:, 1])}
    # arm centreline: z centre of slabs along +X
    for f in (0.35, 0.5, 0.65, 0.8):
        x = f * P[:, 0].max()
        s = P[(P[:, 0] > x - 0.01) & (P[:, 0] < x + 0.01)]
        m[f"arm_z@{f}"] = (s[:, 2].max() + s[:, 2].min()) / 2
        m[f"arm_thick@{f}"] = np.ptp(s[:, 2])
    # crotch: lowest z where the slice at x~0 has vertices (between the legs it is empty below the crotch)
    mid = P[(np.abs(P[:, 0]) < 0.012) & (P[:, 2] < 0.6 * m["height"])]
    m["crotch_z"] = mid[:, 2].min()
    # armpit: lowest z of the surface in a slab just outside the torso
    for z in (0.3, 0.5, 0.62, 0.7):
        s = P[(np.abs(P[:, 2] - z * m["height"]) < 0.01) & (np.abs(P[:, 0]) < 0.3 * m["span"] / 2 + 0.2)]
        m[f"width@{z}"] = np.ptp(s[:, 0])
    s = P[(np.abs(P[:, 2] - 0.02) < 0.02)]
    m["feet_width"] = np.ptp(s[:, 0])
    print(tag, {k: round(float(v), 3) for k, v in m.items()})
    return m


B = load(bare_p)
D = load(glb_p)
mb, md = marks(B, "bare   "), marks(D, "dressed")
s = mb["span"] / md["span"]
D2 = D * s
D2[:, 2] += mb["arm_z@0.5"] - (md["arm_z@0.5"] * s)
print("scale", round(s, 4), "z shift", round(mb["arm_z@0.5"] - md["arm_z@0.5"] * s, 4))
D2z = D2.copy(); D2z[:, 2] -= 0  # marks() re-floors nothing, so compare raw values
m2 = {"top": D2[:, 2].max(), "bottom": D2[:, 2].min()}
mid = D2[(np.abs(D2[:, 0]) < 0.012) & (D2[:, 2] < 1.0)]
m2["crotch_z"] = mid[:, 2].min()
for f in (0.35, 0.65, 0.8):
    x = f * D2[:, 0].max(); sl = D2[(D2[:, 0] > x - 0.01) & (D2[:, 0] < x + 0.01)]
    m2[f"arm_z@{f}"] = (sl[:, 2].max() + sl[:, 2].min()) / 2
print("dressed aligned", {k: round(float(v), 3) for k, v in m2.items()})

"""Compares the dressed Tripo model of Yuki with her MetaHuman body: heights of landmarks and widths of slices.

    ./blender_headless.sh costume_probe_yuki.py -- <dressed.glb> <mh_fullbody.fbx> <head.fbx>

Both are stood facing -Y with the soles at z = 0. Prints torso width and depth per height (arms excluded by a
connected run from the midline), crotch height, shoulder joint height and the arm direction of each."""
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix

glb, mh_p, head_p = (str(Path(a).resolve()) for a in sys.argv[-3:])
bpy.ops.wm.read_factory_settings(use_empty=True)


def pts(o):
    return np.array([o.matrix_world @ v.co for v in o.data.vertices])


bpy.ops.import_scene.gltf(filepath=glb)
dr = max((o for o in bpy.data.objects if o.type == "MESH"), key=lambda o: len(o.data.vertices))
D = pts(dr)
print("DRESSED raw bounds", D.min(0).round(3).tolist(), D.max(0).round(3).tolist(), "faces", len(dr.data.polygons), "materials", [m.name for m in dr.data.materials],
      "images", [(i.name, tuple(i.size)) for i in bpy.data.images if i.size[0]], flush=True)
if np.ptp(D[:, 0]) < np.ptp(D[:, 1]):             # arms along Y: turn them onto X
    D = D @ np.array(Matrix.Rotation(-math.pi / 2, 3, "Z")).T
D = D - np.array([(D[:, 0].max() + D[:, 0].min()) / 2, 0, D[:, 2].min()])
# front is where the toes are: the feet's centre of mass lies in front of the ankles
feet = D[D[:, 2] < 0.05]
legs = D[(D[:, 2] > 0.3) & (D[:, 2] < 0.5)]
if feet[:, 1].mean() > legs[:, 1].mean():
    D = D * np.array([-1, -1, 1])
D[:, 1] -= legs[:, 1].mean() if feet[:, 1].mean() <= legs[:, 1].mean() else -legs[:, 1].mean()
before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=mh_p)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and o not in before)
body = max((o for o in bpy.data.objects if o.type == "MESH" and o not in before), key=lambda o: len(o.data.vertices))
bpy.context.view_layer.update()
B = pts(body)
J = lambda n: np.array(arm.matrix_world @ arm.data.bones[n].head_local)
before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=head_p)
hm = max((o for o in bpy.data.objects if o.type == "MESH" and o not in before), key=lambda o: len(o.data.vertices))
bpy.context.view_layer.update()
H = pts(hm)
print("MH body bounds", B.min(0).round(3).tolist(), B.max(0).round(3).tolist(), "head top", round(float(H[:, 2].max()), 3), flush=True)
print("MH joints", {n: J(n).round(3).tolist() for n in ("pelvis", "thigh_l", "calf_l", "foot_l", "ball_l", "spine_05", "neck_01", "head", "clavicle_l", "upperarm_l", "lowerarm_l", "hand_l")}, flush=True)
z0 = B[:, 2].min()
B = B - np.array([J("pelvis")[0], J("pelvis")[1], z0])
mh_h, dr_h = float(H[:, 2].max() - z0), float(D[:, 2].max())
print("HEIGHT mh (sole to crown)", round(mh_h, 3), "dressed (sole to ear tips)", round(dr_h, 3), flush=True)


def torso(P, z, dz=0.008):
    q = P[np.abs(P[:, 2] - z) < dz]
    if len(q) < 10:
        return None
    xs = np.sort(q[:, 0])
    # connected run through x = 0 (gaps over 2.5 cm end it: arms and hands are separate)
    c = xs[np.argmin(np.abs(xs))]
    if abs(c) > 0.03:
        return None
    lo = hi = c
    for x in xs[xs >= c]:
        if x - hi > 0.025:
            break
        hi = x
    for x in xs[xs <= c][::-1]:
        if lo - x > 0.025:
            break
        lo = x
    m = (q[:, 0] >= lo) & (q[:, 0] <= hi)
    return hi - lo, float(np.ptp(q[m, 1])), float(q[m, 1].min()), float(q[m, 1].max())


def crotch(P):
    mid = P[(np.abs(P[:, 0]) < 0.012) & (P[:, 2] > 0.3 * P[:, 2].max()) & (P[:, 2] < 0.62 * P[:, 2].max())]
    return float(mid[:, 2].min())


def legs_gap(P, z):
    q = P[np.abs(P[:, 2] - z) < 0.008]
    xs = np.sort(q[q[:, 0] > 0, 0])
    return [round(float(xs.min()), 3), round(float(xs.max()), 3)] if len(xs) else None


print("CROTCH z mh", round(crotch(B), 3), "dressed (under the skirt)", round(crotch(D), 3), flush=True)
print("   z_mh  | mh width depth | z_dr  | dressed width depth   (same share of the height)")
for f in np.arange(0.40, 0.90, 0.025):
    a, b = torso(B, f * mh_h), torso(D, f * dr_h)
    print("  %.3f | %s | %.3f | %s" % (f * mh_h, ("%.3f %.3f" % a[:2]) if a else "  -  ", f * dr_h, ("%.3f %.3f" % b[:2]) if b else "  -  "), flush=True)
for f in (0.10, 0.20, 0.30, 0.38):
    print("LEG x range at share", f, "mh", legs_gap(B, f * mh_h), "dressed", legs_gap(D, f * dr_h), flush=True)
for nm, P in (("mh", B), ("dressed", D)):
    top = P[:, 2].max() if nm == "dressed" else mh_h
    a = P[(P[:, 0] > 0.22)]
    c = a.mean(0)
    d = np.linalg.svd(a - c)[2][0]
    d = d * np.sign(d[0])
    print("ARM", nm, "direction", d.round(3).tolist(), "tip x", round(float(P[:, 0].max()), 3), "tip z", round(float(P[np.argmax(P[:, 0]), 2]), 3), flush=True)

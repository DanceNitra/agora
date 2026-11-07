"""Runs inside Unreal (ue_py.py) after ue_retarget_setup.py. Auto-align leaves the spine line, neck and head off
Manny's. Measured 2026-11-07: the idle head hung 45 degrees forward of the neck against Manny's 23, and the spine
(pelvis to neck) stood 4-6 degrees more upright than Manny's in idle and jog. In the TARGET retarget pose this
aims spine_01 so spine_01-to-neck_01 points where Manny's does, then aims neck_01 so neck-to-head matches, and gives
Head an offset that keeps its reference world orientation (face level)."""
import unreal, math

E = unreal.AnimPoseExtensions
T = unreal.RetargetSourceOrTarget.TARGET
WS, LS = unreal.AnimPoseSpaces.WORLD, unreal.AnimPoseSpaces.LOCAL
rtg = unreal.load_asset("/Game/AgoraChar/Retarget/RTG_Manny_to_AgoraChar")
rc = unreal.IKRetargeterController.get_controller(rtg)
ref = E.get_reference_pose(unreal.load_asset("/Game/AgoraChar/AF2/SK_AgoraChar").get_editor_property("skeleton"))
mref = E.get_reference_pose(unreal.load_asset("/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple").get_editor_property("skeleton"))
L = lambda b: E.get_bone_pose(ref, b, LS).rotation
CHAIN = ["root", "pelvis", "spine_01", "spine_02", "spine_03", "neck_01"]


def world(chain):
    w = unreal.Quat(0, 0, 0, 1)
    for b in chain:
        w = w * (L(b) * rc.get_rotation_offset_for_retarget_pose_bone(b, T))
    return w


def unit(v):
    n = math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z)
    return unreal.Vector(v.x / n, v.y / n, v.z / n)


def between(a, b):
    a, b = unit(a), unit(b)
    c = unreal.Vector(a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x)
    ang = math.acos(max(-1.0, min(1.0, a.x * b.x + a.y * b.y + a.z * b.z)))
    if ang < 1e-6:
        return unreal.Quat(0, 0, 0, 1)
    c, s = unit(c), math.sin(ang / 2)
    return unreal.Quat(c.x * s, c.y * s, c.z * s, math.cos(ang / 2))


def seg_deg(v):
    return round(math.degrees(math.atan2(v.y, v.z)), 1)


chk = unreal.Quat(0, 0, 0, 1)
for b in CHAIN:
    chk = chk * L(b)
print("chain check (deg off):", round(math.degrees(chk.angular_distance(E.get_bone_pose(ref, "neck_01", WS).rotation)), 3))

def fk(chain):
    """world rotation and position of the last bone in chain, retarget pose"""
    w, pos = unreal.Quat(0, 0, 0, 1), unreal.Vector(0, 0, 0)
    for b in chain:
        t = E.get_bone_pose(ref, b, LS).translation
        r = w.rotate_vector(t)
        pos = unreal.Vector(pos.x + r.x, pos.y + r.y, pos.z + r.z)
        w = w * (L(b) * rc.get_rotation_offset_for_retarget_pose_bone(b, T))
    return w, pos


def mvec(a, b):
    x, y = E.get_bone_pose(mref, a, WS).translation, E.get_bone_pose(mref, b, WS).translation
    return unreal.Vector(y.x - x.x, y.y - x.y, y.z - x.z)


for b in ("neck_01", "Head"):
    rc.set_rotation_offset_for_retarget_pose_bone(b, unreal.Quat(0, 0, 0, 1), T)
# spine: rotate spine_01 (on top of its auto-align offset) so spine_01 -> neck_01 matches Manny
w1, p1 = fk(CHAIN[:3])
_, pn = fk(CHAIN)
cur_sp = unreal.Vector(pn.x - p1.x, pn.y - p1.y, pn.z - p1.z)
want_sp = mvec("spine_01", "neck_01")
new_w1 = between(cur_sp, want_sp) * w1
d_sp = L("spine_01").inversed() * fk(CHAIN[:2])[0].inversed() * new_w1
rc.set_rotation_offset_for_retarget_pose_bone("spine_01", d_sp, T)
w1, p1 = fk(CHAIN[:3])
_, pn = fk(CHAIN)
print("spine_01->neck_01 forward lean: ours before", seg_deg(cur_sp), "Manny", seg_deg(want_sp), "ours after", seg_deg(unreal.Vector(pn.x - p1.x, pn.y - p1.y, pn.z - p1.z)))
wneck = world(CHAIN)
cur = wneck.rotate_vector(E.get_bone_pose(ref, "Head", LS).translation)
m0, m1 = E.get_bone_pose(mref, "neck_01", WS).translation, E.get_bone_pose(mref, "head", WS).translation
want_dir = unreal.Vector(m1.x - m0.x, m1.y - m0.y, m1.z - m0.z)
new_neck = between(cur, want_dir) * wneck
wparent = world(CHAIN[:-1])
d_neck = L("neck_01").inversed() * wparent.inversed() * new_neck
rc.set_rotation_offset_for_retarget_pose_bone("neck_01", d_neck, T)
after = world(CHAIN).rotate_vector(E.get_bone_pose(ref, "Head", LS).translation)
print("neck->head forward lean: ours before", seg_deg(cur), "Manny", seg_deg(want_dir), "ours after", seg_deg(after))
want_head = E.get_bone_pose(ref, "Head", WS).rotation
d_head = L("Head").inversed() * world(CHAIN).inversed() * want_head
rc.set_rotation_offset_for_retarget_pose_bone("Head", d_head, T)
got = world(CHAIN + ["Head"])
print("Head off its reference orientation (deg):", round(math.degrees(got.angular_distance(want_head)), 3))
unreal.EditorAssetLibrary.save_loaded_asset(rtg)

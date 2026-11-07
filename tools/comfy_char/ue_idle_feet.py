"""Runs inside Unreal (ue_py.py). Epic's MM_Idle stands with the right foot turned 47 degrees out and the left one
straight (measured 2026-11-07: toe yaw 137 and 96, forward is 90). Copied onto our boots, the owner read it as a
broken foot. This turns the whole right leg about the vertical through the hip, every frame, so the right toes point
TARGET_OUT degrees out. The knee follows, so the ankle does not twist; sole tilt and heights are unchanged.
Then (owner, same day: "vedla seba") the right foot is moved forward beside the left, STAGGER cm behind it, by a
two-bone IK on thigh and calf each frame; the foot keeps its world orientation (flat sole, toes as set above).
A backup of the clip is kept as MM_Idle_Agora_EpicStance."""
import math
import unreal

CLIP = "/Game/AgoraChar/Retarget/Anims6/MM_Idle_Agora"
BACKUP = CLIP + "_EpicStance"
TARGET_OUT = 10.0
STAGGER = 5.0
E = unreal.AnimPoseExtensions
W, L = unreal.AnimPoseSpaces.WORLD, unreal.AnimPoseSpaces.LOCAL
lib = unreal.EditorAssetLibrary
if not lib.does_asset_exist(BACKUP):
    lib.duplicate_asset(CLIP, BACKUP)
src = lib.load_asset(BACKUP)       # always start from the untouched Epic stance
dst = lib.load_asset(CLIP)
opts = unreal.AnimPoseEvaluationOptions()
n = unreal.AnimationLibrary.get_num_frames(src) + 1


def toe_yaw(p, s):
    f, b = E.get_bone_pose(p, f"foot_{s}", W).translation, E.get_bone_pose(p, f"ball_{s}", W).translation
    return math.degrees(math.atan2(b.y - f.y, b.x - f.x))


p0 = E.get_anim_pose_at_frame(src, 0, opts)
turn = (90.0 + TARGET_OUT) - toe_yaw(p0, "r")   # right foot: outward is yaw above 90
print("right toe yaw", round(toe_yaw(p0, "r"), 1), "left", round(toe_yaw(p0, "l"), 1), "turn right leg by", round(turn, 1))
rz = unreal.Rotator(0, 0, turn).quaternion()
pos, rot, scl = [], [], []
for fr in range(n):
    p = E.get_anim_pose_at_frame(src, min(fr, n - 2), opts)
    parent_w = E.get_bone_pose(p, "pelvis", W).rotation
    thigh_w = E.get_bone_pose(p, "thigh_r", W).rotation
    loc = E.get_bone_pose(p, "thigh_r", L)
    pos.append(loc.translation)
    rot.append(parent_w.inversed() * rz * thigh_w)
    scl.append(loc.scale3d)
ctrl = dst.get_editor_property("controller")
ctrl.open_bracket(unreal.Text("idle right leg"), False)
ok = ctrl.set_bone_track_keys("thigh_r", pos, rot, scl, False)
ctrl.close_bracket(False)
lib.save_loaded_asset(dst, only_if_is_dirty=False)


def sub(a, b): return unreal.Vector(a.x - b.x, a.y - b.y, a.z - b.z)
def add(a, b): return unreal.Vector(a.x + b.x, a.y + b.y, a.z + b.z)
def mul(a, k): return unreal.Vector(a.x * k, a.y * k, a.z * k)
def dot(a, b): return a.x * b.x + a.y * b.y + a.z * b.z
def unit(a): return mul(a, 1.0 / math.sqrt(dot(a, a)))
def cross(a, b): return unreal.Vector(a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x)


def between(a, b):
    a, b = unit(a), unit(b)
    ang = math.acos(max(-1.0, min(1.0, dot(a, b))))
    if ang < 1e-6:
        return unreal.Quat(0, 0, 0, 1)
    c, s_ = unit(cross(a, b)), math.sin(ang / 2)
    return unreal.Quat(c.x * s_, c.y * s_, c.z * s_, math.cos(ang / 2))


# step 2: two-bone IK, right foot beside the left
src2 = lib.load_asset(CLIP)
tr = {"thigh_r": ([], [], []), "calf_r": ([], [], []), "foot_r": ([], [], [])}
worst_reach = 0.0
for fr in range(n):
    p = E.get_anim_pose_at_frame(src2, min(fr, n - 2), opts)
    g = lambda b: E.get_bone_pose(p, b, W)
    H, K, A = g("thigh_r").translation, g("calf_r").translation, g("foot_r").translation
    Tgt = unreal.Vector(A.x, g("foot_l").translation.y - STAGGER, A.z)
    la, lb = math.sqrt(dot(sub(K, H), sub(K, H))), math.sqrt(dot(sub(A, K), sub(A, K)))
    d = min(math.sqrt(dot(sub(Tgt, H), sub(Tgt, H))), la + lb - 0.5)
    worst_reach = max(worst_reach, d / (la + lb))
    u = unit(sub(Tgt, H))
    pole = sub(K, H)
    pole = unit(sub(pole, mul(u, dot(pole, u))))
    alpha = math.acos(max(-1.0, min(1.0, (la * la + d * d - lb * lb) / (2 * la * d))))
    Kn = add(H, add(mul(u, la * math.cos(alpha)), mul(pole, la * math.sin(alpha))))
    An = add(H, mul(u, d))
    r1 = between(sub(K, H), sub(Kn, H))
    thigh_w = r1 * g("thigh_r").rotation
    r2 = between(r1.rotate_vector(sub(A, K)), sub(An, Kn))
    calf_w = r2 * r1 * g("calf_r").rotation
    foot_w = g("foot_r").rotation
    locs = {"thigh_r": g("pelvis").rotation.inversed() * thigh_w, "calf_r": thigh_w.inversed() * calf_w, "foot_r": calf_w.inversed() * foot_w}
    for b in tr:
        lt = E.get_bone_pose(p, b, L)
        tr[b][0].append(lt.translation); tr[b][1].append(locs[b]); tr[b][2].append(lt.scale3d)
ctrl = dst.get_editor_property("controller")
ctrl.open_bracket(unreal.Text("idle feet side by side"), False)
for b, (ps, rs, ss) in tr.items():
    ctrl.set_bone_track_keys(b, ps, rs, ss, False)
ctrl.close_bracket(False)
lib.save_loaded_asset(dst, only_if_is_dirty=False)
print("leg reach used, worst frame:", round(worst_reach, 3))
p1 = E.get_anim_pose_at_frame(dst, 0, opts)
for b in ("foot_l", "foot_r"):
    t = E.get_bone_pose(p1, b, W).translation
    print(b, "after", round(t.x, 1), round(t.y, 1), round(t.z, 1))
print("keys", n, "ok", ok, "-> right toe yaw", round(toe_yaw(p1, "r"), 1), "left", round(toe_yaw(p1, "l"), 1),
      "right ankle z", round(E.get_bone_pose(p0, "foot_r", W).translation.z, 1), "->", round(E.get_bone_pose(p1, "foot_r", W).translation.z, 1))

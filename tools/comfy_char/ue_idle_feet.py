"""Runs inside Unreal (ue_py.py). Epic's MM_Idle stands with the right foot turned 47 degrees out and the left one
straight (measured 2026-11-07: toe yaw 137 and 96, forward is 90). Copied onto our boots, the owner read it as a
broken foot. This turns the whole right leg about the vertical through the hip, every frame, so the right toes point
TARGET_OUT degrees out. The knee follows, so the ankle does not twist; sole tilt and heights are unchanged.
A backup of the clip is kept as MM_Idle_Agora_EpicStance."""
import math
import unreal

CLIP = "/Game/AgoraChar/Retarget/Anims6/MM_Idle_Agora"
BACKUP = CLIP + "_EpicStance"
TARGET_OUT = 10.0
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
p1 = E.get_anim_pose_at_frame(dst, 0, opts)
print("keys", n, "ok", ok, "-> right toe yaw", round(toe_yaw(p1, "r"), 1), "left", round(toe_yaw(p1, "l"), 1),
      "right ankle z", round(E.get_bone_pose(p0, "foot_r", W).translation.z, 1), "->", round(E.get_bone_pose(p1, "foot_r", W).translation.z, 1))

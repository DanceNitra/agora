"""Runs inside Unreal. Builds an additive body AnimSequence that moves Yuki's head, neck and upper spine from a file of
per-frame yaw, pitch and roll in degrees (written by yuki_head_motion). It is layered over any body animation as a
second animation section in Sequencer (ARGS ADD of ue_yuki_dance_seq).

A wrapper sets ARGS = dict(JSON=<file>, DST=<asset path>, and optionally SIGNS=(yaw, pitch, roll) and FRAMES).
The rotation is given in component space (Z up; the MetaHuman faces +Y, so pitch turns about X and roll about Y) and
is shared between the bones by WEIGHTS. An additive track with the reference pose as base stores, per bone,
delta-in-parent-space times the bone's reference rotation; bones without a track add nothing."""
import json
import math

import unreal

_A = globals().pop("ARGS", {})
SIGNS = _A.get("SIGNS", (1.0, 1.0, 1.0))
WEIGHTS = (("spine_04", 0.08), ("spine_05", 0.12), ("neck_01", 0.20), ("neck_02", 0.20), ("head", 0.40))
PARENT = {"spine_04": "spine_03", "spine_05": "spine_04", "neck_01": "spine_05", "neck_02": "neck_01", "head": "neck_02"}
d = json.load(open(_A["JSON"]))
n = min(len(d["yaw"]), _A.get("FRAMES", 10 ** 9))
lib, tools = unreal.EditorAssetLibrary, unreal.AssetToolsHelpers.get_asset_tools()
idle = unreal.load_asset("/MetaHumanCharacter/Optional/Animation/UEFNAnimPreset/Locomotion/AS_MH_Neutral_Stand_Idle_Loop")
skel = idle.get_skeleton()
AP = unreal.AnimPoseExtensions
pose = AP.get_anim_pose_at_time(idle, 0.0, unreal.AnimPoseEvaluationOptions())


def q_mul(a, b):                       # Hamilton product, (x, y, z, w); q_mul(a, b) rotates by b first, then a
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx, aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz)


def q_inv(a):
    return (-a[0], -a[1], -a[2], a[3])


def q_axis(axis, deg):
    h = math.radians(deg) / 2
    s = math.sin(h)
    return (axis[0] * s, axis[1] * s, axis[2] * s, math.cos(h))


def tq(tr):
    r = tr.rotation
    return (r.x, r.y, r.z, r.w)


if lib.does_asset_exist(_A["DST"]):
    anim = unreal.load_asset(_A["DST"])
else:
    f = unreal.AnimSequenceFactory()
    f.set_editor_property("target_skeleton", skel)
    anim = tools.create_asset(_A["DST"].split("/")[-1], "/".join(_A["DST"].split("/")[:-1]), unreal.AnimSequence, f)
ctl = anim.controller
ctl.open_bracket(unreal.Text("Yuki head motion"), False)
try:
    ctl.set_frame_rate(unreal.FrameRate(30, 1), False)
    ctl.set_number_of_frames(unreal.FrameNumber(n - 1), False)
    ctl.remove_all_bone_tracks(False)
    jobs = [(bone, w, d) for bone, w in WEIGHTS] + [(bone, 1.0, ch) for bone, ch in d.get("extra", {}).items()]
    for bone, w, src in jobs:
        ref_l = AP.get_ref_bone_pose(pose, bone, unreal.AnimPoseSpaces.LOCAL)
        parent = PARENT.get(bone) or str(unreal.AnimationLibrary.find_bone_path_to_root(idle, bone)[1])
        par_c = tq(AP.get_ref_bone_pose(pose, parent, unreal.AnimPoseSpaces.WORLD))
        base = tq(ref_l)
        pos, rot, scl = [], [], []
        for i in range(n):
            dc = q_mul(q_axis((0, 0, 1), SIGNS[0] * w * src["yaw"][i]), q_mul(q_axis((1, 0, 0), SIGNS[1] * w * src["pitch"][i]), q_axis((0, 1, 0), SIGNS[2] * w * src["roll"][i])))
            dp = q_mul(q_inv(par_c), q_mul(dc, par_c))                # the same turn, seen from the parent bone
            r = q_mul(dp, base)
            pos.append(ref_l.translation)
            rot.append(unreal.Quat(r[0], r[1], r[2], r[3]))
            scl.append(unreal.Vector(1, 1, 1))
        ctl.add_bone_curve(bone, False)
        ok = ctl.set_bone_track_keys(bone, pos, rot, scl, False)
        print("HEADANIM track", bone, w, "keys", len(rot), ok)
finally:
    ctl.close_bracket(False)
anim.set_editor_property("additive_anim_type", unreal.AdditiveAnimationType.AAT_LOCAL_SPACE_BASE)
anim.set_editor_property("ref_pose_type", unreal.AdditiveBasePoseType.ABPT_REF_POSE)
print("HEADANIM", anim.get_path_name(), "frames", unreal.AnimationLibrary.get_num_frames(anim), "length", round(anim.get_play_length(), 3),
      "additive", anim.is_valid_additive() if hasattr(anim, "is_valid_additive") else "?", "saved", lib.save_asset(_A["DST"], only_if_is_dirty=False))

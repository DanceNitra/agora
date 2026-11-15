"""Runs inside Unreal. Builds the animation that gives Yuki's MetaHuman body the Tripo model's proportions.

The costume cut from the Tripo model (yuki_costume_tripo) keeps the Tripo figure's shape; the skeleton takes its
proportions from a file written by that script: a scale along the bone's own axis (local X) for a few bones (spine
shorter, thighs and calves longer, arms shorter), with the reciprocal on the next joint where the stretch stops.
Bone scale is used because this skeleton ignores animated bone translations (translation retargeting).
This script writes the scales as a two-frame AnimSequence on the body skeleton, every listed bone at its reference
translation and rotation.

A wrapper sets ARGS = dict(JSON=<proportions file>, DST=<asset path>, ADDITIVE=<bool>). ADDITIVE marks the asset as
a local-space additive over the reference pose, for a layer over other body animation in Sequencer; without it the
asset is a plain pose (reference pose with the proportions), for stills."""
import json

import unreal

_A = globals().pop("ARGS", {})
d = json.load(open(_A["JSON"]))
DST = _A["DST"]
lib, tools = unreal.EditorAssetLibrary, unreal.AssetToolsHelpers.get_asset_tools()
idle = unreal.load_asset("/MetaHumanCharacter/Optional/Animation/UEFNAnimPreset/Locomotion/AS_MH_Neutral_Stand_Idle_Loop")
skel = idle.get_skeleton()
AP = unreal.AnimPoseExtensions
pose = AP.get_anim_pose_at_time(idle, 0.0, unreal.AnimPoseEvaluationOptions())
if lib.does_asset_exist(DST):
    anim = unreal.load_asset(DST)
else:
    f = unreal.AnimSequenceFactory()
    f.set_editor_property("target_skeleton", skel)
    anim = tools.create_asset(DST.split("/")[-1], "/".join(DST.split("/")[:-1]), unreal.AnimSequence, f)
ctl = anim.controller
N = 2
ctl.open_bracket(unreal.Text("Yuki proportions"), False)
done = []
try:
    ctl.set_frame_rate(unreal.FrameRate(30, 1), False)
    ctl.set_number_of_frames(unreal.FrameNumber(N - 1), False)
    ctl.remove_all_bone_tracks(False)
    for bone, sx in d["scale_x"].items():
        try:
            ref = AP.get_ref_bone_pose(pose, bone, unreal.AnimPoseSpaces.LOCAL)
        except Exception as e:
            print("PROP skip", bone, str(e)[:60])
            continue
        ctl.add_bone_curve(bone, False)
        ok = ctl.set_bone_track_keys(bone, [ref.translation] * N, [ref.rotation] * N, [unreal.Vector(float(sx), 1.0, 1.0)] * N, False)
        done.append((bone, round(float(sx), 3), ok))
finally:
    ctl.close_bracket(False)
if _A.get("ADDITIVE", False):
    anim.set_editor_property("additive_anim_type", unreal.AdditiveAnimationType.AAT_LOCAL_SPACE_BASE)
    anim.set_editor_property("ref_pose_type", unreal.AdditiveBasePoseType.ABPT_REF_POSE)
print("PROP", anim.get_path_name(), "bones", done, "actor raise m", round(d["actor_raise_m"], 3), "saved", lib.save_asset(DST, only_if_is_dirty=False))

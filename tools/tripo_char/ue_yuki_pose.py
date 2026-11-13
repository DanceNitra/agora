"""Runs inside Unreal. Gives Yuki's face a resting expression through the face rig, not through the mesh: a one-frame
AnimSequence that holds RigLogic control curves (CTRL_expressions_*), played on the Face component of the Yuki
character. The face mesh has a post-process AnimBP (ABP_Face_PostProcess) that turns those curves into joints, so
the neutral mesh stays neutral for lipsync and the smile is a pose that can be blended in and out.

A wrapper may set ARGS = dict(...) with POSE (dict: control name without the CTRL_expressions_ prefix, with L/R suffix written out, to a
value 0..1), ASSET (asset name) and PLAY (True: also play it on the play copy of Yuki; needs Play-in-Editor running;
the asset is then only read, not rewritten). Saves the animation asset by its path.
Control names read from /MetaHumanCharacter/Face/ARKit/AS_MetaHuman_ARKit_Mapping (2026-11-13)."""
import unreal

# Wrapper values arrive in one dict, ARGS, which is taken out of the globals before anything else runs. The editor's
# Python keeps its globals between runs: single variables set by a wrapper became the defaults of later runs, also
# when a run failed half way (2026-11-13: a close-up's FOV, an old iris scale and PIE=True leaked that way).
_A = globals().pop("ARGS", {})

POSE = _A.get("POSE", {
    "mouthCornerPullL": 0.45, "mouthCornerPullR": 0.45, "mouthDimpleL": 0.15, "mouthDimpleR": 0.15,
    "eyeCheekRaiseL": 0.30, "eyeCheekRaiseR": 0.30, "eyeBlinkL": 0.22, "eyeBlinkR": 0.22,
    "eyeSquintInnerL": 0.15, "eyeSquintInnerR": 0.15})
ASSET = _A.get("ASSET", "A_Yuki_Face_Smile")
PLAY = _A.get("PLAY", False)
PKG = "/Game/AgoraChar/Tripo/Yuki/Anim"
lib = unreal.EditorAssetLibrary
al = unreal.AnimationLibrary
path = f"{PKG}/{ASSET}"
skel = unreal.load_asset("/MetaHumanCharacter/Face/Face_Archetype_Skeleton")
anim = unreal.load_asset(path)       # EditorAssetLibrary answers "does not exist" while Play-in-Editor runs
if anim is None:
    if PLAY:
        raise RuntimeError(path + " does not exist; write it before starting Play-in-Editor")
    f = unreal.AnimSequenceFactory()
    f.set_editor_property("target_skeleton", skel)
    anim = unreal.AssetToolsHelpers.get_asset_tools().create_asset(ASSET, PKG, unreal.AnimSequence, f)
    c = anim.controller
    c.set_frame_rate(unreal.FrameRate(30, 1), False)
    c.set_number_of_frames(unreal.FrameNumber(1), False)
if not PLAY:
    al.remove_all_curve_data(anim)
for k, v in ({} if PLAY else POSE).items():
    n = "CTRL_expressions_" + k
    al.add_curve(anim, n, unreal.RawCurveTrackTypes.RCT_FLOAT, False)
    al.add_float_curve_keys(anim, n, [0.0, anim.get_play_length()], [float(v), float(v)])
print("POSE asset", path, "curves", len(al.get_animation_curve_names(anim, unreal.RawCurveTrackTypes.RCT_FLOAT)), "length", round(anim.get_play_length(), 3),
      "saved", PLAY or lib.save_asset(path, only_if_is_dirty=False))
if PLAY:
    # Play copy only (Play-in-Editor must be running). In the editor world the face does not evaluate animation:
    # "update animation in editor" cannot be set from Python on this component, and editing its properties re-runs the
    # Blueprint construction, which resets the animation mode (2026-11-13).
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    if w is None:
        raise RuntimeError("PLAY needs a running Play-in-Editor session")
    n = 0
    for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor):
        if "MHC_Yuki" in a.get_class().get_name():
            for c in a.get_components_by_class(unreal.SkeletalMeshComponent):
                c.set_forced_lod(1)
                if c.get_name() == "Face":
                    c.play_animation(anim, True)
                    n += 1
    print("POSE playing on", n, "face component(s)")

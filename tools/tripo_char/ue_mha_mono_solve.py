"""Runs inside Unreal (tools/comfy_char/ue_py.py). MetaHuman Animator solve of a single-camera performance video
onto Yuki: ingest the video (Capture Manager, blocking), create a MetaHuman Performance on that footage with input
type MONO_FOOTAGE, process it blocking, and export the face animation (CTRL_expressions curves and head movement)
for the face skeleton Yuki's face animations use. Follows Epic's monocular processing and export examples in
the MetaHumanAnimator plugin's Content/Python folder (UE 5.9).

Two exports: A_<NAME>_face (with the solve's head curves) and A_<NAME>_face_nohead (for a body-driven head).
A wrapper sets ARGS = dict(VIDEO=<absolute path to .mp4/.mov>, NAME=<short asset name>, FACE_REF=<an existing face
AnimSequence whose skeleton is the export target>). Saves only the assets it creates, by path."""
import unreal

_A = globals().pop("ARGS", {})
VIDEO, NAME = _A["VIDEO"], _A["NAME"]
FACE_REF = _A.get("FACE_REF", "/Game/AgoraChar/Tripo/Yuki/Lipsync/AS_Puzzle_e5_face")
PKG = "/Game/AgoraChar/Tripo/Yuki/MHA"
lib = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()

perf_path = f"{PKG}/{NAME}_Performance"
anim_path = f"{PKG}/A_{NAME}_face"
for p_ in (perf_path, anim_path):
    if lib.does_asset_exist(p_):
        raise RuntimeError(p_ + " exists; pick a new NAME")

# 1. Ingest. The blocking call returns the capture data asset; the error text comes back as a second value.
params = unreal.CaptureManagerConversionParams()
res = unreal.CaptureManagerIngestBlueprintLibrary.ingest_mono_video_sync(VIDEO, "", NAME, 1, params)
footage, err = (res if isinstance(res, tuple) else (res, ""))
if not footage:
    raise RuntimeError("ingest failed: " + str(err))
print("INGEST", footage.get_path_name(), "error:", err)

# 2. Performance on the footage, mono input, processed on the main thread until done.
perf = tools.create_asset(asset_name=f"{NAME}_Performance", package_path=PKG, asset_class=unreal.MetaHumanPerformance,
                          factory=unreal.MetaHumanPerformanceFactoryNew())
perf.set_editor_property("input_type", unreal.DataInputType.MONO_FOOTAGE)
perf.set_editor_property("footage_capture_data", footage)
perf.set_blocking_processing(True)
status = perf.start_pipeline()
print("PIPELINE", status)
if status != unreal.StartPipelineErrorType.NONE:
    raise RuntimeError("pipeline did not start: " + str(status))

# 3. Export to the skeleton of Yuki's existing face animation, with head movement.
ref = unreal.load_asset(FACE_REF)
skel = ref.get_editor_property("skeleton")
s = unreal.MetaHumanPerformanceExportAnimationSettings()
s.show_export_dialog = False
s.package_path = PKG
s.asset_name = f"A_{NAME}_face"
s.target_skeleton_or_skeletal_mesh = skel
s.enable_head_movement = True
s.export_range = unreal.PerformanceExportRange.PROCESSING_RANGE
anim = unreal.MetaHumanPerformanceExportUtils.export_animation_sequence(perf, s)
if not anim:
    raise RuntimeError("export returned nothing")
curves = unreal.AnimationLibrary.get_animation_curve_names(anim, unreal.RawCurveTrackTypes.RCT_FLOAT)
n = unreal.AnimationLibrary.get_num_frames(anim)
rate = anim.get_play_length()
print("ANIM", anim.get_path_name(), "frames", n, "length s", rate, "curves", len(curves), "skeleton", skel.get_path_name())
# The same performance without head movement: the head turn goes on the BODY (ue_yuki_head_additive with
# perf_head_angles), because the solve's head curves turn the face mesh alone and leave the body, the costume and its
# ears behind (owner's screenshot, 2026-11-15).
s.asset_name = f"A_{NAME}_face_nohead"
s.enable_head_movement = False
anim2 = unreal.MetaHumanPerformanceExportUtils.export_animation_sequence(perf, s)
print("ANIM_NOHEAD", anim2.get_path_name() if anim2 else None)
for p_ in (footage.get_path_name().split(".")[0], perf_path, anim.get_path_name().split(".")[0],
           anim2.get_path_name().split(".")[0] if anim2 else None):
    if p_:
        print("SAVE", p_, lib.save_asset(p_, only_if_is_dirty=False))

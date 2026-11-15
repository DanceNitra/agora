"""Runs inside Unreal with L_Yuki_Preview open. Builds a level sequence and a Movie Render Queue config that render
Yuki dancing: a body animation on the Body component, the smile pose on the Face component, a camera, and a per-frame
height track on the actor that puts her feet on the floor.

Why the height track: the dance performances were baked for another MetaHuman (Depesa). They play on Yuki's skeleton
as they are, but the pelvis height is absolute, and on Yuki the lower foot hangs 12 to 25 cm above the floor
(measured). Each frame the actor is lowered by what the lower foot (ankle or ball, against its rest height) is above
the floor, smoothed over SMOOTH frames.

A wrapper sets ARGS = dict(ANIM=<asset name in /Game/Companions/Dance/Perf, or a full asset path>, TAG=<name>, OUT=<folder for the PNG
frames>, and optionally FACE, SMOOTH, FOCAL, CAM_Y, CAM_Z, RES=(w, h), TSAMPLES). Saves the sequence, the config and
the level (the camera actor Yuki_DanceCam stays in it)."""
import unreal

_A = globals().pop("ARGS", {})
ANIM, TAG, OUT = _A["ANIM"], _A["TAG"], _A["OUT"]
FACE = _A.get("FACE", "/Game/AgoraChar/Tripo/Yuki/Anim/A_Yuki_Face_Smile")
RANGE = _A.get("RANGE", None)   # (first, last) frame to render; the level's start pose follows it
SMOOTH, FOCAL, CAM_Y, CAM_Z = _A.get("SMOOTH", 5), _A.get("FOCAL", 66.0), _A.get("CAM_Y", 700.0), _A.get("CAM_Z", 68.0)
RES, TS = _A.get("RES", (1080, 1920)), _A.get("TSAMPLES", 4)
PKG = "/Game/AgoraChar/Tripo/Yuki/Anim"
lib = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
acts = {a.get_actor_label(): a for a in eas.get_all_level_actors()}
# The rest heights are read from the body in its reference pose. Once the level's character holds a dance's first pose
# (set at the end of this file), the sockets and bounds describe that pose, and the floor reference came out 3 cm off
# (2026-11-14). So the body is put back on "animation blueprint" (none: the reference pose) before measuring.
_b = next(c for c in acts["Yuki_Character"].get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == "Body")
if _b.get_editor_property("animation_mode") != unreal.AnimationMode.ANIMATION_BLUEPRINT:
    _b.set_editor_property("animation_mode", unreal.AnimationMode.ANIMATION_BLUEPRINT)
    acts = {a.get_actor_label(): a for a in eas.get_all_level_actors()}
ch = acts["Yuki_Character"]
comps = {c.get_name(): c for c in ch.get_components_by_class(unreal.SkeletalMeshComponent)}
body, face = comps["Body"], comps["Face"]
anim = unreal.load_asset(ANIM if ANIM.startswith("/") else "/Game/Companions/Dance/Perf/" + ANIM)   # a full path, or a name in the dance folder
fanim = unreal.load_asset(FACE)
# The body clip may be shorter than the shot (an idle loop under a song): its section loops in the sequence, and the
# heights below are sampled with the clip's time wrapped the same way.
N = max(unreal.AnimationLibrary.get_num_frames(anim), (RANGE[1] if RANGE else 0))

# heights: rest values from the body standing in its reference pose in the level, then the lower foot per frame
rest = {b: body.get_socket_location(b).z - ch.get_actor_location().z for b in ("foot_l", "foot_r", "ball_l", "ball_r")}
AP = unreal.AnimPoseExtensions
opt = unreal.AnimPoseEvaluationOptions()
opt.set_editor_property("optional_skeletal_mesh", body.get_skeletal_mesh_asset())
raw = []
L = anim.get_play_length()
for f in range(N + 1):
    p = AP.get_anim_pose_at_time(anim, min((f / 30.0) % L if N > unreal.AnimationLibrary.get_num_frames(anim) else f / 30.0, L - 1e-3), opt)
    raw.append(min(AP.get_bone_pose(p, b, unreal.AnimPoseSpaces.WORLD).translation.z - rest[b] for b in rest))
# Yuki's soles are not at the actor origin: the head-only conform put her head at the target's height and the shorter
# preset body hangs below it, so the lowest point of the body mesh is about 21 cm above the origin, and the floor of
# the preview level is a plane 5 cm below it (measured 2026-11-13). BASE takes both out.
Z_OFF = _A.get("Z_OFF", 0.0)    # cm added to the actor's height: the proportion layer makes the legs longer and the shoes have heels
bo, be, _r = unreal.SystemLibrary.get_component_bounds(body)
fo, fe = acts["Yuki_Floor"].get_actor_bounds(False)
BASE = (fo.z + fe.z) - (bo.z - be.z - ch.get_actor_location().z) - 0.6   # relative to the actor; 0.6 cm: the bounds sit a little under the mesh
zs = []
for f in range(len(raw)):
    w = raw[max(0, f - SMOOTH // 2):f + SMOOTH // 2 + 1]
    zs.append(BASE + Z_OFF - sum(w) / len(w))
print("DSEQ base offset", round(BASE, 1), "actor z range", round(min(zs), 1), round(max(zs), 1))
print("DSEQ rest heights", {k: round(v, 1) for k, v in rest.items()}, "lift above floor before: min %.1f max %.1f cm" % (min(raw), max(raw)),
      "frames", N)

cam = acts.get("Yuki_DanceCam")
if cam is None:
    cam = eas.spawn_actor_from_class(unreal.CineCameraActor, unreal.Vector(0, CAM_Y, CAM_Z), unreal.Rotator(roll=0, pitch=0, yaw=-90))
    cam.set_actor_label("Yuki_DanceCam")
cam.set_actor_location_and_rotation(unreal.Vector(0, CAM_Y, CAM_Z), unreal.Rotator(roll=0, pitch=0, yaw=-90), False, True)
cc = cam.get_cine_camera_component()
fb = cc.get_editor_property("filmback")
fb.set_editor_property("sensor_width", 24.0 * RES[0] / RES[1])
fb.set_editor_property("sensor_height", 24.0)
cc.set_editor_property("filmback", fb)
cc.set_editor_property("current_focal_length", FOCAL)
cc.set_editor_property("current_aperture", 8.0)
fs = cc.get_editor_property("focus_settings")
fs.set_editor_property("focus_method", unreal.CameraFocusMethod.DISABLE)
cc.set_editor_property("focus_settings", fs)
pp = cc.get_editor_property("post_process_settings")
for k, v in (("auto_exposure_min_brightness", -0.8), ("auto_exposure_max_brightness", -0.8), ("auto_exposure_bias", 0.0)):   # EV100, as in ue_yuki_shot
    pp.set_editor_property("override_" + k, True)
    pp.set_editor_property(k, v)
cc.set_editor_property("post_process_settings", pp)

name = "LS_Yuki_Dance_" + TAG
path = f"{PKG}/{name}"
if lib.does_asset_exist(path):
    raise RuntimeError(path + " exists: use a new TAG (a loaded sequence cannot be deleted from Python without a dialog)")
seq = tools.create_asset(name, PKG, unreal.LevelSequence, unreal.LevelSequenceFactoryNew())
seq.set_display_rate(unreal.FrameRate(30, 1))
# PRE: frames of pre-roll before the first frame, held in the first frame's pose with every layer on. Movie Render
# Queue's own warm-up runs without the sequence's additive layers; with the proportion layer the body changed shape on
# frame 0 and the simulated hair flew for 20 frames (seen 2026-11-14). The pre-roll frames are rendered and dropped.
PRE = int(_A.get("PRE", 0))
seq.set_playback_start((RANGE[0] if RANGE else 0) - PRE)
seq.set_playback_end(RANGE[1] if RANGE else N)
ab = seq.add_possessable(ch)
tt = ab.add_track(unreal.MovieScene3DTransformTrack)
ts = tt.add_section()
ts.set_range(-PRE, N + 1)
chs = ts.get_all_channels()
loc, rot = ch.get_actor_location(), ch.get_actor_rotation()
for i, v in enumerate((loc.x, loc.y, loc.z, rot.roll, rot.pitch, rot.yaw, 1.0, 1.0, 1.0)):
    chs[i].set_default(v)
for f, z in enumerate(zs):
    chs[2].add_key(unreal.FrameNumber(f), z, 0.0, unreal.MovieSceneTimeUnit.DISPLAY_RATE)   # absolute: the floor is the reference
def _sections(track, asset, row):
    sec = track.add_section()
    sec.set_range(0, N + 1)
    sec.set_row_index(row)
    pr = sec.get_editor_property("params")
    pr.set_editor_property("animation", asset)
    sec.set_editor_property("params", pr)
    if PRE:                                  # the same clip, all but standing still on its first frame
        s0 = track.add_section()
        s0.set_range(-PRE, 0)
        s0.set_row_index(row)
        p0 = s0.get_editor_property("params")
        p0.set_editor_property("animation", asset)
        tw = p0.get_editor_property("play_rate")        # a MovieSceneTimeWarpVariant in 5.9, not a float
        tw.set_fixed_play_rate(0.0001)
        p0.set_editor_property("play_rate", tw)
        s0.set_editor_property("params", p0)


for comp, a_ in ((body, anim), (face, fanim)):
    cb = seq.add_possessable(comp)
    at = cb.add_track(unreal.MovieSceneSkeletalAnimationTrack)
    _sections(at, a_, 0)
    # ADD (ARGS): additive body animations (head and body motion from ue_yuki_head_additive, the proportion layer from
    # ue_yuki_proportions), each on its own row of the body track
    if comp is body and _A.get("ADD"):
        adds = _A["ADD"] if isinstance(_A["ADD"], (list, tuple)) else [_A["ADD"]]
        for row, ap in enumerate(adds, 1):
            _sections(at, unreal.load_asset(ap), row)
            print("SEQ additive section", row, ap.split("/")[-1])
cb = seq.add_possessable(cam)
cut = seq.add_track(unreal.MovieSceneCameraCutTrack)
cs = cut.add_section()
cs.set_range(-PRE, N + 1)
cs.set_camera_binding_id(seq.get_binding_id(cb))
# The level's own character starts in this dance's first pose at the first frame's height. Otherwise play begins in the
# reference pose 26 cm higher and the first frame is one big jump that throws the simulated hair over the face.
body.set_editor_property("animation_mode", unreal.AnimationMode.ANIMATION_SINGLE_NODE)
ch = next(a for a in eas.get_all_level_actors() if a.get_actor_label() == "Yuki_Character")
body = next(c for c in ch.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == "Body")
d_ = body.get_editor_property("animation_data")
d_.set_editor_property("anim_to_play", anim)
d_.set_editor_property("saved_position", ((RANGE[0] if RANGE else 0) / 30.0) % anim.get_play_length())
body.set_editor_property("animation_data", d_)
ch = next(a for a in eas.get_all_level_actors() if a.get_actor_label() == "Yuki_Character")
ch.set_actor_location(unreal.Vector(loc.x, loc.y, zs[RANGE[0] if RANGE else 0]), False, True)
print("DSEQ sequence", path, "bindings", [b.get_display_name() for b in seq.get_bindings()], "saved", lib.save_asset(path, only_if_is_dirty=False))

cname = "MRQ_Yuki_Dance_" + TAG
cpath = f"{PKG}/{cname}"
c = lib.load_asset(cpath) if lib.does_asset_exist(cpath) else tools.create_asset(cname, PKG, unreal.MoviePipelinePrimaryConfig, None)
o = c.find_or_add_setting_by_class(unreal.MoviePipelineOutputSetting)
o.output_directory = unreal.DirectoryPath(OUT)
o.output_resolution = unreal.IntPoint(RES[0], RES[1])
o.file_name_format = "{frame_number_rel}" if PRE else "{frame_number}"     # with pre-roll: 0000 is the first pre-roll frame
o.zero_pad_frame_numbers = 4
c.find_or_add_setting_by_class(unreal.MoviePipelineDeferredPassBase)
c.find_or_add_setting_by_class(unreal.MoviePipelineImageSequenceOutput_PNG)
aa = c.find_or_add_setting_by_class(unreal.MoviePipelineAntiAliasingSetting)
aa.spatial_sample_count = 1
aa.temporal_sample_count = TS
aa.engine_warm_up_count = 60
aa.use_camera_cut_for_warm_up = True
c.find_or_add_setting_by_class(unreal.MoviePipelineGameOverrideSetting)
print("DSEQ config", cpath, "saved", lib.save_asset(cpath, only_if_is_dirty=False), "level saved", lib.save_asset("/Game/AgoraChar/Tripo/Yuki/L_Yuki_Preview", only_if_is_dirty=False))

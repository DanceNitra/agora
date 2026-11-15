"""Runs inside Unreal. Makes a face animation for Yuki from an audio file with MetaHuman Animator's audio-driven
animation, the way Epic's example process_audio_performance does it: a SoundWave, a MetaHuman Performance with audio
as input, a blocking solve, and an AnimSequence of rig control curves on the face skeleton.

Feed it the vocals alone (a Demucs "vocals" stem of the song, same length as the song, so the animation shares the
song's clock). With the full mix the solver hears drums and bass as speech.

A wrapper sets ARGS = dict(WAV=<wav on disk>, TAG=<name>, and optionally MOOD ("Auto", "Neutral", "Happy", ...),
MOOD_INTENSITY, MASK ("FullFace" or "MouthOnly"), HEAD (bool: export head movement curves)).
Writes /Game/AgoraChar/Tripo/Yuki/Lipsync/S_<TAG>, MHP_<TAG>, AS_<TAG>_face and saves them."""
import time

import unreal

_A = globals().pop("ARGS", {})
WAV, TAG = _A["WAV"], _A["TAG"]
MOOD, MOOD_INTENSITY, MASK, HEAD = _A.get("MOOD", "Auto"), _A.get("MOOD_INTENSITY", 1.0), _A.get("MASK", "FullFace"), _A.get("HEAD", False)
PKG = "/Game/AgoraChar/Tripo/Yuki/Lipsync"
lib = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
it = unreal.AssetImportTask()
it.filename, it.destination_path, it.destination_name = WAV, PKG, "S_" + TAG
it.automated, it.replace_existing, it.save = True, True, True
tools.import_asset_tasks([it])
snd = unreal.load_asset(f"{PKG}/S_{TAG}")
print("LIPSYNC sound", snd.get_path_name(), "duration", round(snd.get_editor_property("duration"), 2))
ppath = f"{PKG}/MHP_{TAG}"
perf = unreal.load_asset(ppath) or tools.create_asset("MHP_" + TAG, PKG, unreal.MetaHumanPerformance, unreal.MetaHumanPerformanceFactoryNew())
perf.set_editor_property("input_type", unreal.DataInputType.AUDIO)
perf.set_editor_property("audio", snd)
ov = unreal.AudioDrivenAnimationSolveOverrides()
moods = {m.lower(): getattr(unreal.AudioDrivenAnimationMood, m) for m in dir(unreal.AudioDrivenAnimationMood) if m.isupper()}
key = {"auto": "auto_detect"}.get(MOOD.lower(), MOOD.lower())
if key not in moods:                      # the member names differ between engine versions: list them instead of guessing
    raise RuntimeError("mood %r not in %s" % (MOOD, sorted(moods)))
ov.mood = moods[key]
ov.mood_intensity = MOOD_INTENSITY
perf.set_editor_property("audio_driven_animation_solve_overrides", ov)
perf.set_editor_property("audio_driven_animation_output_controls", unreal.AudioDrivenAnimationOutputControls.FULL_FACE if MASK == "FullFace" else unreal.AudioDrivenAnimationOutputControls.MOUTH_ONLY)
perf.set_editor_property("head_movement_mode", unreal.PerformanceHeadMovementMode.CONTROL_RIG if HEAD else unreal.PerformanceHeadMovementMode.DISABLED)
perf.set_blocking_processing(True)
t0 = time.time()
err = perf.start_pipeline()
print("LIPSYNC solve", err, "seconds", round(time.time() - t0, 1))
es = unreal.MetaHumanPerformanceExportAnimationSettings()
es.show_export_dialog = False
es.package_path = PKG
es.asset_name = f"AS_{TAG}_face"
es.target_skeleton_or_skeletal_mesh = unreal.load_asset("/MetaHumanCharacter/Face/Face_Archetype_Skeleton")
es.enable_head_movement = HEAD
es.export_range = unreal.PerformanceExportRange.PROCESSING_RANGE
anim = unreal.MetaHumanPerformanceExportUtils.export_animation_sequence(perf, es)
al = unreal.AnimationLibrary
names = [str(n) for n in al.get_animation_curve_names(anim, unreal.RawCurveTrackTypes.RCT_FLOAT)] if anim else []
print("LIPSYNC anim", anim.get_path_name() if anim else None, "length", round(anim.get_play_length(), 3) if anim else None, "frames", al.get_num_frames(anim) if anim else None,
      "rate", anim.get_editor_property("target_frame_rate") if anim and hasattr(anim, "target_frame_rate") else "?", "curves", len(names))
for p in (ppath, f"{PKG}/AS_{TAG}_face"):
    print("LIPSYNC save", p.split("/")[-1], lib.save_asset(p, only_if_is_dirty=False))

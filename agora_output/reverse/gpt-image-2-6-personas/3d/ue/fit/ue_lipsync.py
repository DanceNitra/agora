# Runs INSIDE Unreal. Imports lipsync_cfg.json["wav"] as a SoundWave, builds a MetaHuman Performance with
# Audio input, solves it (blocking), and exports a face AnimSequence. All assets under /Game/Companions/Lipsync.
import json
import unreal

F = r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit"
cfg = json.load(open(F + r"\lipsync_cfg.json"))
DIR = "/Game/Companions/Lipsync"
name = cfg["name"]
tools = unreal.AssetToolsHelpers.get_asset_tools()
lib = unreal.EditorAssetLibrary

t = unreal.AssetImportTask()
t.set_editor_property("filename", cfg["wav"])
t.set_editor_property("destination_path", DIR)
t.set_editor_property("destination_name", "S_" + cfg.get("sound", name))
t.set_editor_property("automated", True)
t.set_editor_property("replace_existing", True)
t.set_editor_property("save", False)
tools.import_asset_tasks([t])
sw = lib.load_asset(DIR + "/S_" + cfg.get("sound", name))
print("SOUND", sw is not None, sw.get_editor_property("duration") if sw else None)

perf_path = DIR + "/MHP_" + name
perf = lib.load_asset(perf_path) if lib.does_asset_exist(perf_path) else \
    tools.create_asset("MHP_" + name, DIR, unreal.MetaHumanPerformance, unreal.MetaHumanPerformanceFactoryNew())
perf.set_editor_property("input_type", unreal.DataInputType.AUDIO)
perf.set_editor_property("audio", sw)
perf.set_editor_property("generate_blinks", True)
if cfg.get("mood"):
    ov = perf.get_editor_property("audio_driven_animation_solve_overrides")
    ov.set_editor_property("mood", getattr(unreal.AudioDrivenAnimationMood, cfg["mood"]))
    ov.set_editor_property("mood_intensity", float(cfg.get("mood_intensity", 0.8)))
    perf.set_editor_property("audio_driven_animation_solve_overrides", ov)
    print("MOOD", ov)
print("CAN", perf.can_process())
perf.set_blocking_processing(True)
perf.start_pipeline()
print("PROCESSED", perf.get_number_of_processed_frames(), "processing", perf.is_processing(),
      "issue", perf.diagnostics_indicates_processing_issue())
s = unreal.MetaHumanPerformanceExportAnimationSettings()
s.set_editor_property("asset_name", "AS_" + name)
s.set_editor_property("package_path", DIR) if "package_path" in str(type(s).__doc__) else None
s.set_editor_property("show_export_dialog", False) if "show_export_dialog" in str(type(s).__doc__) else None
s.set_editor_property("export_face", True)
s.set_editor_property("enable_head_movement", True)
anim = unreal.MetaHumanPerformanceExportUtils.export_animation_sequence(perf, s)
print("ANIM", anim.get_path_name() if anim else None)

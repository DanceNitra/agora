# Runs INSIDE Unreal: export the processed performance onto the MetaHuman face archetype skeleton.
import json
import unreal
F = r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit"
cfg = json.load(open(F + r"\lipsync_cfg.json"))
DIR = "/Game/Companions/Lipsync"
perf = unreal.EditorAssetLibrary.load_asset(DIR + "/MHP_" + cfg["name"])
s = unreal.MetaHumanPerformanceExportAnimationSettings()
s.set_editor_property("show_export_dialog", False)
s.set_editor_property("package_path", DIR)
s.set_editor_property("asset_name", "AS_" + cfg["name"] + "_face")
s.set_editor_property("export_face", True)
s.set_editor_property("export_body", False)
s.set_editor_property("enable_head_movement", True)
s.set_editor_property("auto_save_anim_sequence", False)
s.set_editor_property("target_skeleton_or_skeletal_mesh", unreal.EditorAssetLibrary.load_asset("/MetaHumanCharacter/Face/Face_Archetype_Skeleton"))
print("CANEXP", perf.can_export_animation(), "frames", perf.get_number_of_processed_frames())
a = unreal.MetaHumanPerformanceExportUtils.export_animation_sequence(perf, s)
print("ANIM", a.get_path_name() if a else None, "len", a.get_editor_property("sequence_length") if a else None)
names = [str(n) for n in unreal.AnimationLibrary.get_animation_curve_names(a, unreal.RawCurveTrackTypes.RCT_FLOAT)] if a else []
print("CURVES", len(names))
for n in names:
    if any(k in n for k in ("jawOpen", "Jaw_Open", "mouthFunnel", "LipsPurse", "eyeBlink", "EyeBlink")):
        t, v = unreal.AnimationLibrary.get_float_keys(a, n)
        if v:
            print("K", n, round(min(v), 3), round(max(v), 3), len(v))

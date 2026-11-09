# Runs INSIDE Unreal: open LS (seqframe_cfg.json) in Sequencer once, lock to its camera cut, go to a frame.
import json
import unreal
F = r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit"
cfg = json.load(open(F + r"\seqframe_cfg.json"))
L = unreal.LevelSequenceEditorBlueprintLibrary
if cfg.get("open"):
    seq = unreal.EditorAssetLibrary.load_asset(cfg["seq"])
    L.open_level_sequence(seq)
    L.set_lock_camera_cut_to_viewport(True)
L.set_current_time(int(cfg["frame"]))
print("FRAME", L.get_current_time())

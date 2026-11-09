# Runs INSIDE Unreal: select wardrobe items (wardrobe_cfg.json) in MH_Depesa's PREVIEW collection, propagate,
# and re-run the preview pipeline. The spawned actor follows the character.
import json
import unreal
F = r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit"
cfg = json.load(open(F + r"\wardrobe_cfg.json"))
mhs = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
ch = unreal.EditorAssetLibrary.load_asset("/Game/Companions/MetaHuman/MH_Depesa")
mhs.try_add_object_to_edit(ch) if not mhs.is_object_added_for_editing(ch) else None
col = mhs.get_preview_collection(ch)
inst = col.get_editor_property("default_instance")
for slot, path in cfg["items"].items():
    key = col.try_add_item_from_wardrobe_item(slot, unreal.EditorAssetLibrary.load_asset(path))
    inst.set_single_slot_selection(slot, key)
    print("SET", slot, path.split("/")[-1], key is not None)
mhs.on_edit_preview_collection(ch)
mhs.assemble_for_preview(ch)
for p in inst.get_instance_parameter_item_paths():
    for prm in inst.get_instance_parameters(p):
        print("PRM", str(prm)[:220])

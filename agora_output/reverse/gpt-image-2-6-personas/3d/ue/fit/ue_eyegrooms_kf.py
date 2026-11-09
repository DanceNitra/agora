# Runs INSIDE Unreal: on MH_DepesaKF set dense black eyelashes and dark full brows (preview collection), then save.
import unreal
lib = unreal.EditorAssetLibrary
mhs = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
ch = lib.load_asset("/Game/Companions/MetaHuman/MH_DepesaKF")
mhs.try_add_object_to_edit(ch) if not mhs.is_object_added_for_editing(ch) else None
col = mhs.get_preview_collection(ch)
inst = col.get_editor_property("default_instance")
B = "/MetaHumanCharacter/Optional/Grooms/Bindings/"
ITEMS = {"Eyelashes": B + "Eyelashes/WI_Eyelashes_L_ThickCurl", "Eyebrows": B + "Eyebrows/WI_Eyebrows_M_Full"}
for slot, path in ITEMS.items():
    key = col.try_add_item_from_wardrobe_item(slot, lib.load_asset(path))
    inst.set_single_slot_selection(slot, key)
    print("SET", slot, path.split("/")[-1], key is not None)
mhs.on_edit_preview_collection(ch)
mhs.assemble_for_preview(ch)
COL = {"Eyelash": {"Melanin": 1.0, "Redness": 0.0, "Lightness": 0.0}, "Eyebrow": {"Melanin": 1.0, "Redness": 0.02, "Lightness": 0.0}}
DYE = {"Eyelash": (0.12, 0.11, 0.11, 1.0), "Eyebrow": (0.2, 0.17, 0.16, 1.0)}
for p in inst.get_instance_parameter_item_paths():
    t = p.export_text()
    for frag, vals in COL.items():
        if frag in t:
            for q in inst.get_instance_parameters(p):
                print("PRM", frag, q.name)
                if str(q.name) == "DyeColor":
                    print("COL", frag, "DyeColor ->", q.set_color(unreal.LinearColor(*DYE[frag])))
                if str(q.name) in vals:
                    print("COL", frag, q.name, q.get_float(), "->", vals[str(q.name)], q.set_float(vals[str(q.name)]))
mhs.on_edit_preview_collection(ch)
lib.save_loaded_asset(ch, only_if_is_dirty=False)
print("OK grooms")

"""Runs inside Unreal (ue_py.py). Dresses MH_AgoraSoldier from the built-in MetaHuman wardrobe (hair, eyebrows,
eyelashes, the default garment) and builds a game-ready (Optimized) MetaHuman into /Game/AgoraChar/MetaHuman/Built."""
import unreal

CH = "/Game/AgoraChar/MetaHuman/MH_AgoraSoldier"
PICK = {
    "Hair": "/MetaHumanCharacter/Optional/Grooms/Bindings/Hair/WI_Hair_S_UpdoBuns",
    "Eyebrows": "/MetaHumanCharacter/Optional/Grooms/Bindings/Eyebrows/WI_Eyebrows_M_Natural",
    "Eyelashes": "/MetaHumanCharacter/Optional/Grooms/Bindings/Eyelashes/WI_Eyelashes_S_Fine",
    "Outfits": "/MetaHumanCharacter/Optional/Clothing/WI_DefaultGarment",
}
lib = unreal.EditorAssetLibrary
mhs = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
ch = lib.load_asset(CH)
mhs.try_add_object_to_edit(ch) if not mhs.is_object_added_for_editing(ch) else None
col = ch.get_editor_property("internal_collection")
inst = col.get_editor_property("default_instance")
reg = unreal.AssetRegistryHelpers.get_asset_registry()
for slot, path in PICK.items():
    item = lib.load_asset(path)
    if item is None:  # the folder layout differs per category; find it by name
        name = path.rsplit("/", 1)[-1]
        f = unreal.ARFilter(class_paths=[unreal.TopLevelAssetPath("/Script/MetaHumanCharacterPalette", "MetaHumanWardrobeItem")], recursive_classes=True)
        hit = [str(a.package_name) for a in reg.get_assets(f) if str(a.asset_name) == name]
        item = lib.load_asset(hit[0]) if hit else None
    key = col.try_add_item_from_wardrobe_item(slot, item)
    if key is None:
        keys = col.get_item_keys_for_wardrobe_item(item) if item else []
        key = keys[0] if keys else None
    ok = inst.set_single_slot_selection(slot, key) if key is not None else False
    print(slot, item.get_name() if item else None, "selected", ok)
mhs.assemble_for_preview(ch)
lib.save_loaded_asset(ch, only_if_is_dirty=False)

params = unreal.MetaHumanCharacterEditorBuildParameters()
params.set_editor_property("pipeline_type", unreal.MetaHumanDefaultPipelineType.OPTIMIZED)
params.set_editor_property("pipeline_quality", unreal.MetaHumanQualityLevel.HIGH)
params.set_editor_property("absolute_build_path", "/Game/AgoraChar/MetaHuman/Built")
print("can build", mhs.can_build_meta_human(ch, True))
mhs.build_meta_human(ch, params)
built = sorted(str(a.package_name) for a in reg.get_assets_by_path("/Game/AgoraChar/MetaHuman/Built", True))
print("built assets", len(built))
for b in built[:40]:
    print("  ", b)

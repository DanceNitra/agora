"""Runs inside Unreal. Adds brows, lashes and the default garment to Yuki's MetaHuman character (no MetaHuman hair: her
hair is our own groom) and builds a game-ready (Optimized, High) MetaHuman into /Game/AgoraChar/Tripo/Yuki/Built_<name>.
A wrapper may set NAME."""
import unreal

CFG = {"name": globals().get("NAME", "MHC_Yuki_v2")}
PKG = "/Game/AgoraChar/Tripo/Yuki"
CH = PKG + "/" + CFG["name"]
OUT = PKG + "/Built_" + CFG["name"]
G = "/MetaHumanCharacter/Optional/Grooms/Bindings/"
PICK = {
    "Eyebrows": G + "Eyebrows/WI_Eyebrows_M_Thin",
    "Eyelashes": G + "Eyelashes/WI_Eyelashes_L_Curl",
    "Outfits": "/MetaHumanCharacter/Optional/Clothing/WI_DefaultGarment",
}
MELANIN = 0.55  # light brown brows; the lashes take the same value
keys = {}
lib = unreal.EditorAssetLibrary
sub = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
ch = lib.load_asset(CH)
if not sub.is_object_added_for_editing(ch):
    print("added for edit", sub.try_add_object_to_edit(ch))
try:
    col = ch.get_editor_property("internal_collection")
    inst = col.get_editor_property("default_instance")
    for slot, path in PICK.items():
        item = lib.load_asset(path)
        key = col.try_add_item_from_wardrobe_item(slot, item) if item else None
        if key is None and item:
            keys = col.get_item_keys_for_wardrobe_item(item)
            key = keys[0] if keys else None
        if key is not None:
            inst.set_single_slot_selection(slot, key)
            keys[slot] = key
        print(slot, item.get_name() if item else None, "key", key is not None)
    sub.assemble_for_preview(ch)
    # Dark hair on every hair groom: Melanin 0 is white, 1 is black. The parameters live on the preview
    # collection; edits there survive the pipeline rebuild.
    pc = sub.get_preview_collection(ch)
    pi = pc.default_instance
    # A new character's preview collection is empty; give it the same items, or the edit below drops them.
    for slot, path in PICK.items():
        item = lib.load_asset(path)
        k = pc.try_add_item_from_wardrobe_item(slot, item)
        if k is None:
            ks = pc.get_item_keys_for_wardrobe_item(item)
            k = ks[0] if ks else None
        if k is not None:
            pi.set_single_slot_selection(slot, k)
    sub.assemble_for_preview(ch)
    for slot, path in PICK.items():
        if slot == "Outfits":
            continue
        done = []
        for key in pc.get_item_keys_for_wardrobe_item(lib.load_asset(path)):
            for q in pi.get_instance_parameters(item_path=unreal.MetaHumanPaletteItemPath(item_key=key)):
                n = str(q.name)
                if n == "Melanin":
                    q.set_float(value=MELANIN); done.append(n)
                elif n == "Redness":
                    q.set_float(value=0.15); done.append(n)
                elif n in ("bUseHighlights", "bUseOmbre"):
                    q.set_bool(value=False); done.append(n)
        print(slot, "set", done)
    try:
        sub.on_edit_preview_collection(ch)
    except Exception as e:  # the signature is not documented; report instead of guessing
        print("on_edit_preview_collection:", e)
    sub.assemble_for_preview(ch)
    lib.save_loaded_asset(ch, only_if_is_dirty=False)
    params = unreal.MetaHumanCharacterEditorBuildParameters()
    params.set_editor_property("pipeline_type", unreal.MetaHumanDefaultPipelineType.OPTIMIZED)
    params.set_editor_property("pipeline_quality", unreal.MetaHumanQualityLevel.HIGH)
    params.set_editor_property("absolute_build_path", OUT)
    print("can build", sub.can_build_meta_human(ch, True))
    sub.build_meta_human(ch, params)
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    # build_meta_human does not save: an editor crash after it lost all 65 assets (2026-11-13).
    print("saved built folder", lib.save_directory(OUT, only_if_is_dirty=False, recursive=True))
    built = sorted(str(a.package_name) for a in reg.get_assets_by_path(OUT, True))
    print("built assets", len(built))
    for b in built:
        if any(k in b for k in ("BP_", "SKM_", "_Body", "FaceMesh", "Skeleton")):
            print("  ", b)
finally:
    if sub.is_object_added_for_editing(ch):
        sub.remove_object_to_edit(ch)

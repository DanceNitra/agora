"""Runs inside Unreal. Finds how the hero's groom instance parameters are reached."""
import unreal

lib = unreal.EditorAssetLibrary
sub = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
ch = lib.load_asset("/Game/AgoraChar/Tripo/Hero01/MHC_Hero01_v2")
added = sub.try_add_object_to_edit(ch)
try:
    col = ch.internal_collection
    inst = col.default_instance
    print("inst", [n for n in dir(inst) if not n.startswith("_") and n not in dir(unreal.Object)])
    print("col", [n for n in dir(col) if not n.startswith("_") and n not in dir(unreal.Object)])
    sub.assemble_for_preview(character=ch)
    item = lib.load_asset("/MetaHumanCharacter/Optional/Grooms/Bindings/Hair/WI_Hair_S_SweptUp")
    for key in col.get_item_keys_for_wardrobe_item(item):
        path = unreal.MetaHumanPaletteItemPath(item_key=key)
        ps = inst.get_instance_parameters(item_path=path)
        print("key params", [str(p.name) for p in ps])
    pc = sub.get_preview_collection(ch) if hasattr(sub, "get_preview_collection") else None
    if pc:
        pi = pc.default_instance
        for key in pc.get_item_keys_for_wardrobe_item(item):
            ps = pi.get_instance_parameters(item_path=unreal.MetaHumanPaletteItemPath(item_key=key))
            print("preview key params", [str(p.name) for p in ps])
finally:
    if added:
        sub.remove_object_to_edit(ch)

import unreal, time
mhs = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
ch = unreal.EditorAssetLibrary.load_asset("/Game/Companions/MetaHuman/MH_DepesaKF")
mhs.try_add_object_to_edit(ch) if not mhs.is_object_added_for_editing(ch) else None
t = unreal.MetaHumanCharacterTextureRequestParams()
t.set_editor_property("blocking", True)
mhs.request_texture_sources(ch, t)
print("RIGTEX can_build", mhs.can_build_meta_human(ch, True))
unreal.EditorAssetLibrary.save_loaded_asset(ch, only_if_is_dirty=False)

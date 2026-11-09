# Runs INSIDE Unreal: replace the face colour override with the olive-graded albedo, set the body skin tone to
# light olive, save, rebuild MH_DepesaKF (OPTIMIZED) and save the build.
import unreal
lib = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
t = unreal.AssetImportTask()
t.set_editor_property("filename", r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\keenface\mh_zip\texture\Head_Color_olive.jpg")
t.set_editor_property("destination_path", "/Game/Companions/KeenFace")
t.set_editor_property("destination_name", "T_DepesaKF_Color_Olive")
t.set_editor_property("automated", True)
t.set_editor_property("replace_existing", True)
t.set_editor_property("save", True)
tools.import_asset_tasks([t])
col = lib.load_asset("/Game/Companions/KeenFace/T_DepesaKF_Color_Olive")
mhs = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
ch = lib.load_asset("/Game/Companions/MetaHuman/MH_DepesaKF")
mhs.try_add_object_to_edit(ch) if not mhs.is_object_added_for_editing(ch) else None
s = ch.get_editor_property("skin_settings")
sk = s.get_editor_property("skin")
sk.set_editor_property("u", 0.42)
sk.set_editor_property("v", 0.5)
s.set_editor_property("skin", sk)
ov = s.get_editor_property("texture_overrides")
face = ov.get_editor_property("face")
face[unreal.FaceTextureType.BASECOLOR] = col
ov.set_editor_property("face", face)
s.set_editor_property("texture_overrides", ov)
mhs.commit_skin_settings(ch, s)
lib.save_loaded_asset(ch, only_if_is_dirty=False)
print("OLIVE set", sk.get_editor_property("u"))

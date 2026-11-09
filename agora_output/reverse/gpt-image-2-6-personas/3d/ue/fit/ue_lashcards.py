# Runs INSIDE Unreal, AFTER the build: mascara-clumped lash cards. Imports our clumped coverage atlas, puts it on
# the built face eyelash card materials (our copies in BuiltKF), makes the cards black, and saves.
import json
import unreal

CFG = json.load(open(r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit\lashcards_cfg.json"))
lib = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
t = unreal.AssetImportTask()
t.set_editor_property("filename", CFG["png"])
t.set_editor_property("destination_path", "/Game/Companions/KeenFace/Looks")
t.set_editor_property("destination_name", CFG["asset"])
t.set_editor_property("automated", True)
t.set_editor_property("replace_existing", True)
t.set_editor_property("save", True)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
tex = lib.load_asset("/Game/Companions/KeenFace/Looks/" + CFG["asset"])
tex.set_editor_property("srgb", False)
tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_GRAYSCALE)
lib.save_loaded_asset(tex, only_if_is_dirty=False)
for n in ("MI_Face_Eyelashes", "MI_Face_EyelashesHiLODs"):
    m = lib.load_asset("/Game/Companions/MetaHuman/BuiltKF/MH_DepesaKF/Face/Materials/" + n)
    for p in mel.get_texture_parameter_names(m):
        cur = mel.get_material_instance_texture_parameter_value(m, p)
        if cur and "Coverage" in cur.get_name():
            mel.set_material_instance_texture_parameter_value(m, p, tex)
            print("LASHCARD tex", n, p)
    for p, v in CFG["scalars"].items():
        mel.set_material_instance_scalar_parameter_value(m, p, v)
    mel.update_material_instance(m)
    lib.save_loaded_asset(m, only_if_is_dirty=False)
print("LASHCARD done", tex.get_path_name())

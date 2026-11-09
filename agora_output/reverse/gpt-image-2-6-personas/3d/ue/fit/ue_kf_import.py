# Runs INSIDE Unreal: import the KeenFace MetaHuman template head + 4K maps, make MH_DepesaKF from the Vivian
# preset, fit it to the template (import_from_template), put the KeenFace maps on as face texture overrides, save.
import unreal

SRC = r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\keenface\mh_zip"
DIR = "/Game/Companions/KeenFace"
CH = "/Game/Companions/MetaHuman/MH_DepesaKF"
lib = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()


def imp(path, name, opts=None):
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", path)
    t.set_editor_property("destination_path", DIR)
    t.set_editor_property("destination_name", name)
    t.set_editor_property("automated", True)
    t.set_editor_property("replace_existing", True)
    t.set_editor_property("save", True)
    if opts:
        t.set_editor_property("options", opts)
    tools.import_asset_tasks([t])
    return lib.load_asset(DIR + "/" + name)


ui = unreal.FbxImportUI()
ui.set_editor_property("import_mesh", True)
ui.set_editor_property("import_as_skeletal", False)
ui.set_editor_property("import_materials", False)
ui.set_editor_property("import_textures", False)
ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
smd = ui.get_editor_property("static_mesh_import_data")
smd.set_editor_property("combine_meshes", True)
smd.set_editor_property("generate_lightmap_u_vs", False)
smd.set_editor_property("auto_generate_collision", False)
smd.set_editor_property("build_nanite", False)
mesh = imp(SRC + r"\head.fbx", "SM_DepesaKF_Head", ui)
print("MESH", mesh.get_path_name() if mesh else None, mesh.get_num_vertices(0) if mesh else None)

col = imp(SRC + r"\texture\Head_Color.jpg", "T_DepesaKF_Color")
nrm = imp(SRC + r"\texture\Head_Normal.jpg", "T_DepesaKF_Normal")
srm = imp(SRC + r"\texture\Head_SRMF.png", "T_DepesaKF_SRMF")
nrm.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
nrm.set_editor_property("srgb", False)
srm.set_editor_property("srgb", False)
for t in (col, nrm, srm):
    lib.save_loaded_asset(t, only_if_is_dirty=False)

if not lib.does_asset_exist(CH):
    lib.duplicate_asset("/MetaHumanCharacter/Optional/Presets/Vivian", CH)
ch = lib.load_asset(CH)
mhs = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
mhs.try_add_object_to_edit(ch) if not mhs.is_object_added_for_editing(ch) else None
p = unreal.ImportFromTemplateParams()
print("PARAMS", p)
res = mhs.import_from_template(ch, mesh, None, None, None, p)
print("IMPORT", res)

print("FACETEX", [m for m in dir(unreal.FaceTextureType) if m.isupper()])
s = ch.get_editor_property("skin_settings")
s.set_editor_property("enable_texture_overrides", True)
ov = s.get_editor_property("texture_overrides")
face = ov.get_editor_property("face")
for key, tex in (("BASECOLOR", col), ("NORMAL", nrm)):
    k = [m for m in dir(unreal.FaceTextureType) if m.isupper() and key in m.replace("_", "")]
    if k:
        face[getattr(unreal.FaceTextureType, k[0])] = tex
        print("OVERRIDE", k[0])
ov.set_editor_property("face", face)
s.set_editor_property("texture_overrides", ov)
mhs.commit_skin_settings(ch, s)
print("SAVED", lib.save_loaded_asset(ch, only_if_is_dirty=False))

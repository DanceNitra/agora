"""Runs inside Unreal. Builds the costume's own material from Tripo's three textures and assigns it to the costume mesh.
The FBX import made a Phong material with no roughness, so the cloth looked wet. ORM is R occlusion, G roughness,
B metallic. Tripo's normal map is OpenGL, Unreal reads DirectX, so the green channel is flipped. Saves only its assets."""
import unreal

DEST = "/Game/AgoraChar/Tripo/Hero01/Costume"
SRC = r"C:\Users\Danculus\agora\tools\tripo_char\models\hero01\costume_v33\hero01_costume_ORM.png"
mel = unreal.MaterialEditingLibrary
eal = unreal.EditorAssetLibrary

task = unreal.AssetImportTask()
task.set_editor_property("filename", SRC)
task.set_editor_property("destination_path", DEST)
task.set_editor_property("automated", True)
task.set_editor_property("replace_existing", True)
task.set_editor_property("save", False)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
orm = unreal.load_asset(DEST + "/hero01_costume_ORM")
orm.set_editor_property("srgb", False)
orm.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
col = unreal.load_asset(DEST + "/hero01_costume_Color")
nrm = unreal.load_asset(DEST + "/hero01_costume_NormalGL")
nrm.set_editor_property("srgb", False)
nrm.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
nrm.set_editor_property("flip_green_channel", True)
print("textures", orm.get_name(), col.get_name(), nrm.get_name(), "normal compression", nrm.get_editor_property("compression_settings"))

P = DEST + "/M_Hero01_Cloth"
if eal.does_asset_exist(P):
    mat = unreal.load_asset(P)
    mel.delete_all_material_expressions(mat)
else:
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset("M_Hero01_Cloth", DEST, unreal.Material, unreal.MaterialFactoryNew())
mat.set_editor_property("two_sided", True)


def sample(tex, y, kind):
    n = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -400, y)
    n.set_editor_property("texture", tex)
    n.set_editor_property("sampler_type", kind)
    return n


c = sample(col, -300, unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
n = sample(nrm, 0, unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
o = sample(orm, 300, unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
mel.connect_material_property(c, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
mel.connect_material_property(n, "RGB", unreal.MaterialProperty.MP_NORMAL)
mel.connect_material_property(o, "R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
mel.connect_material_property(o, "G", unreal.MaterialProperty.MP_ROUGHNESS)
mel.connect_material_property(o, "B", unreal.MaterialProperty.MP_METALLIC)
mel.recompile_material(mat)

mesh = unreal.load_asset(DEST + "/hero01_costume")
# The array returns copies of the slot structs, so each slot is rebuilt and the whole array is set.
mats = []
for m in mesh.get_editor_property("materials"):
    k = unreal.SkeletalMaterial()
    k.set_editor_property("material_interface", mat)
    k.set_editor_property("material_slot_name", m.get_editor_property("material_slot_name"))
    mats.append(k)
mesh.set_editor_property("materials", mats)
print("mesh materials", [m.material_interface.get_name() for m in mesh.get_editor_property("materials")])
for a in (orm, nrm, mat, mesh):
    p = a.get_path_name().split(".")[0]
    print("save", p, eal.save_asset(p, only_if_is_dirty=False))

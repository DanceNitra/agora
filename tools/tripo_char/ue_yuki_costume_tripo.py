"""Runs inside Unreal. Imports the costume cut from Yuki's dressed Tripo model (yuki_costume_tripo) as a skeletal mesh
on her body skeleton, with the Tripo textures in one material, and puts it in the character's outfit component.

Slots: yuki_tripo (base colour, emissive neon, normal, occlusion-roughness-metallic from the Tripo model), yuki_skin
(the body's own skin material: the mesh carries the skin the built body lacks) and yuki_gold (the bell).
The costume mesh also carries all the skin the character shows below the neck (no calves or feet: they are inside the
boots), so the level actor's Body component is hidden (HIDE_BODY) and set to tick its pose always: it stays the
leader of the pose.
A wrapper sets ARGS = dict(DIR=<folder of yuki_costume_tripo's output>, and optionally NAME, EMIT (emissive gain),
ROUGH (roughness gain), HIDE_BODY, SAVE)."""
import os

import unreal

_A = globals().pop("ARGS", {})
NAME = _A.get("NAME", "MHC_Yuki_v5")
DIR = _A["DIR"]
PKG = "/Game/AgoraChar/Tripo/Yuki"
BUILT = f"{PKG}/Built_{NAME}/{NAME}"
DEST = PKG + "/CostumeT"
lib, mel = unreal.EditorAssetLibrary, unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
body = unreal.load_asset(f"{BUILT}/Body/SKM_{NAME}_BodyMesh")
skel = body.get_editor_property("skeleton")
ui = unreal.FbxImportUI()
for k, v in (("import_mesh", True), ("import_as_skeletal", True), ("mesh_type_to_import", unreal.FBXImportType.FBXIT_SKELETAL_MESH), ("skeleton", skel),
             ("import_animations", False), ("import_materials", False), ("import_textures", False), ("create_physics_asset", False)):
    ui.set_editor_property(k, v)
sk = ui.get_editor_property("skeletal_mesh_import_data")
sk.set_editor_property("import_morph_targets", False)
sk.set_editor_property("update_skeleton_reference_pose", False)
sk.set_editor_property("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
tasks = []
t = unreal.AssetImportTask()
for k, v in (("filename", os.path.join(DIR, "yuki_costume.fbx")), ("destination_path", DEST), ("destination_name", "SKM_Yuki_CostumeT"), ("automated", True), ("replace_existing", True),
             ("save", False), ("options", ui)):
    t.set_editor_property(k, v)
tasks.append(t)
for nm in ("base", "emissive", "normal", "orm"):
    t = unreal.AssetImportTask()
    for k, v in (("filename", os.path.join(DIR, f"yuki_costume_{nm}.png")), ("destination_path", DEST), ("destination_name", "T_Yuki_CostumeT_" + nm), ("automated", True),
                 ("replace_existing", True), ("save", False)):
        t.set_editor_property(k, v)
    tasks.append(t)
tools.import_asset_tasks(tasks)
mesh = unreal.load_asset(DEST + "/SKM_Yuki_CostumeT")
tex = {nm: unreal.load_asset(f"{DEST}/T_Yuki_CostumeT_{nm}") for nm in ("base", "emissive", "normal", "orm")}
tex["normal"].set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
tex["normal"].set_editor_property("srgb", False)
tex["normal"].set_editor_property("flip_green_channel", True)          # the Tripo normal map is OpenGL
tex["orm"].set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
tex["orm"].set_editor_property("srgb", False)
for nm, tx in tex.items():
    pass
    lib.save_asset(f"{DEST}/T_Yuki_CostumeT_{nm}", only_if_is_dirty=False)
print("COSTUMET imported", mesh.get_name(), "skeleton", mesh.get_editor_property("skeleton").get_name(), {k: (v.blueprint_get_size_x(), v.blueprint_get_size_y()) for k, v in tex.items()})

m = unreal.load_asset(f"{DEST}/M_Yuki_Tripo") or tools.create_asset("M_Yuki_Tripo", DEST, unreal.Material, unreal.MaterialFactoryNew())
mel.delete_all_material_expressions(m)
m.set_editor_property("two_sided", True)


def sample(nm, y, stype):
    e = mel.create_material_expression(m, unreal.MaterialExpressionTextureSample, -700, y)
    e.set_editor_property("texture", tex[nm])
    e.set_editor_property("sampler_type", stype)
    return e


def const(v, y):
    e = mel.create_material_expression(m, unreal.MaterialExpressionConstant, -500, y)
    e.set_editor_property("r", float(v))
    return e


def mul(a, a_out, k, y):
    e = mel.create_material_expression(m, unreal.MaterialExpressionMultiply, -300, y)
    mel.connect_material_expressions(a, a_out, e, "A")
    mel.connect_material_expressions(const(k, y + 60), "", e, "B")
    return e


b = sample("base", 0, unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
e_ = sample("emissive", 250, unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
n = sample("normal", 500, unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
o = sample("orm", 750, unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
mel.connect_material_property(b, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
mel.connect_material_property(mul(e_, "RGB", _A.get("EMIT", 6.0), 250), "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
mel.connect_material_property(n, "RGB", unreal.MaterialProperty.MP_NORMAL)
mel.connect_material_property(o, "R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
mel.connect_material_property(mul(o, "G", _A.get("ROUGH", 1.0), 800), "", unreal.MaterialProperty.MP_ROUGHNESS)
mel.connect_material_property(o, "B", unreal.MaterialProperty.MP_METALLIC)
mel.recompile_material(m)
lib.save_asset(f"{DEST}/M_Yuki_Tripo", only_if_is_dirty=False)
# hair and ears of the Tripo model: the same textures, tinted (the Tripo hair is a paler peach than Yuki's pink), rougher
# and without the neon layer
mh_ = unreal.load_asset(f"{DEST}/M_Yuki_TripoHair") or tools.create_asset("M_Yuki_TripoHair", DEST, unreal.Material, unreal.MaterialFactoryNew())
mel.delete_all_material_expressions(mh_)
mh_.set_editor_property("two_sided", True)
_m_keep, m = m, mh_
hb_ = sample("base", 0, unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
hn_ = sample("normal", 500, unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
tint = mel.create_material_expression(mh_, unreal.MaterialExpressionConstant3Vector, -500, 120)
_t = _A.get("HAIR_TINT", (1.0, 0.80, 0.96))
tint.set_editor_property("constant", unreal.LinearColor(_t[0], _t[1], _t[2], 1))
mu_ = mel.create_material_expression(mh_, unreal.MaterialExpressionMultiply, -300, 0)
mel.connect_material_expressions(hb_, "RGB", mu_, "A")
mel.connect_material_expressions(tint, "", mu_, "B")
mel.connect_material_property(mu_, "", unreal.MaterialProperty.MP_BASE_COLOR)
mel.connect_material_property(hn_, "RGB", unreal.MaterialProperty.MP_NORMAL)
mel.connect_material_property(const(_A.get("HAIR_ROUGH", 0.55), 800), "", unreal.MaterialProperty.MP_ROUGHNESS)
mel.connect_material_property(const(0.35, 880), "", unreal.MaterialProperty.MP_SPECULAR)
# The ears are thin and their backs face away from the key light: opaque, they rendered black from behind, and every
# bit of ear between the strands read as a dark plate (owner, 2026-11-14). As thin foliage they let the light through
# in their own pink (subsurface colour = the tinted base colour), as real cat ears do against the light.
if _A.get("EAR_SSS", True):
    mh_.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
    mel.connect_material_property(mu_, "", unreal.MaterialProperty.MP_SUBSURFACE_COLOR)
mel.recompile_material(mh_)
lib.save_asset(f"{DEST}/M_Yuki_TripoHair", only_if_is_dirty=False)
m = _m_keep
gold = unreal.load_asset(f"{PKG}/Costume/M_Yuki_Gold")
skin = next(lib.load_asset(a.split(".")[0]) for a in lib.list_assets(f"{BUILT}/Body", recursive=True) if "MI_Body" in a and isinstance(lib.load_asset(a.split(".")[0]), unreal.MaterialInstanceConstant))
table = {"yuki_tripo_hair": mh_, "yuki_tripo": m, "yuki_skin": skin, "yuki_gold": gold}       # the longer name first: slots match by substring
slots = []
for ms in mesh.get_editor_property("materials"):
    nm = str(ms.get_editor_property("material_slot_name"))
    k = unreal.SkeletalMaterial()
    k.set_editor_property("material_interface", next((v for key, v in table.items() if key in nm.lower()), m))
    k.set_editor_property("material_slot_name", ms.get_editor_property("material_slot_name"))
    slots.append(k)
    print("COSTUMET slot", nm, "->", k.get_editor_property("material_interface").get_name())
mesh.set_editor_property("materials", slots)
lib.save_asset(DEST + "/SKM_Yuki_CostumeT", only_if_is_dirty=False)
bp = unreal.load_asset(f"{BUILT}/BP_{NAME}")
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
L = unreal.SubobjectDataBlueprintFunctionLibrary
done = set()
for h in sds.k2_gather_subobject_data_for_blueprint(bp):
    ob = L.get_associated_object(sds.k2_find_subobject_data_from_handle(h))
    if isinstance(ob, unreal.SkeletalMeshComponent) and ob.get_name() == "SkeletalMesh_GEN_VARIABLE" and ob.get_path_name() not in done:
        done.add(ob.get_path_name())
        ob.set_editor_property("override_materials", [])
        ob.set_skeletal_mesh_asset(mesh)
print("COSTUMET blueprint outfit templates set", len(done))
unreal.BlueprintEditorLibrary.compile_blueprint(bp)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in eas.get_all_level_actors():
    if a.get_actor_label() == "Yuki_Character":
        for c in a.get_components_by_class(unreal.SkeletalMeshComponent):
            if c.get_name() == "SkeletalMesh":
                c.set_editor_property("override_materials", [])
                c.set_skeletal_mesh_asset(mesh)
                print("COSTUMET level actor outfit", c.get_skeletal_mesh_asset().get_name(), [x.get_name() for x in c.get_materials()])
            if c.get_name() == "Body" and _A.get("HIDE_BODY", True):
                # the costume mesh carries all the skin that shows; the body still drives the pose, so it keeps ticking
                c.set_editor_property("visible", False)
                c.set_editor_property("visibility_based_anim_tick_option", unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
                print("COSTUMET body hidden, tick option", c.get_editor_property("visibility_based_anim_tick_option"))
if _A.get("SAVE", True):
    print("COSTUMET saved bp", lib.save_asset(f"{BUILT}/BP_{NAME}", only_if_is_dirty=False))

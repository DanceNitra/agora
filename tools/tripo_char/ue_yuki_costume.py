"""Runs inside Unreal. Imports Yuki's costume (yuki_costume_shell) as a skeletal mesh on her body skeleton, gives it its
materials and puts it in the character's outfit component in place of the default T-shirt and shorts.

The outfit component (child of Body, driven by the body's pose) exists in the Blueprint and on the level's actor; both
are set. Slots: yuki_latex (black, glossy), yuki_neon (pink, emissive), yuki_gold (the bell), yuki_strap (matt black bands), yuki_skin (the body's own
skin material: the costume mesh carries the skin the built body lacks under the old clothes).
A wrapper may set ARGS = dict(FBX=..., NAME=..., NEON=emissive strength, SAVE=bool)."""
import unreal

_A = globals().pop("ARGS", {})
NAME = _A.get("NAME", "MHC_Yuki_v5")
FBX = _A.get("FBX", r"C:\Users\Danculus\agora\tools\tripo_char\models\yuki\costume_v1\yuki_costume.fbx")
PKG = "/Game/AgoraChar/Tripo/Yuki"
BUILT = f"{PKG}/Built_{NAME}/{NAME}"
DEST = PKG + "/Costume"
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
task = unreal.AssetImportTask()
for k, v in (("filename", FBX), ("destination_path", DEST), ("destination_name", "SKM_Yuki_Costume"), ("automated", True), ("replace_existing", True), ("save", False), ("options", ui)):
    task.set_editor_property(k, v)
tools.import_asset_tasks([task])
mesh = unreal.load_asset(DEST + "/SKM_Yuki_Costume")
print("COSTUME imported", [str(p) for p in task.get_editor_property("imported_object_paths")], "skeleton", mesh.get_editor_property("skeleton").get_name())


def mat(name, base, rough, spec=0.5, metal=0.0, emissive=None):
    m = unreal.load_asset(f"{DEST}/{name}") or tools.create_asset(name, DEST, unreal.Material, unreal.MaterialFactoryNew())
    mel.delete_all_material_expressions(m)
    m.set_editor_property("two_sided", True)

    def c3(v, y):
        e = mel.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -400, y)
        e.set_editor_property("constant", unreal.LinearColor(v[0], v[1], v[2], 1))
        return e

    def c1(v, y):
        e = mel.create_material_expression(m, unreal.MaterialExpressionConstant, -400, y)
        e.set_editor_property("r", float(v))
        return e

    mel.connect_material_property(c3(base, 0), "", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(c1(rough, 150), "", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.connect_material_property(c1(spec, 220), "", unreal.MaterialProperty.MP_SPECULAR)
    mel.connect_material_property(c1(metal, 290), "", unreal.MaterialProperty.MP_METALLIC)
    if emissive:
        mel.connect_material_property(c3(emissive, 380), "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.recompile_material(m)
    lib.save_asset(f"{DEST}/{name}", only_if_is_dirty=False)
    return m


NE = _A.get("NEON", 12.0)
skin = next(lib.load_asset(a.split(".")[0]) for a in lib.list_assets(f"{BUILT}/Body", recursive=True) if "MI_Body" in a and isinstance(lib.load_asset(a.split(".")[0]), unreal.MaterialInstanceConstant))
table = {"yuki_latex": mat("M_Yuki_Latex", (0.012, 0.010, 0.014), 0.2, 0.7), "yuki_neon": mat("M_Yuki_Neon", (0.02, 0.0, 0.01), 0.4, 0.3, 0.0, (1.0 * NE, 0.06 * NE, 0.5 * NE)),
         "yuki_gold": mat("M_Yuki_Gold", (0.83, 0.62, 0.18), 0.3, 0.5, 1.0), "yuki_skin": skin,
         "yuki_strap": mat("M_Yuki_Strap", (0.030, 0.028, 0.034), 0.55, 0.4)}
slots = []
for mslot in mesh.get_editor_property("materials"):
    nm = str(mslot.get_editor_property("material_slot_name"))
    k = unreal.SkeletalMaterial()
    k.set_editor_property("material_interface", next((v for key, v in table.items() if key in nm.lower()), table["yuki_latex"]))
    k.set_editor_property("material_slot_name", mslot.get_editor_property("material_slot_name"))
    slots.append(k)
    print("COSTUME slot", nm, "->", k.get_editor_property("material_interface").get_name())
mesh.set_editor_property("materials", slots)
lib.save_asset(DEST + "/SKM_Yuki_Costume", only_if_is_dirty=False)
bp = unreal.load_asset(f"{BUILT}/BP_{NAME}")
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
L = unreal.SubobjectDataBlueprintFunctionLibrary
done = set()
for h in sds.k2_gather_subobject_data_for_blueprint(bp):
    o = L.get_associated_object(sds.k2_find_subobject_data_from_handle(h))
    if isinstance(o, unreal.SkeletalMeshComponent) and o.get_name() == "SkeletalMesh_GEN_VARIABLE" and o.get_path_name() not in done:
        done.add(o.get_path_name())
        o.set_editor_property("override_materials", [])
        o.set_skeletal_mesh_asset(mesh)
print("COSTUME blueprint outfit templates set", len(done))
unreal.BlueprintEditorLibrary.compile_blueprint(bp)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in eas.get_all_level_actors():
    if a.get_actor_label() == "Yuki_Character":
        for c in a.get_components_by_class(unreal.SkeletalMeshComponent):
            if c.get_name() == "SkeletalMesh":
                c.set_editor_property("override_materials", [])
                c.set_skeletal_mesh_asset(mesh)
                print("COSTUME level actor outfit", c.get_skeletal_mesh_asset().get_name(), [x.get_name() for x in c.get_materials()])
if _A.get("SAVE", True):
    print("COSTUME saved bp", lib.save_asset(f"{BUILT}/BP_{NAME}", only_if_is_dirty=False))

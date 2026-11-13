"""Runs inside Unreal. Imports the costume FBX as a skeletal mesh on the hero's own skeleton, sets its materials
Two Sided (Tripo's material is single-sided and FBX does not carry the flag), and saves only the imported assets."""
import unreal

# The script runs in the editor's process, so it reads no shell variables. A wrapper may set COSTUME_FBX (another build)
# and SAVE = False (leave the import unsaved, so a test is dropped by reimporting or closing without saving) above it.
FBX = globals().get("COSTUME_FBX", r"C:\Users\Danculus\agora\tools\tripo_char\models\hero01\costume_v33\hero01_costume.fbx")
SAVE = globals().get("SAVE", True)
CLOTH = "/Game/AgoraChar/Tripo/Hero01/Costume/M_Hero01_Cloth"  # ue_costume_material.py; the FBX's own material looks wet
DEST = "/Game/AgoraChar/Tripo/Hero01/Costume"
BODY = "/Game/AgoraChar/Tripo/Hero01/Built_MHC_Hero01_v3/MHC_Hero01_v3/Body/SKM_MHC_Hero01_v3_BodyMesh"

skel = unreal.load_asset(BODY).get_editor_property("skeleton")
print("skeleton", skel.get_path_name())
ui = unreal.FbxImportUI()
ui.set_editor_property("import_mesh", True)
ui.set_editor_property("import_as_skeletal", True)
ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_SKELETAL_MESH)
ui.set_editor_property("skeleton", skel)
ui.set_editor_property("import_animations", False)
have_cloth = unreal.EditorAssetLibrary.does_asset_exist(CLOTH)
ui.set_editor_property("import_materials", not have_cloth)
ui.set_editor_property("import_textures", not have_cloth)
ui.set_editor_property("create_physics_asset", False)
sk = ui.get_editor_property("skeletal_mesh_import_data")
sk.set_editor_property("import_morph_targets", False)
sk.set_editor_property("update_skeleton_reference_pose", False)
sk.set_editor_property("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
task = unreal.AssetImportTask()
task.set_editor_property("filename", FBX)
task.set_editor_property("destination_path", DEST)
task.set_editor_property("automated", True)
task.set_editor_property("replace_existing", True)
task.set_editor_property("save", False)
task.set_editor_property("options", ui)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
paths = [str(p) for p in task.get_editor_property("imported_object_paths")]
print("imported", paths)
made = unreal.EditorAssetLibrary.list_assets(DEST, recursive=True)
for p in made:
    a = unreal.load_asset(p.split(".")[0])
    if isinstance(a, unreal.Material):
        a.set_editor_property("two_sided", True)
        unreal.MaterialEditingLibrary.recompile_material(a)
        print("two sided", p)
    if isinstance(a, unreal.SkeletalMesh):
        if have_cloth:
            cloth = unreal.load_asset(CLOTH)
            slots = []
            for m in a.get_editor_property("materials"):
                k = unreal.SkeletalMaterial()
                k.set_editor_property("material_interface", cloth)
                k.set_editor_property("material_slot_name", m.get_editor_property("material_slot_name"))
                slots.append(k)
            a.set_editor_property("materials", slots)
        b = a.get_bounds()
        print("mesh", p, "skeleton", a.get_editor_property("skeleton").get_name(), "materials", [m.material_interface.get_name() if m.material_interface else None for m in a.materials],
              "bounds extent", b.box_extent, "origin", b.origin)
for p in made if SAVE else []:
    print("save", p, unreal.EditorAssetLibrary.save_asset(p.split(".")[0], only_if_is_dirty=False))

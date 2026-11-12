"""Runs inside Unreal. Imports the costume FBX as a skeletal mesh on the hero's own skeleton, sets its materials
Two Sided (Tripo's material is single-sided and FBX does not carry the flag), and saves only the imported assets."""
import unreal

FBX = r"C:\Users\Danculus\agora\tools\tripo_char\models\hero01\costume_v33\hero01_costume.fbx"
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
ui.set_editor_property("import_materials", True)
ui.set_editor_property("import_textures", True)
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
        b = a.get_bounds()
        print("mesh", p, "skeleton", a.get_editor_property("skeleton").get_name(), "materials", [m.material_interface.get_name() if m.material_interface else None for m in a.materials],
              "bounds extent", b.box_extent, "origin", b.origin)
for p in made:
    print("save", p, unreal.EditorAssetLibrary.save_asset(p.split(".")[0], only_if_is_dirty=False))

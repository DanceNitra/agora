import unreal
lib = unreal.EditorAssetLibrary
path = "/Game/Companions/MetaHuman/BuiltKF/MH_DepesaKF/Face/Baked/T_Head_LOD1_BC_VT"
assert lib.does_asset_exist(path), "missing " + path
t = lib.load_asset(path)
assert t is not None
print("PRM size", t.blueprint_get_size_x(), t.blueprint_get_size_y())
task = unreal.AssetExportTask(); task.set_editor_property("object", t)
task.set_editor_property("filename", r"C:\Users\Danculus\AppData\Local\Temp\claude\8d2d35ef4a747728\83118a43-1d36-4a52-a91d-799c725bc0b0\scratchpad\baked_lod1.png")
task.set_editor_property("automated", True); task.set_editor_property("prompt", False); task.set_editor_property("replace_identical", True)
print("PRM export", unreal.Exporter.run_asset_export_task(task))

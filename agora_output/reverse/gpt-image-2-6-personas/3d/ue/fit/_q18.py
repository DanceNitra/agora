import unreal
lib = unreal.EditorAssetLibrary
S = r"C:\Users\Danculus\AppData\Local\Temp\claude\8d2d35ef4a747728\83118a43-1d36-4a52-a91d-799c725bc0b0\scratchpad"
for path, name in (("/Game/Companions/KeenFace/Looks/T_DepesaKF_Look_p6_v9_brows", "ue_look_v9.png"),
                   ("/Game/Companions/MetaHuman/BuiltKF/MH_DepesaKF/Face/Baked/T_Head_LOD1_BC_VT", "ue_baked_lod1.png")):
    if not lib.does_asset_exist(path):
        print("PRM missing", path); continue
    t = lib.load_asset(path)
    if t is None:
        print("PRM none", path); continue
    print("PRM", path, t.blueprint_get_size_x(), t.blueprint_get_size_y())
    task = unreal.AssetExportTask(); task.set_editor_property("object", t)
    task.set_editor_property("filename", S + "\\" + name)
    task.set_editor_property("automated", True); task.set_editor_property("prompt", False); task.set_editor_property("replace_identical", True)
    print("PRM export", unreal.Exporter.run_asset_export_task(task))

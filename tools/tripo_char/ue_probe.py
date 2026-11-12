"""Runs inside Unreal (tools/comfy_char/ue_py.py). Reports what the MetaHuman Python API offers for a custom mesh."""
import unreal

print("engine", unreal.SystemLibrary.get_engine_version())
print("project", unreal.Paths.get_project_file_path())
sub = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
names = [n for n in dir(sub) if not n.startswith("_")]
for key in ("conform", "fit", "import", "rig", "track", "mesh_data", "build", "assemble"):
    print(key, [n for n in names if key in n])
for cls in ("ConformTargetParams", "MetaHumanCharacterFitToVerticesParams", "PromotedFrameUtils",
            "MetaHumanCharacterAutoRiggingRequestParams", "MetaHumanCharacterEditorBuildParameters"):
    print(cls, hasattr(unreal, cls))
print("toolset classes", [n for n in dir(unreal) if "MetaHumanGenerator" in n][:20])
print("existing", unreal.EditorAssetLibrary.does_asset_exist("/Game/AgoraChar/MetaHuman/MH_AgoraSoldier"))

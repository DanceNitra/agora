import unreal
w = unreal.EditorLevelLibrary.get_editor_world() if hasattr(unreal.EditorLevelLibrary, "get_editor_world") else unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
pk = [p for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages() if p.get_name() == "/Game/Maps/L_Tomb_S03_Ambience"]
print("OK saved", unreal.EditorLoadingAndSavingUtils.save_packages(pk, True) if pk else "none dirty")
print("OK dirty maps after", [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()])

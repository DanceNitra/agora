"""Runs inside Unreal. Points the editor viewport at the hero's head and redraws it."""
import unreal

ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
ues.set_level_viewport_camera_info(unreal.Vector(0, 160, 160), unreal.Rotator(roll=0, pitch=0, yaw=-90))
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_invalidate_viewports()
print("viewport camera", ues.get_level_viewport_camera_info())

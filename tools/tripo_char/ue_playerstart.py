"""Runs inside Unreal. Puts one PlayerStart in the preview level so the play camera stands in front of the hero."""
import unreal

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in eas.get_all_level_actors():
    if a.get_actor_label() == "Hero01_Start":
        eas.destroy_actor(a)
ps = eas.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(0, 480, 100), unreal.Rotator(roll=0, pitch=0, yaw=-90))
ps.set_actor_label("Hero01_Start")
print("start", ps.get_actor_location(), unreal.EditorAssetLibrary.save_asset("/Game/AgoraChar/Tripo/Hero01/L_Hero01_Preview", only_if_is_dirty=False))

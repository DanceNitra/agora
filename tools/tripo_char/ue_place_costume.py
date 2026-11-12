"""Runs inside Unreal. Places the costume skeletal mesh in the preview level as `Hero01_Costume`, on the hero's transform.
The level is not saved here. In play, play_capture.py (COSTUME=...) makes it follow the body's pose."""
import unreal

COSTUME = "/Game/AgoraChar/Tripo/Hero01/Costume/hero01_costume"
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in eas.get_all_level_actors():
    if a.get_actor_label() == "Hero01_Costume":
        eas.destroy_actor(a)
hero = next(a for a in eas.get_all_level_actors() if a.get_actor_label() == "Hero01_Character")
body = next(c for c in hero.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == "Body")
t = body.get_world_transform()
sa = eas.spawn_actor_from_object(unreal.load_asset(COSTUME), t.translation, t.rotation.rotator())
sa.set_actor_label("Hero01_Costume")
print("placed", sa.get_class().get_name(), sa.get_actor_location(), sa.get_actor_rotation(), "body", t.translation, t.rotation.rotator())

# Runs INSIDE Unreal: destroy every FIT_* helper actor, transient ones included (get_all_level_actors skips them).
import unreal
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
les.eject_pilot_level_actor()
dead = [a for a in unreal.ObjectIterator(unreal.Actor) if a.get_actor_label().startswith("FIT_")]
names = [a.get_actor_label() for a in dead]
for a in dead:
    eas.destroy_actor(a)
print("CLEAN", len(names), sorted(names))

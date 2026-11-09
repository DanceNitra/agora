import unreal
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
acts = unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor)
mh = [a for a in acts if "MetaHuman" in a.get_class().get_name()]
print("MH actors:", [(a.get_name(), round(a.get_actor_location().y)) for a in mh])

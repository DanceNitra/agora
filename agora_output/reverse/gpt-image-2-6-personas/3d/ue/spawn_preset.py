# Spawns one MetaHuman preset as a TRANSIENT actor far from the level content (not saved with the level).
import unreal, os
NAME = "Jelena"
LOC = unreal.Vector(0.0, 300000.0, 100000.0)
mhs = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
ch = unreal.EditorAssetLibrary.load_asset("/MetaHumanCharacter/Optional/Presets/" + NAME)
print("added", mhs.try_add_object_to_edit(ch))
mhs.assemble_for_preview(ch)
a = mhs.spawn_meta_human_actor(ch, True)
a.set_actor_location(LOC, False, False)
a.set_actor_rotation(unreal.Rotator(0, 0, 0), False)
b = a.get_actor_bounds(False)
print("ACTOR", a.get_path_name(), "origin", b[0], "extent", b[1], "fwd", a.get_actor_forward_vector())

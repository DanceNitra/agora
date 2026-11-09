# Runs INSIDE Unreal: rebuild the preview and respawn the transient FIT_MH actor at the fit location.
import unreal
mhs = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
ch = unreal.EditorAssetLibrary.load_asset("/Game/Companions/MetaHuman/MH_Depesa")
mhs.try_add_object_to_edit(ch) if not mhs.is_object_added_for_editing(ch) else None
old = set()
for c in unreal.ObjectIterator(unreal.SkeletalMeshComponent):
    o = c.get_owner()
    if o and o.get_actor_label() == "FIT_MH":
        old.add(o)
for o in old:
    eas.destroy_actor(o)
mhs.assemble_for_preview(ch)
a = mhs.spawn_meta_human_actor(ch, True)
a.set_actor_label("FIT_MH")
a.set_actor_location(unreal.Vector(0.0, 300000.0, 100000.0), False, False)
a.set_actor_rotation(unreal.Rotator(0, 0, 0), False)
print("RESPAWN destroyed", len(old), [c.get_name() for c in a.get_components_by_class(unreal.GroomComponent)])
for c in a.get_components_by_class(unreal.GroomComponent):
    g = c.get_editor_property("groom_asset")
    print("G", c.get_name(), g.get_name() if g else None)

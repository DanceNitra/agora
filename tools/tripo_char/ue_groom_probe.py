"""Runs inside Unreal. Prints the state of the hero's groom and LOD components in the preview level."""
import unreal

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
hero = next(a for a in eas.get_all_level_actors() if a.get_actor_label() == "Hero01_Character")
for c in hero.get_components_by_class(unreal.ActorComponent):
    n = c.get_name()
    if isinstance(c, unreal.GroomComponent):
        ga = c.get_editor_property("groom_asset")
        print("GROOM", n, "asset", ga.get_name() if ga else None, "binding", bool(c.get_editor_property("binding_asset")),
              "visible", c.is_visible(), "materials", len(c.get_editor_property("override_materials")),
              "forced_lod", c.get_forced_lod() if hasattr(c, "get_forced_lod") else "n/a")
    elif isinstance(c, unreal.LODSyncComponent):
        print("LODSYNC", n, "forced_lod", c.get_editor_property("forced_lod"), "num_lods", c.get_editor_property("num_lods"),
              "min_lod", c.get_editor_property("min_lod"))
    elif isinstance(c, unreal.SkeletalMeshComponent):
        print("SKM", n, "forced_lod", c.get_forced_lod(), "predicted", c.get_predicted_lod_level() if hasattr(c, "get_predicted_lod_level") else "n/a")
    else:
        print("OTHER", n, c.get_class().get_name())
ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
print("viewport camera", ues.get_level_viewport_camera_info())

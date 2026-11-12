"""Runs inside Unreal. Removes a test clip from the editor copy of the hero so the body returns to the reference pose,
then saves only the preview level."""
import unreal
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
hero = next(a for a in eas.get_all_level_actors() if a.get_actor_label() == "Hero01_Character")
cdo = unreal.get_default_object(hero.get_class())
ref = next((c for c in cdo.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name().startswith("Body")), None)
body = next(c for c in hero.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == "Body")
print("before", body.get_animation_mode(), body.get_editor_property("animation_data").anim_to_play, "class default", ref.get_animation_mode() if ref else "?", ref.get_editor_property("anim_class") if ref else "?")
body.set_editor_property("animation_data", unreal.SingleAnimationPlayData())
body.set_animation_mode(ref.get_animation_mode() if ref else unreal.AnimationMode.ANIMATION_BLUEPRINT)
print("after", body.get_animation_mode(), body.get_editor_property("animation_data").anim_to_play)
lvl = hero.get_world().get_path_name().split(".")[0]
print("save", lvl, unreal.EditorAssetLibrary.save_asset(lvl, only_if_is_dirty=False))

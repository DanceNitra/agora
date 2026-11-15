"""Runs inside Unreal. Attaches the ear bodies (actor Yuki_Ears) to the "head" bone of Yuki's body with the right
relative transform, and saves the level.

The ear mesh is modelled in the character's own space (head at about z 165 with the actor at the origin). Attached
with "keep world", the offset to the head bone lived only in the attachment, and it was lost when later edits rebuilt
the character's components: the ears then sat at the bone itself, far from the head (seen 2026-11-14). Here the offset
is computed from the body in its reference pose and written explicitly, so it can be re-applied after any such edit.
Run this as the last step before a render."""
import unreal

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def get():
    a = {x.get_actor_label(): x for x in eas.get_all_level_actors()}
    ch = a["Yuki_Character"]
    return ch, a["Yuki_Ears"], next(c for c in ch.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == "Body")


ch, ea, body = get()
mode = body.get_editor_property("animation_mode")
data = body.get_editor_property("animation_data")
anim = data.get_editor_property("anim_to_play")
if mode != unreal.AnimationMode.ANIMATION_BLUEPRINT:           # the reference pose: no animation blueprint is set on the body
    body.set_editor_property("animation_mode", unreal.AnimationMode.ANIMATION_BLUEPRINT)
    ch, ea, body = get()
head = body.get_socket_transform("head")
want = unreal.Transform(ch.get_actor_location(), ch.get_actor_rotation(), unreal.Vector(1, 1, 1))
rel = unreal.MathLibrary.make_relative_transform(want, head)
if mode != unreal.AnimationMode.ANIMATION_BLUEPRINT:
    body.set_editor_property("animation_mode", mode)
    ch, ea, body = get()
    d = body.get_editor_property("animation_data")
    d.set_editor_property("anim_to_play", anim)
    body.set_editor_property("animation_data", d)
    ch, ea, body = get()
ea.static_mesh_component.set_mobility(unreal.ComponentMobility.MOVABLE)
ea.attach_to_component(body, "head", unreal.AttachmentRule.KEEP_RELATIVE, unreal.AttachmentRule.KEEP_RELATIVE, unreal.AttachmentRule.KEEP_RELATIVE, False)
ea.root_component.set_relative_transform(rel, False, False)
o, e = ea.get_actor_bounds(False)
hz = body.get_socket_location("head").z
print("EARS attached to", ea.get_attach_parent_actor().get_actor_label(), ea.get_attach_parent_socket_name(), "| ear centre above the head bone:", round(o.z - hz, 1), "cm (about 18 expected)",
      "| saved", unreal.EditorAssetLibrary.save_asset("/Game/AgoraChar/Tripo/Yuki/L_Yuki_Preview", only_if_is_dirty=False))

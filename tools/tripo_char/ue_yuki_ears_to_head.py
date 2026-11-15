"""Runs inside Unreal with L_Yuki_Preview open (tools/comfy_char/ue_py.py). Re-attaches the solid ear bodies (actor
Yuki_Ears) from the character's root to the head bone of the Face component, keeping their world placement, so the
ears follow head motion. Until 2026-11-15 they sat on the root: a MetaHuman Animator video solve that turns the head
left the ears standing in the air (owner's screenshot of render YT_Sinead118). Saves the level by path."""
import unreal

BONE = globals().pop("ARGS", {}).get("BONE", "head")
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
acts = {a.get_actor_label(): a for a in eas.get_all_level_actors()}
ch, ea = acts["Yuki_Character"], acts["Yuki_Ears"]
face = next(c for c in ch.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == "Face")
if not face.does_socket_exist(BONE):
    raise RuntimeError("Face has no bone " + BONE)
before = ea.get_actor_location()
ea.detach_from_actor(unreal.DetachmentRule.KEEP_WORLD, unreal.DetachmentRule.KEEP_WORLD, unreal.DetachmentRule.KEEP_WORLD)
ea.attach_to_component(face, BONE, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD,
                       unreal.AttachmentRule.KEEP_WORLD, False)
after = ea.get_actor_location()
print("EARS parent", ea.get_attach_parent_actor().get_actor_label() if ea.get_attach_parent_actor() else None,
      "socket", ea.get_attach_parent_socket_name(), "moved cm", round((after - before).length(), 3))
print("EARS level saved", unreal.EditorAssetLibrary.save_asset("/Game/AgoraChar/Tripo/Yuki/L_Yuki_Preview", only_if_is_dirty=False))

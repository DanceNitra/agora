"""Runs inside Unreal. Makes Yuki in L_Yuki_Preview able to move: until now her hair was a separate groom actor and her
ears a static mesh actor, both standing still on the actor root.

- Hair: a groom binding of GR_Yuki_Hair to the built face mesh, and the groom goes into the character's own "Hair"
  component (attached to the face, as MetaHuman hair is), so the roots follow the head. The separate actor Yuki_Hair
  is removed.
- Ears: the actor Yuki_Ears is attached to the "head" bone of the body.
A wrapper may set ARGS = dict(WIDTH=..., SHADOW_DENSITY=...). Saves the binding and the level."""
import unreal

_A = globals().pop("ARGS", {})
WIDTH, SHADOW_DENSITY = _A.get("WIDTH", 0.03), _A.get("SHADOW_DENSITY", 0.08)
PKG = "/Game/AgoraChar/Tripo/Yuki"
lib = unreal.EditorAssetLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
groom = unreal.load_asset(PKG + "/GR_Yuki_Hair")
mi = unreal.load_asset(PKG + "/MI_Yuki_Hair")


def actors():
    return {a.get_actor_label(): a for a in eas.get_all_level_actors()}


ch = actors()["Yuki_Character"]
face = next(c for c in ch.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == "Face")
BIND = PKG + "/GB_Yuki_Hair"
binding = unreal.load_asset(BIND)
if binding is None:
    binding = unreal.GroomLibrary.create_new_groom_binding_asset_with_path(BIND, groom, face.get_skeletal_mesh_asset(), 100, None, 0)
print("DANCE binding", binding.get_path_name() if binding else None)
h = next(c for c in ch.get_components_by_class(unreal.GroomComponent) if c.get_name() == "Hair")
h.set_groom_asset(groom)
h.set_binding_asset(binding)
h.set_visibility(True, True)
h.set_cast_shadow(True)
for i in range(max(1, h.get_num_materials())):
    h.set_material(i, mi)
ds = []
for d in list(h.get_editor_property("groom_groups_desc")):
    d.set_editor_property("hair_width", WIDTH)
    d.set_editor_property("hair_width_override", True)
    d.set_editor_property("hair_shadow_density", SHADOW_DENSITY)
    d.set_editor_property("hair_shadow_density_override", True)
    ds.append(d)
h.set_editor_property("groom_groups_desc", ds)
a = actors()
ch = a["Yuki_Character"]
h = next(c for c in ch.get_components_by_class(unreal.GroomComponent) if c.get_name() == "Hair")
print("DANCE hair component: groom", h.get_editor_property("groom_asset").get_name() if h.get_editor_property("groom_asset") else None,
      "binding", h.get_editor_property("binding_asset").get_name() if h.get_editor_property("binding_asset") else None,
      "visible", h.is_visible(), "width", [round(d.get_editor_property("hair_width"), 3) for d in h.get_editor_property("groom_groups_desc")])
if "Yuki_Hair" in a:
    eas.destroy_actor(a["Yuki_Hair"])
    print("DANCE removed the separate hair actor")
body = next(c for c in ch.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == "Body")
if "Yuki_Ears" in a:
    a["Yuki_Ears"].static_mesh_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    a["Yuki_Ears"].attach_to_component(body, "head", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
    print("DANCE ears on", a["Yuki_Ears"].get_attach_parent_actor().get_actor_label() if a["Yuki_Ears"].get_attach_parent_actor() else None,
          "socket", a["Yuki_Ears"].get_attach_parent_socket_name(), "location", a["Yuki_Ears"].get_actor_location())
for p in (BIND, PKG + "/L_Yuki_Preview"):
    print("DANCE save", p.split("/")[-1], lib.save_asset(p, only_if_is_dirty=False))

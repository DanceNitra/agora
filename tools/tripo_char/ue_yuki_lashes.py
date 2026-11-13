"""Runs inside Unreal. Makes the MetaHuman lash groom on Yuki_Character in L_Yuki_Preview finer and shorter: the built
L_Curl lashes read as a thick black band over the concept's thin liner. Sets the override on the level actor's groom
component (width in cm, length as a scale) and prints what the component holds afterwards. A wrapper may set
ARGS = dict(WIDTH=..., LENGTH=...). The level is saved by the caller."""
import unreal

_A = globals().pop("ARGS", {})
WIDTH, LENGTH = _A.get("WIDTH", 0.006), _A.get("LENGTH", 0.7)   # the asset's own width is 0.0123 cm
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
ch = next(a for a in eas.get_all_level_actors() if a.get_actor_label() == "Yuki_Character")
g = next(c for c in ch.get_components_by_class(unreal.GroomComponent) if c.get_name() == "Eyelashes")
out = []
for d in list(g.get_editor_property("groom_groups_desc")):
    d.set_editor_property("hair_width", WIDTH)
    d.set_editor_property("hair_width_override", True)
    d.set_editor_property("hair_length_scale", LENGTH)
    d.set_editor_property("hair_length_scale_override", True)
    out.append(d)
g.set_editor_property("groom_groups_desc", out)
ch = next(a for a in eas.get_all_level_actors() if a.get_actor_label() == "Yuki_Character")   # the edit rebuilds the actor's components
g = next(c for c in ch.get_components_by_class(unreal.GroomComponent) if c.get_name() == "Eyelashes")
print("LASHES", [(round(d.get_editor_property("hair_width"), 4), d.get_editor_property("hair_width_override"), round(d.get_editor_property("hair_length_scale"), 2),
                  d.get_editor_property("hair_length_scale_override")) for d in g.get_editor_property("groom_groups_desc")])

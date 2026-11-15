"""Runs inside Unreal. Puts Yuki's hair on the character as two grooms, for a character that moves:

- GR_Yuki_HairLong (strands of 30 cm and more) in the character's "Hair" component: this one is simulated
  (settings: ue_yuki_hair_sim with GROOM="GR_Yuki_HairLong").
- GR_Yuki_HairShort (fringe, ear fur, short hair on the head) in the character's unused "Fuzz" component: bound to
  the face mesh, never simulated, so it stays in its styled shape on the head.
Both come from the strand generator's files yuki_hair_long_ue.abc and yuki_hair_short_ue.abc in DIR and share
MI_Yuki_Hair. A wrapper may set ARGS = dict(DIR=..., WIDTH=..., SHADOW_DENSITY=..., GUIDES=...).
Saves the grooms, the short binding and the level. Run the simulation script afterwards: it makes the long binding."""
import os

import unreal

_A = globals().pop("ARGS", {})
DIR = _A.get("DIR", "C:/Users/Danculus/agora/tools/tripo_char/models/yuki/hair_strands_mh6")
WIDTH, SHADOW_DENSITY, GUIDES = _A.get("WIDTH", 0.03), _A.get("SHADOW_DENSITY", 0.08), _A.get("GUIDES", 0.03)
PKG = "/Game/AgoraChar/Tripo/Yuki"
lib = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
mi = unreal.load_asset(PKG + "/MI_Yuki_Hair")
grooms = {}
for tag in ("Long", "Short"):
    opts = unreal.GroomImportOptions()
    conv = unreal.GroomConversionSettings()
    conv.set_editor_property("rotation", unreal.Vector(0, 0, 0))
    conv.set_editor_property("scale", unreal.Vector(1, 1, 1))
    opts.set_editor_property("conversion_settings", conv)
    task = unreal.AssetImportTask()
    task.filename, task.destination_path, task.destination_name = os.path.join(DIR, f"yuki_hair_{tag.lower()}_ue.abc"), PKG, "GR_Yuki_Hair" + tag
    task.automated, task.replace_existing, task.save, task.options = True, True, False, opts
    tools.import_asset_tasks([task])
    g = unreal.load_asset(f"{PKG}/GR_Yuki_Hair{tag}")
    if tag == "Long":
        it = list(g.get_editor_property("hair_groups_interpolation"))
        for i, x in enumerate(it):
            s2 = x.get_editor_property("interpolation_settings")
            s2.set_editor_property("guide_type", unreal.GroomGuideType.GENERATED)
            s2.set_editor_property("hair_to_guide_density", GUIDES)
            x.set_editor_property("interpolation_settings", s2)
            it[i] = x
        g.set_editor_property("hair_groups_interpolation", it)
    grooms[tag] = g
    print("SPLIT imported", g.get_name(), "saved", lib.save_asset(f"{PKG}/GR_Yuki_Hair{tag}", only_if_is_dirty=False))


def character():
    return next(a for a in eas.get_all_level_actors() if a.get_actor_label() == "Yuki_Character")


face = next(c for c in character().get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == "Face")
BS = PKG + "/GB_Yuki_HairShort"
bshort = unreal.load_asset(BS) or unreal.GroomLibrary.create_new_groom_binding_asset_with_path(BS, grooms["Short"], face.get_skeletal_mesh_asset(), 100, None, 0)
for comp, tag, binding in (("Hair", "Long", None), ("Fuzz", "Short", bshort)):
    h = next(c for c in character().get_components_by_class(unreal.GroomComponent) if c.get_name() == comp)
    h.set_groom_asset(grooms[tag])
    if binding is not None:
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
for c in character().get_components_by_class(unreal.GroomComponent):
    if c.get_name() in ("Hair", "Fuzz"):
        print("SPLIT component", c.get_name(), "groom", c.get_editor_property("groom_asset").get_name() if c.get_editor_property("groom_asset") else None,
              "binding", c.get_editor_property("binding_asset").get_name() if c.get_editor_property("binding_asset") else None,
              "parent", c.get_attach_parent().get_name(), "visible", c.is_visible())
print("SPLIT saved", lib.save_asset(BS, only_if_is_dirty=False), lib.save_asset(PKG + "/L_Yuki_Preview", only_if_is_dirty=False))

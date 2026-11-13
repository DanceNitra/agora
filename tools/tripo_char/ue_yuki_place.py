"""Runs inside Unreal. Stands the built MetaHuman Yuki in L_Yuki_Preview, reimports her strand groom, gives it a
pink MetaHuman hair material, and attaches it to the character's root. Saves only the assets it names.
The groom was fitted in Blender to the conformed head as exported (Geo_<name>_Head): its place on the built actor is
found from the bounds of that mesh against the bounds of the built face component. A wrapper may set ABC, NAME, DYE."""
import unreal

NAME = globals().get("NAME", "MHC_Yuki_v2")
ABC = globals().get("ABC", r"C:\Users\Danculus\agora\tools\tripo_char\models\yuki\hair_strands_mh3\yuki_hair_ue.abc")
DYE = globals().get("DYE", (0.95, 0.30, 0.50))
WIDTH = globals().get("HAIR_WIDTH", 0.045)  # cm; the imported width read thin and see-through in the viewport
MELANIN = globals().get("HAIR_MELANIN", 0.08)
PKG = "/Game/AgoraChar/Tripo/Yuki"
LEVEL = PKG + "/L_Yuki_Preview"
BP = f"{PKG}/Built_{NAME}/{NAME}/BP_{NAME}"
GEO = f"{PKG}/Geo_{NAME}/{NAME}_Head"
lib = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

opts = unreal.GroomImportOptions()
conv = unreal.GroomConversionSettings()
conv.set_editor_property("rotation", unreal.Vector(0, 0, 0))
conv.set_editor_property("scale", unreal.Vector(1, 1, 1))
opts.set_editor_property("conversion_settings", conv)
task = unreal.AssetImportTask()
task.filename, task.destination_path, task.destination_name = ABC, PKG, "GR_Yuki_Hair"
task.automated, task.replace_existing, task.save, task.options = True, True, False, opts
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
groom = unreal.load_asset(PKG + "/GR_Yuki_Hair")

MI = PKG + "/MI_Yuki_Hair"
mi = unreal.load_asset(MI) if lib.does_asset_exist(MI) else unreal.AssetToolsHelpers.get_asset_tools().create_asset(
    "MI_Yuki_Hair", PKG, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
mel.set_material_instance_parent(mi, unreal.load_asset("/MetaHumanCharacter/Materials/MI_Hair"))
mel.set_material_instance_scalar_parameter_value(mi, "hairMelanin", MELANIN)
mel.set_material_instance_scalar_parameter_value(mi, "hairRedness", 0.0)
mel.set_material_instance_vector_parameter_value(mi, "hairDye", unreal.LinearColor(DYE[0], DYE[1], DYE[2], 1))
mel.update_material_instance(mi)
gm = groom.get_editor_property("hair_groups_materials")
for m in gm:
    m.set_editor_property("material", mi)
groom.set_editor_property("hair_groups_materials", gm)
gr = groom.get_editor_property("hair_groups_rendering")
for r in gr:
    try:
        g = r.get_editor_property("geometry_settings")
        g.set_editor_property("hair_width", WIDTH)
        g.set_editor_property("hair_width_override", True)
        r.set_editor_property("geometry_settings", g)
        sh = r.get_editor_property("shadow_settings")
        sh.set_editor_property("hair_shadow_density", 2.0)
        r.set_editor_property("shadow_settings", sh)
    except Exception as e:  # property names differ between engine versions; report, do not guess
        print("groom rendering settings:", e)
groom.set_editor_property("hair_groups_rendering", gr)
print("groom width", [r.get_editor_property("geometry_settings").get_editor_property("hair_width") for r in groom.get_editor_property("hair_groups_rendering")])

print("level", les.load_level(LEVEL))
for a in eas.get_all_level_actors():
    if a.get_actor_label() in ("Yuki_Head", "Yuki_Hair", "Yuki_Character"):
        eas.destroy_actor(a)
geo = eas.spawn_actor_from_object(unreal.load_asset(GEO), unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
go, ge = geo.get_actor_bounds(False)
eas.destroy_actor(geo)
ch = eas.spawn_actor_from_object(unreal.load_asset(BP), unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
ch.set_actor_label("Yuki_Character")
# A character made from a preset carries the preset's own hair groom; Yuki's hair is ours.
for g in ch.get_components_by_class(unreal.GroomComponent):
    if g.get_name() == "Hair":
        g.set_visibility(False, True)
        g.set_editor_property("groom_asset", None)
print("grooms on the character", [(g.get_name(), g.get_editor_property("groom_asset").get_name() if g.get_editor_property("groom_asset") else None)
                                  for g in ch.get_components_by_class(unreal.GroomComponent)])
face = next(c for c in ch.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == "Face")
fb = face.get_editor_property("bounds") if False else None
fo, fe = unreal.SystemLibrary.get_component_bounds(face)[0:2]
print("geo head hi z", go.z + ge.z, "centre", go.x, go.y, "| face hi z", fo.z + fe.z, "centre", fo.x, fo.y, "extent", fe)
delta = unreal.Vector(fo.x - go.x, fo.y - go.y, (fo.z + fe.z) - (go.z + ge.z))
print("groom offset", delta)
ga = eas.spawn_actor_from_object(groom, delta, unreal.Rotator(0, 0, 0))
ga.set_actor_label("Yuki_Hair")
gc = ga.get_component_by_class(unreal.GroomComponent)
for i in range(max(1, gc.get_num_materials())):  # a fresh groom has no material slots of its own
    gc.set_material(i, mi)
# Width on the component: the asset's own rendering settings came back unchanged (struct copies), 0.01 cm.
descs = []
for d in list(gc.get_editor_property("groom_groups_desc")):
    d.set_editor_property("hair_width", WIDTH)
    d.set_editor_property("hair_width_override", True)
    d.set_editor_property("hair_shadow_density", 2.0)
    d.set_editor_property("hair_shadow_density_override", True)
    descs.append(d)
gc.set_editor_property("groom_groups_desc", descs)
print("hair width", [d.get_editor_property("hair_width") for d in gc.get_editor_property("groom_groups_desc")])
# On the actor root, not the "head" socket: attached to the socket the groom came back beside the head with pitch 90
# after a level reload (2026-11-13). Binding to the head bone is a later step.
ga.attach_to_actor(ch, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
gc.set_cast_shadow(False)   # thin strands throw a speckled shadow on the face (reports/yuki_ue_v6)
for g in ch.get_components_by_class(unreal.GroomComponent):
    if g.get_name() == "Eyebrows":
        g.set_visibility(False)   # the brows are painted from the concept
o, e = ch.get_actor_bounds(False)
print("character bounds lo", o - e, "hi", o + e, "components", [c.get_name() for c in ch.get_components_by_class(unreal.SkeletalMeshComponent)])
for p in (MI, PKG + "/GR_Yuki_Hair", LEVEL):
    print("save", p, lib.save_asset(p, only_if_is_dirty=False))

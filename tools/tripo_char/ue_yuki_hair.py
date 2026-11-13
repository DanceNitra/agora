"""Runs inside Unreal. Replaces Yuki's hair in L_Yuki_Preview without placing the character again (the place script
respawns her and loses the settings made on the level actor): reimports the strand groom, sets the hair material's
colour, the strand width and shadow on the Yuki_Hair actor, and stands the solid ear bodies (yuki_ears.fbx, written
by the strand generator, yuki_hair_strands) as the static mesh actor Yuki_Ears on the character's root.

A wrapper may set ARGS = dict(DIR=<folder with yuki_hair_ue.abc and yuki_ears.fbx>, IMPORT=False to keep the groom
asset and only change the look, DYE=(r, g, b), MELANIN, WIDTH (cm), SHADOW (bool), SHADOW_DENSITY, EAR_RGB, GLOSS (dict of hair material scalars)).
Saves the assets it names and the level.
No file name ending in dot-py may stand in this text: with a wrapper line above it, Unreal's remote execution took the
text up to the first such name for a file path and failed without running anything (2026-11-13)."""
import os

import unreal

_A = globals().pop("ARGS", {})
DIR = _A.get("DIR", r"C:\Users\Danculus\agora\tools\tripo_char\models\yuki\hair_strands_mh6")
IMPORT = _A.get("IMPORT", True)
DYE = _A.get("DYE", (0.80, 0.50, 0.68))       # lavender pink; (0.95, 0.30, 0.50) read as hot pink, (0.86, 0.62, 0.72) as white
MELANIN = _A.get("MELANIN", 0.03)
WIDTH = _A.get("WIDTH", 0.03)                 # cm; 0.045 read as wire, 0.02 too thin to cover
SHADOW = _A.get("SHADOW", True)
SHADOW_DENSITY = _A.get("SHADOW_DENSITY", 0.08)   # 0.5 with the glossy material left near-black patches in the locks
EAR_RGB = _A.get("EAR_RGB", (0.62, 0.36, 0.46))  # linear
# Gloss: scalar parameters of the MetaHuman hair material. The defaults (Scraggle 0.15, HairRoughness 0.37, strong
# melanin variation) read as fluffy and matt; the concept's hair is smooth with broad highlights.
GLOSS = _A.get("GLOSS", {"Scraggle": 0.03, "ScraggleMobile": 0.03, "HairRoughness": 0.30, "RoughnessOverall": 0.45, "RoughnessVariation": 0.10,
                         "MelaninVariationFine": 0.10, "MelaninVariationRough": 0.05, "RIntensity": 0.30})
PKG = "/Game/AgoraChar/Tripo/Yuki"
lib = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
tools = unreal.AssetToolsHelpers.get_asset_tools()

if IMPORT:
    opts = unreal.GroomImportOptions()
    conv = unreal.GroomConversionSettings()
    conv.set_editor_property("rotation", unreal.Vector(0, 0, 0))
    conv.set_editor_property("scale", unreal.Vector(1, 1, 1))
    opts.set_editor_property("conversion_settings", conv)
    task = unreal.AssetImportTask()
    task.filename, task.destination_path, task.destination_name = os.path.join(DIR, "yuki_hair_ue.abc"), PKG, "GR_Yuki_Hair"
    task.automated, task.replace_existing, task.save, task.options = True, True, False, opts
    tools.import_asset_tasks([task])
    print("HAIR groom imported", [str(p) for p in task.imported_object_paths])
    t2 = unreal.AssetImportTask()
    t2.filename, t2.destination_path, t2.destination_name = os.path.join(DIR, "yuki_ears.fbx"), PKG, "SM_Yuki_Ears"
    t2.automated, t2.replace_existing, t2.save = True, True, False
    tools.import_asset_tasks([t2])
    print("HAIR ears imported", [str(p) for p in t2.imported_object_paths])
groom = unreal.load_asset(PKG + "/GR_Yuki_Hair")
mi = unreal.load_asset(PKG + "/MI_Yuki_Hair")
mel.set_material_instance_scalar_parameter_value(mi, "hairMelanin", MELANIN)
mel.set_material_instance_scalar_parameter_value(mi, "hairRedness", 0.0)
have = {str(n) for n in mel.get_scalar_parameter_names(mi)}
for k, v in GLOSS.items():
    if k in have:
        mel.set_material_instance_scalar_parameter_value(mi, k, float(v))
print("HAIR gloss set", sorted(k for k in GLOSS if k in have), "unknown", sorted(k for k in GLOSS if k not in have))
mel.set_material_instance_vector_parameter_value(mi, "hairDye", unreal.LinearColor(DYE[0], DYE[1], DYE[2], 1))
mel.update_material_instance(mi)

EM = PKG + "/M_Yuki_Ear"
em = unreal.load_asset(EM)
if em is None:
    em = tools.create_asset("M_Yuki_Ear", PKG, unreal.Material, unreal.MaterialFactoryNew())
    col = mel.create_material_expression(em, unreal.MaterialExpressionVectorParameter, -400, 0)
    col.set_editor_property("parameter_name", "Color")
    col.set_editor_property("default_value", unreal.LinearColor(EAR_RGB[0], EAR_RGB[1], EAR_RGB[2], 1))
    rough = mel.create_material_expression(em, unreal.MaterialExpressionConstant, -400, 200)
    rough.set_editor_property("r", 0.85)
    mel.connect_material_property(col, "", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.recompile_material(em)

acts = {a.get_actor_label(): a for a in eas.get_all_level_actors()}
ch, ga = acts["Yuki_Character"], acts["Yuki_Hair"]
gc = ga.get_component_by_class(unreal.GroomComponent)
gc.set_groom_asset(groom)
for i in range(max(1, gc.get_num_materials())):
    gc.set_material(i, mi)
descs = []
for d in list(gc.get_editor_property("groom_groups_desc")):
    d.set_editor_property("hair_width", WIDTH)
    d.set_editor_property("hair_width_override", True)
    d.set_editor_property("hair_shadow_density", SHADOW_DENSITY)
    d.set_editor_property("hair_shadow_density_override", True)
    descs.append(d)
gc.set_editor_property("groom_groups_desc", descs)
gc.set_cast_shadow(SHADOW)
print("HAIR component width", [round(d.get_editor_property("hair_width"), 4) for d in gc.get_editor_property("groom_groups_desc")], "shadow", SHADOW)

sm = unreal.load_asset(PKG + "/SM_Yuki_Ears")
if sm is not None:
    ea = acts.get("Yuki_Ears")
    if ea is None:
        ea = eas.spawn_actor_from_object(sm, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
        ea.set_actor_label("Yuki_Ears")
        ea.attach_to_actor(ch, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
    smc = ea.static_mesh_component
    smc.set_static_mesh(sm)
    smc.set_material(0, em)
    smc.set_mobility(unreal.ComponentMobility.MOVABLE)
    o, e = ea.get_actor_bounds(False)
    print("HAIR ears bounds lo", o - e, "hi", o + e)
for p in ([PKG + "/GR_Yuki_Hair", PKG + "/SM_Yuki_Ears"] if IMPORT else []) + [PKG + "/MI_Yuki_Hair", EM, PKG + "/L_Yuki_Preview"]:
    print("HAIR save", p.split("/")[-1], lib.save_asset(p, only_if_is_dirty=False))

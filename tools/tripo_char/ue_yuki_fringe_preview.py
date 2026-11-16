"""Runs inside Unreal. Shows fringe proposals on Yuki without changing any saved asset.

A wrapper sets ARGS = dict(VARIANTS=[(label, dir or None), ...], OUT_DIR=..., SHOT=dict(...)). For each variant with a
dir, the short groom of that strand build (yuki_hair_short_ue.abc: fringe, ear fur, short hair) is imported as a new
unsaved groom, bound to the face and put on the "Fuzz" component; None keeps the current fringe. The shot script ue_yuki_shot
then captures <OUT_DIR>/<label>.png with the SHOT settings. Unreal's remote execution reads the first Python file
extension in a command as the end of a file name, so this script never writes that extension literally. EXTRA=[(label,
shot dict), ...] adds shots after the current fringe is back, for example the back of the head (YAW=180). At the end the Fuzz component gets its original groom, binding
and materials back. Nothing is saved: the editor is closed after the preview and the proposals are gone."""
import os

import unreal

_A = globals().pop("ARGS", {})
PKG = "/Game/AgoraChar/Tripo/Yuki"
HERE = r"C:\Users\Danculus\agora\tools\tripo_char"
tools = unreal.AssetToolsHelpers.get_asset_tools()
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
# The caller has loaded L_Yuki_Preview already; loading it again fails once a warm-up shot has dirtied the level.
ch = next(a for a in eas.get_all_level_actors() if a.get_actor_label() == "Yuki_Character")
face = next(c for c in ch.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == "Face")
fuzz = next(c for c in ch.get_components_by_class(unreal.GroomComponent) if c.get_name() == "Fuzz")
orig = (fuzz.get_editor_property("groom_asset"), fuzz.get_editor_property("binding_asset"),
        [fuzz.get_material(i) for i in range(fuzz.get_num_materials())], list(fuzz.get_editor_property("groom_groups_desc")))
# Wrinkle check (owner 2026-11-15: forehead, between the brows, nose bridge): which materials the face wears and
# whether any of them has the MetaHuman animated wrinkle maps (parameters with "wm" or "wrinkle" in the name).
for i in range(face.get_num_materials()):
    m = face.get_material(i)
    if m is None:
        continue
    names = []
    for getter in ("get_scalar_parameter_names", "get_texture_parameter_names", "get_vector_parameter_names"):
        try:
            names += [str(n) for n in getattr(unreal.MaterialEditingLibrary, getter)(m)]
        except Exception:
            pass
    hits = [n for n in names if "wm" in n.lower() or "wrinkle" in n.lower() or "animated" in n.lower()]
    base = m
    while isinstance(base, unreal.MaterialInstance) and base.get_editor_property("parent"):
        base = base.get_editor_property("parent")
    print("WRINKLE slot", i, face.get_material_slot_names()[i] if i < len(face.get_material_slot_names()) else "?", m.get_path_name(),
          "base", base.get_path_name(), "params", len(names), "wrinkle params", hits[:12], flush=True)
shot_code = open(os.path.join(HERE, "ue_yuki_shot" + os.extsep + "py"), encoding="utf-8").read()
for i, (label, d) in enumerate(_A["VARIANTS"]):
    if d:
        opts, conv = unreal.GroomImportOptions(), unreal.GroomConversionSettings()
        conv.set_editor_property("rotation", unreal.Vector(0, 0, 0))
        conv.set_editor_property("scale", unreal.Vector(1, 1, 1))
        opts.set_editor_property("conversion_settings", conv)
        t = unreal.AssetImportTask()
        t.filename, t.destination_path, t.destination_name = os.path.join(d, "yuki_hair_short_ue.abc"), PKG + "/FringePreview", f"GR_FringeP{i}"
        t.automated, t.replace_existing, t.save, t.options = True, True, False, opts
        tools.import_asset_tasks([t])
        g = unreal.load_asset(f"{PKG}/FringePreview/GR_FringeP{i}")
        b = unreal.GroomLibrary.create_new_groom_binding_asset_with_path(f"{PKG}/FringePreview/GB_FringeP{i}", g, face.get_skeletal_mesh_asset(), 100, None, 0)
        fuzz.set_groom_asset(g)
        fuzz.set_binding_asset(b)
        for k, m in enumerate(orig[2]):
            fuzz.set_material(k, m)
        ds = []
        for dd in list(fuzz.get_editor_property("groom_groups_desc")):
            if orig[3]:
                dd.set_editor_property("hair_width", orig[3][0].get_editor_property("hair_width"))
                dd.set_editor_property("hair_width_override", True)
                dd.set_editor_property("hair_shadow_density", orig[3][0].get_editor_property("hair_shadow_density"))
                dd.set_editor_property("hair_shadow_density_override", True)
            ds.append(dd)
        fuzz.set_editor_property("groom_groups_desc", ds)
    else:
        fuzz.set_groom_asset(orig[0])
        fuzz.set_binding_asset(orig[1])
    shot = dict(_A.get("SHOT", {}))
    shot["OUT"] = os.path.join(_A["OUT_DIR"], f"{label}.png")
    exec(shot_code, {"ARGS": shot, "__name__": "__shot__"})
    print("FRINGE PREVIEW", label, shot["OUT"], flush=True)
fuzz.set_groom_asset(orig[0])
fuzz.set_binding_asset(orig[1])
for k, m in enumerate(orig[2]):
    fuzz.set_material(k, m)
print("FRINGE PREVIEW restored", orig[0].get_name() if orig[0] else None)
hair = next(c for c in ch.get_components_by_class(unreal.GroomComponent) if c.get_name() == "Hair")
orig_long = (hair.get_editor_property("groom_asset"), hair.get_editor_property("binding_asset"),
             [hair.get_material(i) for i in range(hair.get_num_materials())])
# LONG_VARIANTS=[(label, dir)]: the long groom of that build goes on the "Hair" component (no binding: a still in the
# rest pose needs none), then every EXTRA shot is taken as <label>_<extra label>. The current long groom comes back after.
for li, (llabel, ld) in enumerate([("current", None)] + list(_A.get("LONG_VARIANTS", []))):
    if ld:
        opts, conv = unreal.GroomImportOptions(), unreal.GroomConversionSettings()
        conv.set_editor_property("rotation", unreal.Vector(0, 0, 0))
        conv.set_editor_property("scale", unreal.Vector(1, 1, 1))
        opts.set_editor_property("conversion_settings", conv)
        t = unreal.AssetImportTask()
        t.filename, t.destination_path, t.destination_name = os.path.join(ld, "yuki_hair_long_ue.abc"), PKG + "/FringePreview", f"GR_LongP{li}"
        t.automated, t.replace_existing, t.save, t.options = True, True, False, opts
        tools.import_asset_tasks([t])
        hair.set_binding_asset(None)
        hair.set_groom_asset(unreal.load_asset(f"{PKG}/FringePreview/GR_LongP{li}"))
        for k, m in enumerate(orig_long[2]):
            hair.set_material(k, m)
    for label, extra in _A.get("EXTRA", []):
        shot = dict(extra)
        shot["OUT"] = os.path.join(_A["OUT_DIR"], f"{llabel}_{label}.png")
        exec(shot_code, {"ARGS": shot, "__name__": "__shot__"})
        print("FRINGE PREVIEW extra", llabel, label, shot["OUT"], flush=True)
hair.set_groom_asset(orig_long[0])
hair.set_binding_asset(orig_long[1])
for k, m in enumerate(orig_long[2]):
    hair.set_material(k, m)

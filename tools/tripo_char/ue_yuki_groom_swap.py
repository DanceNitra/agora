"""Runs inside Unreal. Swaps the groom on one of Yuki's groom components for a strand build, or puts the original back.
Saves nothing.

A wrapper sets ARGS = dict(COMP="Hair" or "Fuzz", ABC=<alembic file or None>, NAME=<asset name>, STATE=<json file>).
With ABC, the component's original groom, binding and materials are written to STATE (once), the file is imported as
an unsaved groom under /Game/AgoraChar/Tripo/Yuki/FringePreview and set on the component without a binding (a still in
the rest pose needs none). Without ABC, the component gets back what STATE holds. Groom building runs while the
editor ticks, so the caller waits between this call and any shot."""
import json
import os

import unreal

_A = globals().pop("ARGS", {})
PKG = "/Game/AgoraChar/Tripo/Yuki"
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
ch = next(a for a in eas.get_all_level_actors() if a.get_actor_label() == "Yuki_Character")
comp = next(c for c in ch.get_components_by_class(unreal.GroomComponent) if c.get_name() == _A["COMP"])
state = _A["STATE"]
if _A.get("ABC"):
    if not os.path.exists(state):
        g, b = comp.get_editor_property("groom_asset"), comp.get_editor_property("binding_asset")
        json.dump(dict(groom=g.get_path_name() if g else None, binding=b.get_path_name() if b else None,
                       mats=[m.get_path_name() if m else None for m in (comp.get_material(i) for i in range(comp.get_num_materials()))]),
                  open(state, "w"))
    st = json.load(open(state))
    opts, conv = unreal.GroomImportOptions(), unreal.GroomConversionSettings()
    conv.set_editor_property("rotation", unreal.Vector(0, 0, 0))
    conv.set_editor_property("scale", unreal.Vector(1, 1, 1))
    opts.set_editor_property("conversion_settings", conv)
    t = unreal.AssetImportTask()
    t.filename, t.destination_path, t.destination_name = _A["ABC"], PKG + "/FringePreview", _A["NAME"]
    t.automated, t.replace_existing, t.save, t.options = True, True, False, opts
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    g = unreal.load_asset(f"{PKG}/FringePreview/{_A['NAME']}")
    # The long hair file has no guide strands: like ue_yuki_hair_split, let the groom generate them, or it never builds
    # and the component shows a bald head (back preview, 2026-11-15: 20 minutes of waiting, no hair).
    it = list(g.get_editor_property("hair_groups_interpolation"))
    for i, x in enumerate(it):
        s2 = x.get_editor_property("interpolation_settings")
        s2.set_editor_property("guide_type", unreal.GroomGuideType.GENERATED)
        s2.set_editor_property("hair_to_guide_density", 0.03)
        x.set_editor_property("interpolation_settings", s2)
        it[i] = x
    g.set_editor_property("hair_groups_interpolation", it)
    comp.set_binding_asset(None)
    comp.set_groom_asset(g)
    for k, m in enumerate(st["mats"]):
        if m:
            comp.set_material(k, unreal.load_asset(m))
    print("SWAP set", _A["COMP"], _A["NAME"], flush=True)
else:
    st = json.load(open(state))
    comp.set_groom_asset(unreal.load_asset(st["groom"]) if st["groom"] else None)
    comp.set_binding_asset(unreal.load_asset(st["binding"]) if st["binding"] else None)
    for k, m in enumerate(st["mats"]):
        if m:
            comp.set_material(k, unreal.load_asset(m))
    print("SWAP restored", _A["COMP"], st["groom"], flush=True)

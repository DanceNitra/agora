"""Runs inside Unreal. The other baked maps of the MetaHuman body (normal, roughness and the like), out and back in.

The body's base colour had its painted underwear filled with skin (yuki_body_skin_fill), but the top still showed on
the chest as a paler band in bright light (stills of 2026-11-14): the other baked maps carry the cloth too.
STEP "export" lists every texture parameter of the body material instances and writes each texture to DIR as
map_<parameter>.png, with maps.json (parameter, asset, sRGB, compression). STEP "apply" imports DIR/fill_<parameter>.png
for every parameter that has such a file and points the materials at it.
A wrapper sets ARGS = dict(STEP=..., DIR=..., NAME=...). Saves only the assets it names."""
import json
import os
import re

import unreal

_A = globals().pop("ARGS", {})
STEP, NAME, DIR = _A.get("STEP", "export"), _A.get("NAME", "MHC_Yuki_v5"), _A["DIR"]
PKG = "/Game/AgoraChar/Tripo/Yuki"
BUILT = f"{PKG}/Built_{NAME}/{NAME}"
lib, mel = unreal.EditorAssetLibrary, unreal.MaterialEditingLibrary
os.makedirs(DIR, exist_ok=True)
ms = []
for a in lib.list_assets(f"{BUILT}/Body", recursive=True):
    if "MI_Body" in a:
        m = lib.load_asset(a.split(".")[0])
        if isinstance(m, unreal.MaterialInstanceConstant):
            ms.append(m)
safe = lambda s_: re.sub(r"[^A-Za-z0-9]+", "_", s_).strip("_")
if STEP == "export":
    info = {}
    for m in ms:
        for pn in mel.get_texture_parameter_names(m):
            t = mel.get_material_instance_texture_parameter_value(m, pn)
            key = safe(str(pn))
            if t is None or key in info:
                continue
            task = unreal.AssetExportTask()
            for k, v in (("object", t), ("filename", os.path.join(DIR, f"map_{key}.png")), ("automated", True), ("prompt", False), ("replace_identical", True)):
                task.set_editor_property(k, v)
            ok = unreal.Exporter.run_asset_export_task(task)
            info[key] = {"parameter": str(pn), "texture": t.get_path_name(), "ok": bool(ok), "srgb": bool(t.get_editor_property("srgb")),
                         "compression": str(t.get_editor_property("compression_settings"))}
    json.dump(info, open(os.path.join(DIR, "maps.json"), "w"), indent=1)
    print("BODYMAPS materials", [m.get_name() for m in ms], "exported", {k: (v["ok"], v["texture"].split("/")[-1].split(".")[0], v["compression"].split(".")[-1].split(":")[0]) for k, v in info.items()})
else:
    info = json.load(open(os.path.join(DIR, "maps.json")))
    for key, v in info.items():
        png = os.path.join(DIR, f"fill_{key}.png")
        if not os.path.exists(png):
            continue
        like = unreal.load_asset(v["texture"].split(".")[0])
        it = unreal.AssetImportTask()
        for k, val in (("filename", png), ("destination_path", PKG + "/Tex"), ("destination_name", "T_Yuki_body_" + key), ("automated", True), ("replace_existing", True), ("save", False)):
            it.set_editor_property(k, val)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([it])
        tex = lib.load_asset(f"{PKG}/Tex/T_Yuki_body_{key}")
        tex.set_editor_property("srgb", like.get_editor_property("srgb"))
        tex.set_editor_property("compression_settings", like.get_editor_property("compression_settings"))
        tex.set_editor_property("virtual_texture_streaming", like.get_editor_property("virtual_texture_streaming"))
        lib.save_loaded_asset(tex, only_if_is_dirty=False)
        for m in ms:
            mel.set_material_instance_texture_parameter_value(m, v["parameter"], tex)
            mel.update_material_instance(m)
            lib.save_loaded_asset(m, only_if_is_dirty=False)
        print("BODYMAPS applied", key, "->", tex.get_name(), "to", len(ms), "materials")

"""Agora Makeup inside Unreal: paint a look onto the baked face textures of a built MetaHuman.

How it works, so nothing needs a rebuild:
1. Find the face skin material instances of the target (the selected actor's "Face" component, or a folder).
2. The first time, export the ORIGINAL "Basecolor Baked VT" and "SRMF Baked VT" textures to
   <Project>/Saved/AgoraMakeup/<key>/ and remember them, so looks never stack on each other.
3. Paint the look out of process (cli.py with OpenCV) from those originals.
4. Import the result under fixed names in /Game/AgoraMakeup/<key>/ (overwritten each time, so memory and
   disk do not grow with every try) and point the materials at it.
reset() points the materials back at the originals.
"""
import json
import os
import subprocess

import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(HERE, "config.json")))
lib = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
PARAMS = {"BC": "Basecolor Baked VT", "SRMF": "SRMF Baked VT"}


def _saved(key):
    d = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), "AgoraMakeup", key)
    os.makedirs(d, exist_ok=True)
    return d


def _cli(*args):
    r = subprocess.run([CFG["python"], os.path.join(CFG["tool_dir"], "cli.py")] + list(args),
                       capture_output=True, text=True, timeout=600)
    if r.returncode:
        raise RuntimeError("agora_makeup cli failed: " + r.stderr[-2000:])
    return json.loads(r.stdout.strip().splitlines()[-1])


def list_looks():
    return _cli("list")


def face_materials_of_actor(actor):
    mats = []
    for comp in actor.get_components_by_class(unreal.SkeletalMeshComponent):
        if "face" not in comp.get_name().lower():
            continue
        for m in comp.get_materials():
            if m and isinstance(m, unreal.MaterialInstanceConstant) and "Skin" in m.get_name():
                mats.append(m)
    return mats


def face_materials_in_folder(folder):
    return [lib.load_asset(a) for a in lib.list_assets(folder, recursive=True) if "MI_Face_Skin" in a]


def _key_for(mats):
    path = mats[0].get_path_name()
    parts = path.split("/")
    return parts[-4] if len(parts) > 4 else "Face"


def _export(tex, png):
    t = unreal.AssetExportTask()
    t.set_editor_property("object", tex)
    t.set_editor_property("filename", png)
    t.set_editor_property("automated", True)
    t.set_editor_property("prompt", False)
    t.set_editor_property("replace_identical", True)
    if not unreal.Exporter.run_asset_export_task(t):
        raise RuntimeError("export failed: " + tex.get_path_name())


def _originals(mats, key, refresh=False):
    d = _saved(key)
    side = os.path.join(d, "originals.json")
    if os.path.exists(side) and not refresh:
        return json.load(open(side)), d
    orig = {}
    for k, p in PARAMS.items():
        for m in mats:
            t = mel.get_material_instance_texture_parameter_value(m, p)
            if t and "/AgoraMakeup/" not in t.get_path_name():
                orig[k] = t.get_path_name()
                _export(t, os.path.join(d, "base_%s.png" % k))
                break
    if "BC" not in orig:
        raise RuntimeError("no baked basecolor found on " + mats[0].get_path_name())
    json.dump(orig, open(side, "w"), indent=1)
    return orig, d


def _import(png, key, name, like):
    dest = "/Game/AgoraMakeup/" + key
    it = unreal.AssetImportTask()
    it.set_editor_property("filename", png)
    it.set_editor_property("destination_path", dest)
    it.set_editor_property("destination_name", name)
    it.set_editor_property("automated", True)
    it.set_editor_property("replace_existing", True)
    it.set_editor_property("save", False)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([it])
    tex = lib.load_asset(dest + "/" + name)
    tex.set_editor_property("srgb", like.get_editor_property("srgb"))
    tex.set_editor_property("compression_settings", like.get_editor_property("compression_settings"))
    tex.set_editor_property("virtual_texture_streaming", True)
    lib.save_loaded_asset(tex, only_if_is_dirty=False)
    return tex


def body_materials_for(face_folder):
    body = face_folder.rsplit("/", 1)[0] + "/Body"
    return [lib.load_asset(a) for a in lib.list_assets(body, recursive=True) if "MI_Body" in a]


def apply(look_id, actor=None, folder=None, refresh_base=False):
    """Paint look_id onto the target. Target: actor (default: the first selected actor) or a built folder."""
    if folder:
        mats = face_materials_in_folder(folder)
    else:
        actor = actor or (unreal.EditorLevelLibrary.get_selected_level_actors() or [None])[0]
        if actor is None:
            raise RuntimeError("select a MetaHuman in the level, or pass folder=")
        mats = face_materials_of_actor(actor)
    if not mats:
        raise RuntimeError("no face skin materials found")
    key = _key_for(mats)
    orig, d = _originals(mats, key, refresh_base)
    out_bc, out_srmf = os.path.join(d, "look_BC.png"), os.path.join(d, "look_SRMF.png")
    args = ["paint", "--look", look_id, "--bc", os.path.join(d, "base_BC.png"), "--out-bc", out_bc]
    if "SRMF" in orig:
        args += ["--srmf", os.path.join(d, "base_SRMF.png"), "--out-srmf", out_srmf]
    # METHOD.md rule 2: the base evens the BODY texture with the same colour transform as the face
    bmats = body_materials_for(mats[0].get_path_name().split("/Materials/")[0].rsplit("/", 1)[0] + "/Face") if folder is None else body_materials_for(folder)
    borig = None
    if bmats:
        bside = os.path.join(d, "body_originals.json")
        if os.path.exists(bside) and not refresh_base:
            borig = json.load(open(bside))
        else:
            t = mel.get_material_instance_texture_parameter_value(bmats[0], PARAMS["BC"])
            if t and "/AgoraMakeup/" not in t.get_path_name():
                _export(t, os.path.join(d, "base_body_BC.png"))
                borig = {"BC": t.get_path_name()}
                json.dump(borig, open(bside, "w"))
    if borig:
        args += ["--body-bc", os.path.join(d, "base_body_BC.png"), "--out-body-bc", os.path.join(d, "look_body_BC.png")]
    res = _cli(*args)
    if borig:
        btex = _import(os.path.join(d, "look_body_BC.png"), key, "T_%s_Makeup_Body_BC" % key, lib.load_asset(borig["BC"]))
        for m in bmats:
            mel.set_material_instance_texture_parameter_value(m, PARAMS["BC"], btex)
            mel.update_material_instance(m)
            lib.save_loaded_asset(m, only_if_is_dirty=False)
    new = {"BC": _import(out_bc, key, "T_%s_Makeup_BC" % key, lib.load_asset(orig["BC"]))}
    if "SRMF" in orig:
        new["SRMF"] = _import(out_srmf, key, "T_%s_Makeup_SRMF" % key, lib.load_asset(orig["SRMF"]))
    n = 0
    for m in mats:
        for k, p in PARAMS.items():
            cur = mel.get_material_instance_texture_parameter_value(m, p)
            if k in new and cur and (cur.get_path_name() == orig.get(k) or "/AgoraMakeup/" in cur.get_path_name()):
                mel.set_material_instance_texture_parameter_value(m, p, new[k])
                n += 1
        mel.update_material_instance(m)
        lib.save_loaded_asset(m, only_if_is_dirty=False)
    unreal.log("Agora Makeup: %s on %s (%d texture slots)" % (res["look"], key, n))
    return {"look": res["look"], "key": key, "slots": n}


def reset(actor=None, folder=None):
    mats = face_materials_in_folder(folder) if folder else face_materials_of_actor(
        actor or unreal.EditorLevelLibrary.get_selected_level_actors()[0])
    key = _key_for(mats)
    bside = os.path.join(_saved(key), "body_originals.json")
    if os.path.exists(bside):
        borig = json.load(open(bside))
        for m in body_materials_for(folder) if folder else []:
            mel.set_material_instance_texture_parameter_value(m, PARAMS["BC"], lib.load_asset(borig["BC"]))
            mel.update_material_instance(m)
            lib.save_loaded_asset(m, only_if_is_dirty=False)
    orig = json.load(open(os.path.join(_saved(key), "originals.json")))
    for m in mats:
        for k, p in PARAMS.items():
            cur = mel.get_material_instance_texture_parameter_value(m, p)
            if cur and "/AgoraMakeup/" in cur.get_path_name() and k in orig:
                mel.set_material_instance_texture_parameter_value(m, p, lib.load_asset(orig[k]))
        mel.update_material_instance(m)
        lib.save_loaded_asset(m, only_if_is_dirty=False)
    return {"reset": key}


def compare(n=1000, workers=16):
    """Generate n looks, paint them on the frontal face view, rank them; returns the sheet path and the top ids."""
    out = os.path.join(_saved("compare"), "compare_top.png")
    r = subprocess.run([CFG["python"], os.path.join(CFG["tool_dir"], "compare.py"), "--n", str(n), "--out", out,
                        "--workers", str(workers)], capture_output=True, text=True, timeout=600)
    if r.returncode:
        raise RuntimeError("compare failed: " + r.stderr[-2000:])
    res = json.loads(r.stdout.strip().splitlines()[-1])
    unreal.log("Agora Makeup: compared %d looks in %.1f s, sheet %s" % (res["looks"], res["painted_and_ranked_s"], out))
    os.startfile(out)
    return res


def apply_rank(rank=1, actor=None, folder=None):
    """Apply the look at this rank from the last comparison."""
    rk = json.load(open(os.path.join(_saved("compare"), "compare_top_ranking.json")))
    return apply(rk[rank - 1]["id"], actor=actor, folder=folder)

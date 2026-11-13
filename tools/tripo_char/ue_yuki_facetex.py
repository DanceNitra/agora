"""Runs inside Unreal. Step "export": writes the baked base colour of the built MetaHuman's face and body to disk.
Step "apply": imports the composited face and body base colour and points the face and body skin materials at them.
The method is the make-up tool's (tools/agora_makeup): the baked "Basecolor Baked VT" parameter of MI_Face_Skin* and
MI_Body*. A wrapper sets STEP ("export" or "apply") and may set NAME and DIR. Saves only the assets it names."""
import json
import os

import unreal

STEP = globals().get("STEP", "export")
NAME = globals().get("NAME", "MHC_Yuki_v5")
DIR = globals().get("DIR", r"C:\Users\Danculus\agora\tools\tripo_char\models\yuki\face_tex_v1")
PKG = "/Game/AgoraChar/Tripo/Yuki"
BUILT = f"{PKG}/Built_{NAME}/{NAME}"
PARAM = "Basecolor Baked VT"
lib = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
os.makedirs(DIR, exist_ok=True)


def mats(sub, key):
    out = []
    for a in lib.list_assets(f"{BUILT}/{sub}", recursive=True):
        if key in a:
            m = lib.load_asset(a.split(".")[0])
            if isinstance(m, unreal.MaterialInstanceConstant):
                out.append(m)
    return out


face, body = mats("Face", "MI_Face_Skin"), mats("Body", "MI_Body")
print("face mats", [m.get_name() for m in face], "body mats", [m.get_name() for m in body])
if STEP == "export":
    info = {}
    for tag, ms in (("face", face), ("body", body)):
        for m in ms:
            t = mel.get_material_instance_texture_parameter_value(m, PARAM)
            if t and "/Tex/" not in t.get_path_name():
                task = unreal.AssetExportTask()
                task.set_editor_property("object", t)
                task.set_editor_property("filename", os.path.join(DIR, f"base_{tag}_BC.png"))
                task.set_editor_property("automated", True)
                task.set_editor_property("prompt", False)
                task.set_editor_property("replace_identical", True)
                ok = unreal.Exporter.run_asset_export_task(task)
                info[tag] = {"texture": t.get_path_name(), "ok": bool(ok), "size": [t.blueprint_get_size_x(), t.blueprint_get_size_y()],
                             "srgb": bool(t.get_editor_property("srgb"))}
                break
    json.dump(info, open(os.path.join(DIR, "originals.json"), "w"), indent=1)
    print("exported", info)
else:
    orig = json.load(open(os.path.join(DIR, "originals.json")))
    for tag, ms in (("face", face), ("body", body)):
        png = os.path.join(DIR, f"yuki_{tag}_BC.png")
        if not os.path.exists(png) or tag not in orig:
            print("skip", tag)
            continue
        like = unreal.load_asset(orig[tag]["texture"].split(".")[0])
        it = unreal.AssetImportTask()
        it.set_editor_property("filename", png)
        it.set_editor_property("destination_path", PKG + "/Tex")
        it.set_editor_property("destination_name", f"T_Yuki_{tag}_BC")
        it.set_editor_property("automated", True)
        it.set_editor_property("replace_existing", True)
        it.set_editor_property("save", False)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([it])
        tex = lib.load_asset(f"{PKG}/Tex/T_Yuki_{tag}_BC")
        tex.set_editor_property("srgb", like.get_editor_property("srgb"))
        tex.set_editor_property("compression_settings", like.get_editor_property("compression_settings"))
        tex.set_editor_property("virtual_texture_streaming", True)
        lib.save_loaded_asset(tex, only_if_is_dirty=False)
        for m in ms:
            mel.set_material_instance_texture_parameter_value(m, PARAM, tex)
            mel.update_material_instance(m)
            lib.save_loaded_asset(m, only_if_is_dirty=False)
        print("applied", tag, tex.get_path_name(), "to", len(ms), "materials")

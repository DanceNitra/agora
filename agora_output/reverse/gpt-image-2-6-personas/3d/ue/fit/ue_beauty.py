# Runs INSIDE Unreal. Applies beauty_cfg.json to MH_Depesa: skin, makeup, eyes (both), eyelashes.
# Paths are dotted struct fields, values are numbers, bools, enum names or [r, g, b, a] colours.
import json
import unreal

F = r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit"
cfg = json.load(open(F + r"\beauty_cfg.json"))
mhs = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
ch = unreal.EditorAssetLibrary.load_asset("/Game/Companions/MetaHuman/MH_Depesa")
mhs.try_add_object_to_edit(ch) if not mhs.is_object_added_for_editing(ch) else None
ENUMS = {"type": None, "pattern": unreal.MetaHumanCharacterEyesIrisPattern}


def conv(holder, name, v):
    cur = holder.get_editor_property(name)
    if isinstance(v, list):
        return unreal.LinearColor(*v)
    if isinstance(v, str):
        return getattr(type(cur), v)
    return type(cur)(v) if isinstance(cur, (int, float, bool)) else v


def set_path(root, path, v):
    parts = path.split(".")
    chain = [root]
    for p in parts[:-1]:
        chain.append(chain[-1].get_editor_property(p))
    chain[-1].set_editor_property(parts[-1], conv(chain[-1], parts[-1], v))
    for i in range(len(parts) - 2, -1, -1):
        chain[i].set_editor_property(parts[i], chain[i + 1])


if cfg.get("skin"):
    s = ch.get_editor_property("skin_settings")
    for k, v in cfg["skin"].items():
        set_path(s, k, v)
    mhs.commit_skin_settings(ch, s)
if cfg.get("makeup"):
    m = ch.get_editor_property("makeup_settings")
    for k, v in cfg["makeup"].items():
        set_path(m, k, v)
    mhs.commit_makeup_settings(ch, m)
if cfg.get("eyes"):
    e = ch.get_editor_property("eyes_settings")
    for side in ("eye_left", "eye_right"):
        for k, v in cfg["eyes"].items():
            set_path(e, side + "." + k, v)
    mhs.commit_eyes_settings(ch, e)
if cfg.get("head"):
    h = ch.get_editor_property("head_model_settings")
    for k, v in cfg["head"].items():
        set_path(h, k, v)
    mhs.commit_head_model_settings(ch, h)
print("BEAUTY ok", ch.get_editor_property("skin_settings").get_editor_property("skin").get_editor_property("u"))

# Runs INSIDE Unreal: add the brow layer (browlayer_cfg.json -> layer json from the brow layer script) on top of the
# Speech2Face keys of the render sequence, then apply the limits from the research file: clamp raiseIn 0.45,
# raiseOut 0.55, down 0.4; scale raiseIn by (1 - down) when down > 0.15 (no sad AU1+4 brow); and the Duchenne rule
# cheekRaise >= 0.6 x cornerPull. Original key values are kept in browlayer_backup.json, so every run starts from
# the untouched Speech2Face values (re-runnable, and restorable with "restore": true).
import json
import os
import unreal

F = r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit"
CFG = json.load(open(os.path.join(F, "browlayer_cfg.json")))
lib = unreal.EditorAssetLibrary
seq = lib.load_asset(CFG["seq"])
face = [b for b in seq.get_bindings() if str(b.get_display_name()) == "Face"][0].get_tracks()[0].get_sections()[0]
LAY = json.load(open(CFG["layer"]))["layers"]
bk_path = os.path.join(F, "browlayer_backup.json")
backup = json.load(open(bk_path)) if os.path.exists(bk_path) else {}
WANT = ("brow_raiseIn", "brow_raiseOut", "brow_down", "brow_lateral", "mouth_cornerPull", "eye_cheekRaise")
chans = {}
for ch in face.get_all_channels():
    nm = str(ch.get_name())
    base = nm.rsplit("_", 1)[0]  # CTRL_L_brow_raiseIn_3 -> CTRL_L_brow_raiseIn
    if ch.get_num_keys() and any(base.endswith(w) for w in WANT) and base.startswith(("CTRL_L_", "CTRL_R_")):
        chans[base] = ch
        if base not in backup:  # key by base name: the numeric suffix changes between reads
            backup[base] = [k.get_value() for k in ch.get_keys()]
json.dump(backup, open(bk_path, "w"))
print("BROW channels", sorted(chans))


def orig(base):
    ch = chans[base]
    return {k.get_time().frame_number.value: v for k, v in zip(ch.get_keys(), backup[base])}


n = 0
for sd in ("L", "R"):
    P = "CTRL_%s_" % sd
    o = {w: orig(P + w) for w in WANT if P + w in chans}
    for base, ch in ((P + w, chans[P + w]) for w in WANT if P + w in chans):
        w = base[len(P):]
        for k in ch.get_keys():
            f = k.get_time().frame_number.value
            if CFG.get("restore"):
                k.set_value(o[w][f]); n += 1
                continue
            add = lambda key: (LAY[key][f] if 0 <= f < len(LAY[key]) else 0.0)
            down = min(CFG.get("max_down", 0.4), o.get("brow_down", {}).get(f, 0.0) + add("down_" + sd))
            if w == "brow_down":
                v = down
            elif w == "brow_lateral":
                v = min(1.0, o[w][f] + add("lateral_" + sd))
            elif w == "brow_raiseIn":
                v = min(0.45, o[w][f] + add("raiseIn_" + sd))
                if down > 0.15:
                    v *= (1 - down)
            elif w == "brow_raiseOut":
                v = min(0.55, o[w][f] + add("raiseOut_" + sd))
            elif w == "eye_cheekRaise":
                cp = o.get("mouth_cornerPull", {}).get(f, 0.0)
                v = max(o[w][f], 0.6 * cp) if cp > 0.2 else o[w][f]
            else:
                v = o[w][f]
            k.set_value(max(0.0, min(1.0, v))); n += 1
lib.save_loaded_asset(seq, only_if_is_dirty=False)
print("BROW keys set", n, "restore" if CFG.get("restore") else "applied")

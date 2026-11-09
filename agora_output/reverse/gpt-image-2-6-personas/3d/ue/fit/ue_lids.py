# Runs INSIDE Unreal: heavier, sultry upper lids. Adds a constant amount to every eye_blink key of the render sequence.
# Original key values are written to lids_backup.json first, so they can be restored.
import json, os, unreal
F = r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit"
SEQ = "/Game/Companions/Lipsync/LS_KF_Depesa_lajk_confidence_v5"
LID = 0.18
lib = unreal.EditorAssetLibrary
seq = lib.load_asset(SEQ)
face = [b for b in seq.get_bindings() if str(b.get_display_name()) == "Face"][0].get_tracks()[0].get_sections()[0]
bk = os.path.join(F, "lids_backup.json")
backup = json.load(open(bk)) if os.path.exists(bk) else {}
first = not backup
n = 0
for ch in face.get_all_channels():
    nm = str(ch.get_name())
    if "eye_blink" not in nm or ch.get_num_keys() == 0:
        continue
    keys = ch.get_keys()
    if first:
        backup[nm] = [k.get_value() for k in keys]
    for k, v0 in zip(keys, backup[nm]):
        k.set_value(min(1.0, max(0.0, v0) + LID)); n += 1
if first:
    json.dump(backup, open(bk, "w"))
lib.save_loaded_asset(seq, only_if_is_dirty=False)
print("LID", LID, "keys", n, "channels", len(backup))

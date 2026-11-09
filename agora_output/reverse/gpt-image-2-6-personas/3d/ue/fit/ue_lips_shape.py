# Runs INSIDE Unreal: back up the MH_DepesaKF face coefficients, move the lip landmarks from lips_shape_cfg.json,
# commit the face state, and report the landmark change. Restore: set_face_model_coefficients from the backup.
import unreal, json, os
F = r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit"
cfg = json.load(open(F + r"\lips_shape_cfg.json"))
mhs = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
ch = unreal.EditorAssetLibrary.load_asset("/Game/Companions/MetaHuman/MH_DepesaKF")
mhs.try_add_object_to_edit(ch) if not mhs.is_object_added_for_editing(ch) else None
bk = F + r"\kf_coeffs_backup_before_lips.json"
if not os.path.exists(bk):
    json.dump(list(mhs.get_face_model_coefficients(ch)), open(bk, "w"))
L0 = [[p.x, p.y, p.z] for p in mhs.get_face_landmarks(ch)]
idx = [int(k) for k in cfg["moves"]]
d = [unreal.Vector(*cfg["moves"][str(i)]) for i in idx]
mhs.translate_face_landmarks(ch, idx, d)
L1 = [[p.x, p.y, p.z] for p in mhs.get_face_landmarks(ch)]
for i in idx:
    print("LIPS moved", i, [round(b - a, 3) for a, b in zip(L0[i], L1[i])], "asked", cfg["moves"][str(i)])
other = max(max(abs(b - a) for a, b in zip(L0[j], L1[j])) for j in range(len(L0)) if j not in idx)
far = max(max(abs(b - a) for a, b in zip(L0[j], L1[j])) for j in range(len(L0)) if L0[j][2] > 165)
print("LIPS max change other landmarks", round(other, 3), "above z165 (eyes/brows/nose)", round(far, 3))
mhs.commit_face_state(ch)
json.dump(L1, open(F + r"\kf_landmarks3d_lips.json", "w"))
print("LIPS committed, saved", unreal.EditorAssetLibrary.save_loaded_asset(ch, only_if_is_dirty=False))

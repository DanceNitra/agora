# Runs INSIDE Unreal: restore the MH_DepesaKF face shape from the coefficients saved before the lip reshape.
import unreal, json
F = r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit"
mhs = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
ch = unreal.EditorAssetLibrary.load_asset("/Game/Companions/MetaHuman/MH_DepesaKF")
mhs.try_add_object_to_edit(ch) if not mhs.is_object_added_for_editing(ch) else None
mhs.set_face_model_coefficients(ch, json.load(open(F + r"\kf_coeffs_backup_before_lips.json")))
mhs.commit_face_state(ch)
L0 = json.load(open(F + r"\kf_landmarks3d.json"))
L = [[p.x, p.y, p.z] for p in mhs.get_face_landmarks(ch)]
print("LIPS restore max landmark diff vs original cm", round(max(abs(a - b) for u, w in zip(L0, L) for a, b in zip(u, w)), 4))
print("LIPS saved", unreal.EditorAssetLibrary.save_loaded_asset(ch, only_if_is_dirty=False))

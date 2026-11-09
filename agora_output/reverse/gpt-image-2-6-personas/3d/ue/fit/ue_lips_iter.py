# Runs INSIDE Unreal: iterate translate_face_landmarks until the lip landmarks reach (original + asked), from kf_landmarks3d.json.
import unreal, json
F = r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit"
cfg = json.load(open(F + r"\lips_shape_cfg.json"))
L0 = json.load(open(F + r"\kf_landmarks3d.json"))
mhs = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
ch = unreal.EditorAssetLibrary.load_asset("/Game/Companions/MetaHuman/MH_DepesaKF")
mhs.try_add_object_to_edit(ch) if not mhs.is_object_added_for_editing(ch) else None
idx = [int(k) for k in cfg["moves"]]
tgt = {i: [a + b for a, b in zip(L0[i], cfg["moves"][str(i)])] for i in idx}
for it in range(25):
    L = [[p.x, p.y, p.z] for p in mhs.get_face_landmarks(ch)]
    rem = {i: [t - c for t, c in zip(tgt[i], L[i])] for i in idx}
    err = max(max(abs(v) for v in r) for r in rem.values())
    print("LIPS iter", it, "max remaining cm", round(err, 3))
    if err < 0.015:
        break
    mhs.translate_face_landmarks(ch, idx, [unreal.Vector(*rem[i]) for i in idx])
L = [[p.x, p.y, p.z] for p in mhs.get_face_landmarks(ch)]
for i in idx:
    print("LIPS total", i, [round(b - a, 3) for a, b in zip(L0[i], L[i])], "asked", cfg["moves"][str(i)])
far = max(max(abs(b - a) for a, b in zip(L0[j], L[j])) for j in range(len(L0)) if L0[j][2] > 165)
print("LIPS above z165 change", round(far, 3))
mhs.commit_face_state(ch)
json.dump(L, open(F + r"\kf_landmarks3d_lips.json", "w"))
print("LIPS saved", unreal.EditorAssetLibrary.save_loaded_asset(ch, only_if_is_dirty=False))

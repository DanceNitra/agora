import json, sys, numpy as np
sys.path.insert(0, r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit")
from fit_lib import *
out = ue(f'''import unreal, json
mhs = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
ch = unreal.EditorAssetLibrary.load_asset("{ASSET}")
mhs.try_add_object_to_edit(ch) if not mhs.is_object_added_for_editing(ch) else None
L = mhs.get_face_landmarks(ch)
print("LMK" + json.dumps([[p.x, p.y, p.z] for p in L]))''')
L = np.array(json.loads(out.split("LMK", 1)[1].strip().splitlines()[0]))
json.dump(L.tolist(), open(F + r"\mh_landmarks3d.json", "w"))
print("n landmarks", len(L), "bbox min", L.min(0).round(2), "max", L.max(0).round(2))
lm0 = track(capture("t_base"), "t_base")
# move the landmark with the lowest z (chin?) and one at max x
for idx, d in [(int(L[:, 2].argmin()), [0, 0, -1.5]), (int(L[:, 0].argmax()), [1.5, 0, 0])]:
    ue(f'''import unreal
mhs = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
ch = unreal.EditorAssetLibrary.load_asset("{ASSET}")
mhs.translate_face_landmarks(ch, [{idx}], [unreal.Vector({d[0]}, {d[1]}, {d[2]})])''')
    lm = track(capture(f"t_{idx}"), f"t_{idx}")
    keys = sorted(lm0)
    ok = keys == sorted(lm) and all(len(lm[k]) == len(lm0[k]) for k in keys)
    print("landmark", idx, "at", L[idx].round(2), "delta", d, "move px", round(float(np.abs(flat(lm, keys) - flat(lm0, keys)).mean()), 3) if ok else "track changed")

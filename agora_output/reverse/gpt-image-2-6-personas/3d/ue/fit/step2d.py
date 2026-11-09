import json, sys, time, numpy as np
sys.path.insert(0, r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit")
from fit_lib import *
def apply(c):
    json.dump([float(x) for x in c], open(F + r"\_coeffs.json", "w"))
    t = time.time()
    ue(f'''import unreal, json
mhs = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
ch = unreal.EditorAssetLibrary.load_asset("{ASSET}")
mhs.try_add_object_to_edit(ch) if not mhs.is_object_added_for_editing(ch) else None
mhs.set_face_model_coefficients(ch, json.load(open(r"{F}\_coeffs.json")))
mhs.commit_face_state(ch)
mhs.assemble_for_preview(ch)''')
    return time.time() - t
ref = json.load(open(F + r"\ref_landmarks.json"))
c0 = np.array(json.load(open(F + r"\coeffs_base.json")))
print("t base", round(apply(c0), 1)); lm0 = track(capture("e_base"), "e_base"); capture("e_base").convert("RGB").save(F + r"\e_base_full.png")
c = c0.copy(); c[30] += 3.0; c[100] += 3.0; c[300] += 3.0
print("t mod", round(apply(c), 1)); lm1 = track(capture("e_mod"), "e_mod")
keys = sorted(lm0)
print("move px", round(float(np.abs(flat(lm1, keys) - flat(lm0, keys)).mean()), 3), "err base", round(aligned_error(lm0, ref)[0], 3), "err mod", round(aligned_error(lm1, ref)[0], 3))
apply(c0); print("restored")

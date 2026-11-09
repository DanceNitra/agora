import json, sys, numpy as np
sys.path.insert(0, r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit")
from fit_lib import *
from PIL import ImageChops
c0 = np.array(json.load(open(F + r"\coeffs_base.json")))
base = capture("d_base")
for mode in ["commit", "assemble"]:
    c = c0.copy(); c[30] += 3.0; c[100] += 3.0; c[300] += 3.0
    json.dump([float(x) for x in c], open(F + r"\_coeffs.json", "w"))
    extra = "mhs.commit_face_state(ch)" if mode == "commit" else "mhs.commit_face_state(ch)\nmhs.assemble_for_preview(ch)"
    print(ue(f'''import unreal, json
mhs = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
ch = unreal.EditorAssetLibrary.load_asset("{ASSET}")
mhs.try_add_object_to_edit(ch) if not mhs.is_object_added_for_editing(ch) else None
mhs.set_face_model_coefficients(ch, json.load(open(r"{F}\_coeffs.json")))
{extra}
back = list(mhs.get_face_model_coefficients(ch))
print("readback diff", sum(abs(a-b) for a,b in zip(back, json.load(open(r"{F}\_coeffs.json")))))''').strip().splitlines()[-1])
    im = capture("d_" + mode)
    diff = np.asarray(ImageChops.difference(base.convert("RGB"), im.convert("RGB"))).mean()
    print(mode, "pixel diff vs base", round(float(diff), 3))
set_coeffs(c0)
print(ue(f'''import unreal
mhs = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
ch = unreal.EditorAssetLibrary.load_asset("{ASSET}")
mhs.commit_face_state(ch)
print("restored")''').strip().splitlines()[-1])

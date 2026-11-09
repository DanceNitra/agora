"""Move the 81 face landmarks back to a saved state: python restore.py <state.json>."""
import json, sys
import numpy as np
sys.path.insert(0, r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit")
from fit_lib import ASSET, ue  # noqa: E402

PRE = f"""import unreal, json
mhs = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
ch = unreal.EditorAssetLibrary.load_asset("{ASSET}")
mhs.try_add_object_to_edit(ch) if not mhs.is_object_added_for_editing(ch) else None
"""

def current():
    out = ue(PRE + 'print("LMK" + json.dumps([[p.x, p.y, p.z] for p in mhs.get_face_landmarks(ch)]))')
    return np.array(json.loads(out.split("LMK", 1)[1].strip().splitlines()[0]))

target = np.array(json.load(open(sys.argv[1])))
for rnd in range(int(sys.argv[2]) if len(sys.argv) > 2 else 12):
    d = target - current()
    print("round", rnd, "max offset cm", round(float(np.abs(d).max()), 4))
    if np.abs(d).max() < 1e-3:
        break
    ue(PRE + f"mhs.translate_face_landmarks(ch, list(range({len(d)})), "
             f"[unreal.Vector(*v) for v in {d.tolist()}])")

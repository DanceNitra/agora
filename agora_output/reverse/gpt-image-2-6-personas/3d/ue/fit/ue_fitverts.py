# Runs INSIDE Unreal. Reads face_target_v.bin (33845 x 3 float32, FaceMesh topology order) and fits the
# MH_Depesa face state to it. Prints landmark change and the solver result.
import unreal, json, struct
F = r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit"
cfg = json.load(open(F + r"\fitverts_cfg.json"))
mhs = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
ch = unreal.EditorAssetLibrary.load_asset("/Game/Companions/MetaHuman/MH_Depesa")
mhs.try_add_object_to_edit(ch) if not mhs.is_object_added_for_editing(ch) else None
raw = open(F + r"\face_target_v.bin", "rb").read()
f = struct.unpack("<%df" % (len(raw) // 4), raw)
V = [unreal.Vector(f[i], f[i + 1], f[i + 2]) for i in range(0, len(f), 3)]
L0 = [[p.x, p.y, p.z] for p in mhs.get_face_landmarks(ch)]
p = unreal.MetaHumanCharacterFitToVerticesParams()
p.set_editor_property("head_vertices", V[0:24049])
p.set_editor_property("left_eye_vertices", V[cfg["left"][0]:cfg["left"][1]])
p.set_editor_property("right_eye_vertices", V[cfg["right"][0]:cfg["right"][1]])
p.set_editor_property("teeth_vertices", V[24049:28295])
o = p.get_editor_property("options")
for k, val in cfg.get("options", {}).items():
    o.set_editor_property(k, val)
p.set_editor_property("options", o)
ok = mhs.fit_state_to_target_vertices(ch, p)
L1 = [[q.x, q.y, q.z] for q in mhs.get_face_landmarks(ch)]
d = max(abs(a - b) for u, w in zip(L0, L1) for a, b in zip(u, w))
print("FIT", ok, "max landmark change cm", round(d, 4), "options", str(o))

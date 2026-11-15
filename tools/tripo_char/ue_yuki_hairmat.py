"""Runs inside Unreal. Sets look parameters on Yuki's hair material MI_Yuki_Hair (an instance of the MetaHuman MI_Hair).
A wrapper sets ARGS = dict(S={scalar name: value}, V={vector name: (r, g, b)}, SAVE=bool). Names as the material lists
them: hairDye, hairMelanin, MelaninVariationFine/Rough, HairRoughness, RoughnessOverall, RIntensity, Highlights,
HighlightshairDye, HighlightsIntensity, HighlightsVariationNumber, Ombre, OmbrehairDye, OmbreShift and so on.
Prints the values it set; unknown names stop the run."""
import unreal

_A = globals().pop("ARGS", {})
mel, lib = unreal.MaterialEditingLibrary, unreal.EditorAssetLibrary
p = "/Game/AgoraChar/Tripo/Yuki/MI_Yuki_Hair"
m = unreal.load_asset(p)
sn, vn = set(str(n) for n in mel.get_scalar_parameter_names(m)), set(str(n) for n in mel.get_vector_parameter_names(m))
for k, v in _A.get("S", {}).items():
    assert k in sn, "no scalar " + k
    mel.set_material_instance_scalar_parameter_value(m, k, float(v))
for k, v in _A.get("V", {}).items():
    assert k in vn, "no vector " + k
    mel.set_material_instance_vector_parameter_value(m, k, unreal.LinearColor(v[0], v[1], v[2], 1.0))
mel.update_material_instance(m)
print("HAIRMAT set", _A.get("S", {}), _A.get("V", {}), "saved", lib.save_asset(p, only_if_is_dirty=False) if _A.get("SAVE", True) else "no")

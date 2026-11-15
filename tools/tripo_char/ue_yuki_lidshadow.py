"""Runs inside Unreal. Sets the lid shadow that the MetaHuman eye shell casts on the eyeball (MI_Face_EyeShell of the
built Yuki): ShadowTint (smaller is darker; the build has 0.9) and the top shadow's radius and hardness. The concept's
upper lid throws a clear shadow on the top of the iris; without it the whole iris is lit and the eye stares.
A wrapper sets ARGS = dict(TINT=..., TOP_RADIUS=..., TOP_HARDNESS=..., NAME=...). Saves the material instance."""
import unreal

_A = globals().pop("ARGS", {})
NAME = _A.get("NAME", "MHC_Yuki_v5")
mel, lib = unreal.MaterialEditingLibrary, unreal.EditorAssetLibrary
p = f"/Game/AgoraChar/Tripo/Yuki/Built_{NAME}/{NAME}/Face/Materials/MI_Face_EyeShell"
m = lib.load_asset(p)
t = _A.get("TINT", 0.9)
mel.set_material_instance_vector_parameter_value(m, "ShadowTint", unreal.LinearColor(t, t * 0.92, t, 1.0))
for k, name in (("TOP_RADIUS", "TopShadow_Radius"), ("TOP_HARDNESS", "TopShadow_Hardness")):
    if k in _A:
        mel.set_material_instance_scalar_parameter_value(m, name, _A[k])
mel.update_material_instance(m)
print("LIDSHADOW tint", t, {k: _A[k] for k in ("TOP_RADIUS", "TOP_HARDNESS") if k in _A}, "saved", lib.save_asset(p, only_if_is_dirty=False))

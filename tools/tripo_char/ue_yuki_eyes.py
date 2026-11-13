"""Runs inside Unreal. Gives the built MetaHuman Yuki her amber eyes and dark brows and lashes.

The built eye materials (MI_EyeL_Baked, MI_EyeR_Baked) have "Use Baked Material" on, so the iris colour parameters do
nothing: the colour is the texture "Iris Basecolor Baked". This imports the recoloured iris (yuki_iris_amber.py) and
points both eyes at it. A wrapper may set ARGS = dict(...) with NAME, PNG, IRIS_SCALE, CORNEA, PUPIL, BROW_MELANIN, LASH_MELANIN. Saves only the assets it
names."""
import unreal

# Wrapper values arrive in one dict, ARGS, which is taken out of the globals before anything else runs. The editor's
# Python keeps its globals between runs: single variables set by a wrapper became the defaults of later runs, also
# when a run failed half way (2026-11-13: a close-up's FOV, an old iris scale and PIE=True leaked that way).
_A = globals().pop("ARGS", {})


NAME = _A.get("NAME", "MHC_Yuki_v5")
PNG = _A.get("PNG", r"C:\Users\Danculus\agora\tools\tripo_char\models\yuki\eye_tex_v1\yuki_iris_BC.png")
# Measured on close-ups 2026-11-13: "Cornea Size" is what makes the iris disc larger (0.174 preset, 0.31 reaches from lid
# to lid as in the concept); "Iris Scale" only zooms the iris texture inside the disc: 1.0 shows no rim, 0.88 puts the dark rim at the
# edge, 0.8 and lower starts to repeat the texture at the sides.
IRIS_SCALE = _A.get("IRIS_SCALE", 0.88)
CORNEA = _A.get("CORNEA", 0.31)
PUPIL = _A.get("PUPIL", 1.0)   # "Pupil Dilation": 0.6 no pupil, 0.955 the preset's small pupil, 1.3 two thirds of the iris
BROW_MELANIN = _A.get("BROW_MELANIN", 0.8)
LASH_MELANIN = _A.get("LASH_MELANIN", 1.0)
PKG = "/Game/AgoraChar/Tripo/Yuki"
BUILT = f"{PKG}/Built_{NAME}/{NAME}"
lib = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary

it = unreal.AssetImportTask()
it.set_editor_property("filename", PNG)
it.set_editor_property("destination_path", f"{PKG}/Tex")
it.set_editor_property("destination_name", "T_Yuki_iris_BC")
it.set_editor_property("automated", True)
it.set_editor_property("replace_existing", True)
it.set_editor_property("save", False)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([it])
tex = unreal.load_asset(f"{PKG}/Tex/T_Yuki_iris_BC")
tex.set_editor_property("srgb", True)
lib.save_asset(f"{PKG}/Tex/T_Yuki_iris_BC", only_if_is_dirty=False)
for side in ("L", "R"):
    path = f"{BUILT}/Face/Materials/MI_Eye{side}_Baked"
    m = lib.load_asset(path)
    mel.set_material_instance_texture_parameter_value(m, "Iris Basecolor Baked", tex)
    mel.set_material_instance_vector_parameter_value(m, "Iris Color Multiply", unreal.LinearColor(1, 1, 1, 1))
    mel.set_material_instance_scalar_parameter_value(m, "Iris Scale", IRIS_SCALE)
    mel.set_material_instance_scalar_parameter_value(m, "Pupil Dilation", PUPIL)
    mel.set_material_instance_scalar_parameter_value(m, "Cornea Size", CORNEA)
    mel.update_material_instance(m)
    print("EYE", side, lib.save_asset(path, only_if_is_dirty=False))
for a in lib.list_assets(f"{BUILT}/Grooms", recursive=True):
    p = a.split(".")[0]
    val = BROW_MELANIN if "Eyebrows" in p else LASH_MELANIN if "Eyelashes" in p else None
    m = lib.load_asset(p) if val is not None else None
    if isinstance(m, unreal.MaterialInstanceConstant):
        mel.set_material_instance_scalar_parameter_value(m, "hairMelanin", val)
        mel.update_material_instance(m)
        print("GROOM MAT", p.split("/")[-1], val, lib.save_asset(p, only_if_is_dirty=False))

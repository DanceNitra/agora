# Runs INSIDE Unreal, AFTER the build: make the built eyebrow groom materials near-black like p6 by setting the hair
# shader parameters directly on our built copies in BuiltKF (the build regenerates them, so run after every build).
import json
import unreal
CFG = json.load(open(r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit\brows_post_cfg.json"))
lib = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
n = 0
for a in lib.list_assets("/Game/Companions/MetaHuman/BuiltKF/MH_DepesaKF/Grooms", recursive=True):
    if "Eyebrows" not in a or "/MI_" not in a:
        continue
    m = lib.load_asset(a)
    names = [str(p) for p in mel.get_scalar_parameter_names(m)]
    if n == 0:
        print("BROWPOST before", {p: round(mel.get_material_instance_scalar_parameter_value(m, p), 3) for p in names if p in CFG["scalars"] or "elanin" in p or "edness" in p})
    for p, v in CFG["scalars"].items():
        if p in names:
            mel.set_material_instance_scalar_parameter_value(m, p, v)
    mel.update_material_instance(m)
    lib.save_loaded_asset(m, only_if_is_dirty=False)
    n += 1
print("BROWPOST materials", n)

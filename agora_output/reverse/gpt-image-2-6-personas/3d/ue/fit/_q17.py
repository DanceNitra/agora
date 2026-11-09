import unreal
lib = unreal.EditorAssetLibrary
seq = lib.load_asset("/Game/Companions/Lipsync/LS_KF_Depesa_lajk_confidence_v5")
print("PRM bindings", [str(b.get_display_name()) for b in seq.get_bindings()])
ch = lib.load_asset("/Game/Companions/MetaHuman/MH_DepesaKF")
ov = ch.get_editor_property("skin_settings").get_editor_property("texture_overrides").get_editor_property("face")
print("PRM override", {str(k): (v.get_path_name() if v else None) for k, v in ov.items()})

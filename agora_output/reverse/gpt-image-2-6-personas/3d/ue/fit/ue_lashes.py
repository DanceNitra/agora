# Runs INSIDE Unreal, AFTER the build: mascara look on the built eyelash groom (our copy in BuiltKF).
# Fewer, thicker lashes with blunt tips read as lashes clumped into spikes by a mascara wand.
# The build regenerates this asset, so run this after every build.
import json
import unreal

CFG = json.load(open(r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit\lashes_cfg.json"))
lib = unreal.EditorAssetLibrary
g = lib.load_asset("/Game/Companions/MetaHuman/BuiltKF/MH_DepesaKF/Grooms/Eyelashes_L_ThickCurl")
ls = g.get_editor_property("hair_groups_lod")
lods = ls[0].get_editor_property("lods")
l0 = lods[0]
l0.set_editor_property("curve_decimation", CFG["curve_decimation"])
lods[0] = l0
ls[0].set_editor_property("lods", lods)
g.set_editor_property("hair_groups_lod", ls)
rs = g.get_editor_property("hair_groups_rendering")
gs = rs[0].get_editor_property("geometry_settings")
gs.set_editor_property("hair_width_override", True)
gs.set_editor_property("hair_width", CFG["width"])
gs.set_editor_property("hair_root_scale", CFG["root_scale"])
gs.set_editor_property("hair_tip_scale", CFG["tip_scale"])
rs[0].set_editor_property("geometry_settings", gs)
g.set_editor_property("hair_groups_rendering", rs)
lib.save_loaded_asset(g, only_if_is_dirty=False)
gs2 = g.get_editor_property("hair_groups_rendering")[0].get_editor_property("geometry_settings")
print("LASHES width", gs2.get_editor_property("hair_width"), "decim",
      g.get_editor_property("hair_groups_lod")[0].get_editor_property("lods")[0].get_editor_property("curve_decimation"))

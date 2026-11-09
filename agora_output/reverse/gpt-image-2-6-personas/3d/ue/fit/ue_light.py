# Runs INSIDE Unreal: set the three spawnable point lights of a sequence from light_cfg.json
# ({"seq": path, "rig": [[offset xyz, colour rgb, candela, radius], key, rim, fill]}).
# The original Dosvit rig is in the Dosvit script (amber key 255,168,92 at 1.1 cd; violet rim 1.6; cool fill 0.10).
import json
import unreal

CFG = json.load(open(r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit\light_cfg.json"))
lib = unreal.EditorAssetLibrary
seq = lib.load_asset(CFG["seq"])
HEAD = (0.0, 300000.0, 100166.0)
lights = [b for b in seq.get_bindings() if str(b.get_display_name()).startswith("Point Light")]
lights.sort(key=lambda b: str(b.get_display_name()))
for b, (off, colr, cd, rad) in zip(lights, CFG["rig"]):
    lc = b.get_object_template().get_editor_property("point_light_component")
    lc.set_editor_property("light_color", unreal.Color(r=colr[0], g=colr[1], b=colr[2], a=255))
    lc.set_editor_property("intensity_units", unreal.LightUnits.CANDELAS)
    lc.set_editor_property("intensity", cd)
    lc.set_editor_property("attenuation_radius", rad)
    lc.set_editor_property("source_radius", 8.0)
    for t in b.get_tracks():
        if isinstance(t, unreal.MovieScene3DTransformTrack):
            ch = t.get_sections()[0].get_all_channels()
            for c, v in zip(ch[:3], (HEAD[0] + off[0], HEAD[1] + off[1], HEAD[2] + off[2])):
                c.set_default(v)
    print("LIGHT", b.get_display_name(), off, colr, cd)
lib.save_loaded_asset(seq, only_if_is_dirty=False)
print("LIGHTSET", seq.get_path_name())

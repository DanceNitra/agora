# Runs INSIDE Unreal: relight the sequence in arc_target.json with the Dosvit look: warm amber key low from the
# left, rose-violet rim from behind right, a weak cool fill. Edits the three spawnable point lights in place.
import json
import unreal

lib = unreal.EditorAssetLibrary
seq = lib.load_asset(json.load(open(r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit\arc_target.json"))["seq"])
HEAD = (0.0, 300000.0, 100166.0)
# offsets (x, y, z) from the head, colour, candela, radius
RIG = [
    ((-60.0, 40.0, 10.0), (255, 168, 92), 1.1, 300.0),    # key: amber, camera-left, slightly low
    ((75.0, -35.0, 30.0), (225, 120, 255), 1.6, 300.0),   # rim: rose-violet, behind right
    ((10.0, 90.0, -15.0), (170, 185, 255), 0.10, 300.0),  # fill: cool, weak, front
]
lights = [b for b in seq.get_bindings() if str(b.get_display_name()).startswith("Point Light")]
lights.sort(key=lambda b: str(b.get_display_name()))
for b, (off, colr, cd, rad) in zip(lights, RIG):
    lc = b.get_object_template().get_editor_property("point_light_component")
    lc.set_editor_property("light_color", unreal.Color(colr[2], colr[1], colr[0], 255) if False else unreal.Color(r=colr[0], g=colr[1], b=colr[2], a=255))
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
print("DOSVIT", seq.get_path_name())

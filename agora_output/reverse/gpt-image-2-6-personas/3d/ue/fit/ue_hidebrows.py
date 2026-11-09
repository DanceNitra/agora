# Runs INSIDE Unreal, AFTER the build: hide the MetaHuman eyebrow groom (our built copy in BuiltKF) by making its
# strands near-zero wide, because our own p6-shaped brow grooms replace it in the render sequence.
import unreal
lib = unreal.EditorAssetLibrary
for a in lib.list_assets("/Game/Companions/MetaHuman/BuiltKF/MH_DepesaKF/Grooms", recursive=False):
    o = lib.load_asset(a)
    if isinstance(o, unreal.GroomAsset) and "Eyebrows" in a:
        rs = o.get_editor_property("hair_groups_rendering")
        for r in rs:
            gs = r.get_editor_property("geometry_settings")
            gs.set_editor_property("hair_width_override", True)
            gs.set_editor_property("hair_width", 0.0001)
            r.set_editor_property("geometry_settings", gs)
        o.set_editor_property("hair_groups_rendering", rs)
        lib.save_loaded_asset(o, only_if_is_dirty=False)
        w = o.get_editor_property("hair_groups_rendering")[0].get_editor_property("geometry_settings").get_editor_property("hair_width")
        print("HIDEBROWS", a, w)

# Runs INSIDE Unreal: give FIT_MH new grooms (setgroom_cfg.json: component -> wardrobe binding asset) with a
# transient binding built against the live preview face mesh, as the MetaHuman preview pipeline does.
import json
import unreal
F = r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit"
cfg = json.load(open(F + r"\setgroom_cfg.json"))
comps = {}
for c in unreal.ObjectIterator(unreal.GroomComponent):
    o = c.get_owner()
    if o and o.get_actor_label() == "FIT_MH":
        comps[c.get_name()] = c
face = comps["Eyelashes"].get_editor_property("binding_asset").get_editor_property("target_skeletal_mesh")
for name, path in cfg.items():
    src = unreal.EditorAssetLibrary.load_asset(path)
    b = unreal.new_object(unreal.GroomBindingAsset)
    b.set_editor_property("groom", src.get_editor_property("groom"))
    b.set_editor_property("source_skeletal_mesh", src.get_editor_property("source_skeletal_mesh"))
    b.set_editor_property("target_skeletal_mesh", face)
    b.set_editor_property("num_interpolation_points", 100)
    b.build()
    c = comps[name]
    c.set_editor_property("binding_asset", b)
    c.set_editor_property("groom_asset", src.get_editor_property("groom"))
    c.set_visibility(True, True)
    print("SETG", name, src.get_editor_property("groom").get_name(), c.get_editor_property("binding_asset") is not None)

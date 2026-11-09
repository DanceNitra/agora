# Runs INSIDE Unreal: set groom colour parameters per wardrobe item (groomcolor_cfg.json: item-name fragment -> {param: value}).
import json
import unreal
F = r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit"
cfg = json.load(open(F + r"\groomcolor_cfg.json"))
mhs = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
ch = unreal.EditorAssetLibrary.load_asset("/Game/Companions/MetaHuman/MH_Depesa")
inst = mhs.get_preview_collection(ch).get_editor_property("default_instance")
for p in inst.get_instance_parameter_item_paths():
    txt = p.export_text()
    for frag, vals in cfg.items():
        if frag in txt:
            for q in inst.get_instance_parameters(p):
                if str(q.name) in vals:
                    print("COL", frag, q.name, q.get_float(), "->", vals[str(q.name)], q.set_float(vals[str(q.name)]))
mhs.on_edit_preview_collection(ch)

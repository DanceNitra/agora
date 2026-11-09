import unreal
ch = unreal.EditorAssetLibrary.load_asset("/Game/Companions/MetaHuman/MH_DepesaKF")
m = ch.get_editor_property("makeup_settings")
l = m.get_editor_property("lips")
print("PRM lips", l.to_dict() if hasattr(l,"to_dict") else l)
t = l.get_editor_property("type")
print("PRM types", [x for x in dir(type(t)) if x.isupper()])

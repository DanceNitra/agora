import unreal, os
print([n for n in dir(unreal) if "humbnail" in n])
tt = getattr(unreal, "ThumbnailTools", None)
print("ThumbnailTools", tt and [n for n in dir(tt) if not n.startswith("_")][:40])
ch = unreal.EditorAssetLibrary.load_asset("/MetaHumanCharacter/Optional/Presets/Jelena")
print("props", [p for p in dir(ch) if any(k in p.lower() for k in ("thumb","preview","image","texture","face"))])

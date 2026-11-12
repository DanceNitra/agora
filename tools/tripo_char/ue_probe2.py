"""Runs inside Unreal. Lists how the conformed character's geometry can be read or exported."""
import unreal

sub = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
names = [n for n in dir(sub) if not n.startswith("_")]
print("get", [n for n in names if n.startswith("get_")])
print("other", [n for n in names if any(k in n for k in ("export", "vert", "preview", "skeletal", "mesh", "is_", "can_", "login", "sign"))])
ex = unreal.MetaHumanCharacterExportBlueprintLibrary
print("export lib", [n for n in dir(ex) if not n.startswith("_") and "export" in n])
for cls in ("MetaHumanGeometryExportParams", "MetaHumanDCCExportParams"):
    c = getattr(unreal, cls, None)
    if c:
        print(cls, [n for n in dir(c()) if not n.startswith("_") and n not in dir(unreal.StructBase)])
ch = unreal.load_asset("/Game/AgoraChar/Tripo/Hero01/MHC_Hero01")
print("character props", [p for p in dir(ch) if not p.startswith("_") and p not in dir(unreal.Object)])
w = unreal.MetaHumanGeneratorSubsystemWrapper
print("wrapper", [n for n in dir(w) if not n.startswith("_") and n not in dir(unreal.Object)])

"""Runs inside Unreal (ue_py.py). Fixes BP_AgoraMH in place so the hair, eyebrows and eyelashes render at every
distance, as in the built BP_MH_AgoraSoldier: copies each groom's override materials, its binding attachment
(FACIAL_C_FacialRoot) and use_attach_parent_bound, and adds a LODSync component with the MetaHuman's LOD mapping,
renamed to this character's components (Body -> CharacterMesh0, SkeletalMesh -> Outfit).
Measured 2026-11-07: at 4 m the head rendered bald because none of this was copied."""
import unreal

NEW = "/Game/AgoraChar/MetaHuman/BP_AgoraMH"
MH_BP = "/Game/AgoraChar/MetaHuman/Built/MH_AgoraSoldier/BP_MH_AgoraSoldier"
RENAME = {"Body": "CharacterMesh0", "SkeletalMesh": "Outfit"}
lib = unreal.EditorAssetLibrary
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
SDL = unreal.SubobjectDataBlueprintFunctionLibrary


def comps(bp):
    out = {}
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        o = SDL.get_associated_object(SDL.get_data(h))
        if o:
            out.setdefault(o.get_name().replace("_GEN_VARIABLE", ""), (h, o))
    return out


bp, mh = lib.load_asset(NEW), lib.load_asset(MH_BP)
a, b = comps(mh), comps(bp)
for g in ("Hair", "Eyebrows", "Eyelashes", "Fuzz"):
    if g in a and g in b:
        for p in ("override_materials", "attachment_name", "use_attach_parent_bound", "groom_asset", "binding_asset"):
            b[g][1].set_editor_property(p, a[g][1].get_editor_property(p))
        print(g, "copied; materials", len(b[g][1].get_editor_property("override_materials")))

src_lod = a["LODSync"][1]
if "LODSync" in b:
    lod = b["LODSync"][1]
else:
    root_h = next(h for n, (h, o) in b.items() if n.startswith("CollisionCylinder"))
    h, fail = sds.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=root_h, new_class=unreal.LODSyncComponent, blueprint_context=bp))
    sds.rename_subobject(h, unreal.Text("LODSync"))
    lod = SDL.get_associated_object(SDL.get_data(h))
present = set(b)
sync = []
for item in src_lod.get_editor_property("components_to_sync"):
    name = RENAME.get(str(item.name), str(item.name))
    if name in present or name == "CharacterMesh0":
        item.name = name
        sync.append(item)
lod.set_editor_property("components_to_sync", sync)
mapping = {}
for k, v in src_lod.get_editor_property("custom_lod_mapping").items():
    if str(k) in present:
        mapping[k] = v
lod.set_editor_property("custom_lod_mapping", mapping)
lod.set_editor_property("num_lods", src_lod.get_editor_property("num_lods"))
print("LODSync components", [(str(i.name), str(i.sync_option)) for i in lod.get_editor_property("components_to_sync")])
unreal.BlueprintEditorLibrary.compile_blueprint(bp)
lib.save_loaded_asset(bp, only_if_is_dirty=False)
print("status", bp.get_editor_property("status"))

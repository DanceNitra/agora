"""Runs inside Unreal (ue_py.py). Points the idle slots back at MM_Idle_Agora: the Idle state's sequence player in
ABP_Unarmed_Agora and the nine speed-0 samples of BS_Idle_Walk_Run_Agora. Needed after MM_Idle_Agora was deleted and
recreated (2026-11-07), which cleared every reference to it and stopped play with a compile error."""
import unreal

ANIMS = "/Game/AgoraChar/Retarget/Anims6"
lib = unreal.EditorAssetLibrary
idle = lib.load_asset(f"{ANIMS}/MM_Idle_Agora")

bs = lib.load_asset(f"{ANIMS}/BS_Idle_Walk_Run_Agora")
samples = list(bs.get_editor_property("sample_data"))
fixed = 0
for s in samples:
    if s.get_editor_property("animation") is None:
        s.set_editor_property("animation", idle); fixed += 1
bs.set_editor_property("sample_data", samples)
bs.modify()
lib.save_loaded_asset(bs, only_if_is_dirty=False)
print("blend space samples relinked:", fixed, "still empty:", sum(1 for s in bs.get_editor_property("sample_data") if s.get_editor_property("animation") is None))

abp = lib.load_asset(f"{ANIMS}/ABP_Unarmed_Agora")
path = f"{ANIMS}/ABP_Unarmed_Agora.ABP_Unarmed_Agora:AnimGraph.AnimGraphNode_StateMachine_0.Locomotion.AnimStateNode_1.Idle.AnimGraphNode_SequencePlayer_1"
node = unreal.find_object(None, path)
print("idle node", node)
inner = node.get_editor_property("node")
inner.set_editor_property("sequence", idle)
node.set_editor_property("node", inner)
print("idle node sequence now", node.get_editor_property("node").get_editor_property("sequence"))
unreal.BlueprintEditorLibrary.compile_blueprint(abp)
print("ABP saved", lib.save_loaded_asset(abp, only_if_is_dirty=False))

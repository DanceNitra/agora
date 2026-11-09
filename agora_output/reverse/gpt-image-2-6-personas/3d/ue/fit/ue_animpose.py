# Runs INSIDE Unreal: put AS_<name> on FIT_MH's face in single-node mode at time t (animpose_cfg.json).
import json
import unreal
F = r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit"
cfg = json.load(open(F + r"\animpose_cfg.json"))
anim = unreal.EditorAssetLibrary.load_asset(cfg["anim"])
for c in unreal.ObjectIterator(unreal.SkeletalMeshComponent):
    o = c.get_owner()
    if o and o.get_actor_label() == "FIT_MH" and c.get_name() == "Face":
        if cfg.get("setup"):
            c.set_update_animation_in_editor(True)
            c.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
            c.set_animation(anim)
            c.set_play_rate(0.0)
        c.set_position(cfg["t"], False)
        print("POSE", cfg["t"], anim.get_editor_property("sequence_length") if cfg.get("setup") else "")

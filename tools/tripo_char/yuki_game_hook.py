"""Runs inside the render process (UnrealEditor -game ... -ExecCmds="py <this file>"), not in the editor.

The hair groom collides only with the bones of the mesh it is bound to (the face mesh: torso, shoulders, upper arms,
neck, head). Forearms, hands and legs belong to the Body component, and adding that component as a collider is a
runtime call that the level cannot store. This hook waits until the level's Yuki exists, adds the Body component as a
collider of the long-hair groom, writes a marker file, and removes itself."""
import unreal

ACTOR = "/Game/AgoraChar/Tripo/Yuki/L_Yuki_Preview.L_Yuki_Preview:PersistentLevel.BP_MHC_Yuki_v5_C_0"
MARK = "C:/Users/Danculus/agora/tools/tripo_char/reports/yuki_dance/hook_ran.txt"
HIDE_BONES = ()            # was calf_l, calf_r: hiding bones on Body also hides them on the costume (leader pose); the body is hidden as a whole now
state = {"n": 0, "h": None}


def tick(dt):
    state["n"] += 1
    a = unreal.find_object(None, ACTOR)
    if a is None:
        if state["n"] > 20000:
            unreal.unregister_slate_post_tick_callback(state["h"])
        return
    body = next((c for c in a.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == "Body"), None)
    hair = next((c for c in a.get_components_by_class(unreal.GroomComponent) if c.get_name() == "Hair"), None)
    if body is None or hair is None:
        return
    hair.add_collision_component(body)
    for bn in HIDE_BONES:          # the costume's boots do not fit over the bare feet: the body's calves and feet are hidden
        body.hide_bone_by_name(bn, unreal.PhysBodyOp.PBO_NONE)
    open(MARK, "w").write("hair collides with the body component; tick %d\n" % state["n"])
    unreal.log("YUKI HOOK: hair collides with the body component")
    unreal.unregister_slate_post_tick_callback(state["h"])


state["h"] = unreal.register_slate_post_tick_callback(tick)

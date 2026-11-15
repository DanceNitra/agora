"""Runs inside Unreal while Play-in-Editor is running. Poses or plays the play copy of Yuki for check shots: the body
plays a dance animation from TIME at RATE (0 holds that pose), the face may hold an expression pose, and the hair
simulation can be reset once the pose is set. Nothing in the level or in any asset changes.

Why RESET: the play copy starts in the reference pose. Jumping from there into a dance pose hits the hair with one
huge move; it lands over the face and stays there, and the test then judges the jump, not the settings (four variants
looked equally bad that way on 2026-11-13). Reset puts the strands back in their styled shape on the new pose.

A wrapper sets ARGS = dict(ANIM=<asset path of a body AnimSequence>, TIME=<seconds>, RATE=<play rate>, RESET=<bool>,
FREEZE=<bool: only stop the clip where it is>, FACE=<asset path of a face pose, or "" for none>,
BODY_COLLISION=<bool>)."""
import unreal

_A = globals().pop("ARGS", {})
ANIM, TIME, FACE = _A.get("ANIM", ""), float(_A.get("TIME", 0.0)), _A.get("FACE", "")
RATE, RESET, FREEZE = float(_A.get("RATE", 0.0)), _A.get("RESET", False), _A.get("FREEZE", False)
FACE_TIME = _A.get("FACE_TIME", None)
BODY_COLLISION = _A.get("BODY_COLLISION", False)   # the hair also collides with the Body component (forearms, hands, legs)
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
anim = unreal.load_asset(ANIM) if ANIM else None
fa = unreal.load_asset(FACE) if FACE else None
for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor):
    if "MHC_Yuki" in a.get_class().get_name():
        for c in a.get_components_by_class(unreal.SkeletalMeshComponent):
            c.set_forced_lod(1)
            if c.get_name() == "Body":
                if FREEZE:
                    c.set_play_rate(0.0)
                    print("PLAY frozen at", round(c.get_position(), 2))
                else:
                    c.play_animation(anim, False)
                    c.set_position(TIME, False)
                    c.set_play_rate(RATE)
            elif c.get_name() == "Face" and fa is not None and not FREEZE:
                c.play_animation(fa, True)
                if FACE_TIME is not None:          # hold one moment of a long face animation (a song's lipsync)
                    c.set_position(float(FACE_TIME), False)
                    c.set_play_rate(0.0)
        if BODY_COLLISION:
            bodyc = next(c for c in a.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == "Body")
            for g in a.get_components_by_class(unreal.GroomComponent):
                if g.get_name() == "Hair":
                    g.add_collision_component(bodyc)
                    print("PLAY hair collides with the body component")
        if RESET:
            for g in a.get_components_by_class(unreal.GroomComponent):
                if g.get_name() == "Hair":
                    g.reset_simulation()
                    print("PLAY hair simulation reset")
        if not FREEZE:
            print("PLAY", anim.get_name(), "from", TIME, "rate", RATE)

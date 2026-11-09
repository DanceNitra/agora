# Runs INSIDE Unreal: add a directed smile / brow layer on top of the lip-sync keys of the sequence in
# arc_target.json (Face control rig). Additive, smooth 0.3 s ramps, clamped to 0..1.
import json
import unreal

lib = unreal.EditorAssetLibrary
seq = lib.load_asset(json.load(open(r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit\arc_target.json"))["seq"])
RAMP = 0.3
# (start, end, {control base name: amount}); times relative to the clip
PLAN = [
    (1.2, 5.3, {"mouth_cornerPull": 0.35, "mouth_dimple": 0.15, "eye_cheekRaise": 0.12}),
    (5.3, 9.0, {"mouth_cornerPull": 0.5, "mouth_dimple": 0.25, "eye_cheekRaise": 0.2}),
    (7.3, 9.0, {"L_brow_raiseOut": 0.45}),
    (9.0, 13.6, {"mouth_cornerPull": 0.6, "mouth_dimple": 0.3, "eye_cheekRaise": 0.4, "eye_squintInner": 0.2, "brow_raiseIn": 0.15}),
    (13.6, 16.2, {"mouth_cornerPull": 0.45, "mouth_dimple": 0.2, "eye_cheekRaise": 0.15}),
]


def env(t, a, b):
    if t <= a - RAMP or t >= b + RAMP:
        return 0.0
    if t < a:
        x = (t - (a - RAMP)) / RAMP
    elif t > b:
        x = 1 - (t - b) / RAMP
    else:
        return 1.0
    return x * x * (3 - 2 * x)


def add_for(name, t):
    base = name.rsplit("_", 1)[0]  # strip the _17 index
    total = 0.0
    for a, b, ctl in PLAN:
        for key, amt in ctl.items():
            side_ok = (key.startswith(("L_", "R_")) and ("CTRL_" + key) == base) or \
                      (not key.startswith(("L_", "R_")) and base in ("CTRL_L_" + key, "CTRL_R_" + key))
            if side_ok:
                total = max(total, amt * env(t, a, b))
    return total


face = None
for bnd in seq.get_bindings():
    if str(bnd.get_display_name()) == "Face":
        face = bnd.get_tracks()[0].get_sections()[0]
tick = seq.get_display_rate()
tps = tick.numerator / tick.denominator
n = 0
for ch in face.get_all_channels():
    if ch.get_num_keys() == 0:
        continue
    for k in ch.get_keys():
        t = k.get_time().frame_number.value / tps
        d = add_for(ch.get_name(), t)
        if d > 0:
            k.set_value(min(1.0, max(0.0, k.get_value()) + d))
            n += 1
lib.save_loaded_asset(seq, only_if_is_dirty=False)
print("SMILE keys changed", n, "seq", seq.get_path_name())

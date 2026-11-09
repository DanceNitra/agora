# Runs INSIDE Unreal. LS_KF_Depesa_lajk_arc2 = copy of the CONFIDENCE sequence whose Face control-rig keys are
# replaced by a per-line blend of the CONFIDENCE / PLAYFULNESS / HAPPINESS solves (0.25 s cross-fades), with
# jaw range +12 %, lip seals x1.3 and blinks x4 (clamped to the control range).
import unreal

DIR = "/Game/Companions/Lipsync"
lib = unreal.EditorAssetLibrary
MOODS = ("confidence", "playfulness", "happiness")
LINES = [(0.0, 5.32, "confidence"), (5.32, 9.02, "playfulness"), (9.02, 13.62, "happiness"), (13.62, 99.0, "confidence")]
FADE = 0.25


def weights(t):
    w = {m: 0.0 for m in MOODS}
    for i, (a, b, m) in enumerate(LINES):
        if a <= t < b:
            w[m] += 1.0
            if i + 1 < len(LINES) and t > b - FADE:
                k = (t - (b - FADE)) / FADE
                w[m] -= 0.5 * k
                w[LINES[i + 1][2]] += 0.5 * k
            if i > 0 and t < a + FADE:
                k = 1.0 - (t - a) / FADE
                w[m] -= 0.5 * k
                w[LINES[i - 1][2]] += 0.5 * k
            break
    return w


def face_channels(seq):
    for b in seq.get_bindings():
        if str(b.get_display_name()) == "Face":
            return {c.get_name(): c for c in b.get_tracks()[0].get_sections()[0].get_all_channels() if c.get_num_keys() > 0}
    return {}


def shape(name, v):
    n = name.lower()
    if "jaw.y" in n:
        return v * 1.12
    if "lipstogether" in n:
        return min(1.0, v * 1.3)
    if "eye_blink" in n:
        return min(1.0, v * 4.0) if v > 0 else v
    return v


import json
dst = lib.load_asset(json.load(open(r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit\arc_target.json"))["seq"])
src = {m: face_channels(lib.load_asset(f"{DIR}/LS_KF_Depesa_lajk_{m}_v2")) for m in MOODS}
out = face_channels(dst)
tick = dst.get_display_rate()
tps = tick.numerator / tick.denominator
changed = 0
for name, ch in out.items():
    vals = {}
    for m in MOODS:
        c = src[m].get(name)
        vals[m] = {k.get_time().frame_number.value: k.get_value() for k in c.get_keys()} if c else {}
    for k in ch.get_keys():
        fr = k.get_time().frame_number.value
        t = fr / tps
        w = weights(t)
        v = sum(w[m] * vals[m].get(fr, vals["confidence"].get(fr, k.get_value())) for m in MOODS)
        k.set_value(shape(name, v))
        changed += 1
lib.save_loaded_asset(dst, only_if_is_dirty=False)
print("ARC2 keys", changed, "channels", len(out), "tick/s", tps, "seq", dst.get_path_name())

# Runs INSIDE Unreal. Builds AS_Depesa_lajk_arc_face: per-line mood blend of three full-clip solves (same audio),
# with cross-fades, plus curve shaping (jaw range, lip seals, blinks). Then builds LS_KF_Depesa_lajk_arc from the
# CONFIDENCE sequence with the face driven by this animation instead of the control rig track.
import unreal

DIR = "/Game/Companions/Lipsync"
lib = unreal.EditorAssetLibrary
AL = unreal.AnimationLibrary
SRC = {m: lib.load_asset(f"{DIR}/AS_Depesa_lajk_{m}_face") for m in ("confidence", "playfulness", "happiness")}
# (start s, end s, mood) relative to the clip (master 6.0 s)
LINES = [(0.0, 5.32, "confidence"), (5.32, 9.02, "playfulness"), (9.02, 13.62, "happiness"), (13.62, 99.0, "confidence")]
FADE = 0.25


def weights(t):
    w = {m: 0.0 for m in SRC}
    for i, (a, b, m) in enumerate(LINES):
        if a <= t < b:
            w[m] += 1.0
            if i + 1 < len(LINES) and t > b - FADE:  # fade into the next line
                k = (t - (b - FADE)) / FADE
                w[m] -= 0.5 * k
                w[LINES[i + 1][2]] += 0.5 * k
            if i > 0 and t < a + FADE:  # fade out of the previous line
                k = 1.0 - (t - a) / FADE
                w[m] -= 0.5 * k
                w[LINES[i - 1][2]] += 0.5 * k
            break
    return w


def shape(name, v):
    n = name.lower()
    if "jawopen" in n:
        return min(1.0, v * 1.12)
    if "lipspress" in n or "lipstogether" in n:
        return min(1.0, v * 1.3)
    if "eyeblink" in n:
        return min(1.0, v * 4.0)
    return v


dst_path = f"{DIR}/AS_Depesa_lajk_arc_face"
if lib.does_asset_exist(dst_path):
    lib.delete_asset(dst_path)
dst = lib.duplicate_asset(f"{DIR}/AS_Depesa_lajk_confidence_face", dst_path)
names = [str(n) for n in AL.get_animation_curve_names(SRC["confidence"], unreal.RawCurveTrackTypes.RCT_FLOAT)]
done = 0
for name in names:
    keys = {}
    for m, a in SRC.items():
        t, v = AL.get_float_keys(a, name)
        keys[m] = dict(zip([round(x, 4) for x in t], v))
    times = sorted(set().union(*[set(k) for k in keys.values()]))
    vals = []
    for t in times:
        w = weights(t)
        s = sum(w[m] * keys[m].get(t, keys["confidence"].get(t, 0.0)) for m in SRC)
        vals.append(shape(name, s))
    AL.remove_curve(dst, name, False)
    AL.add_curve(dst, name, unreal.RawCurveTrackTypes.RCT_FLOAT, False)
    AL.add_float_curve_keys(dst, name, times, vals)
    done += 1
lib.save_loaded_asset(dst, only_if_is_dirty=False)
print("ARC curves", done, "len", dst.get_editor_property("sequence_length"))

seq_path = f"{DIR}/LS_KF_Depesa_lajk_arc"
if lib.does_asset_exist(seq_path):
    lib.delete_asset(seq_path)
seq = lib.duplicate_asset(f"{DIR}/LS_KF_Depesa_lajk_confidence_v2", seq_path)
for b in seq.get_bindings():
    if str(b.get_display_name()) == "Face":
        for t in list(b.get_tracks()):
            b.remove_track(t)
        tr = b.add_track(unreal.MovieSceneSkeletalAnimationTrack)
        sec = tr.add_section()
        sec.set_range(seq.get_playback_start(), seq.get_playback_end())
        p = sec.get_editor_property("params")
        p.set_editor_property("animation", dst)
        sec.set_editor_property("params", p)
        print("FACE track set")
lib.save_loaded_asset(seq, only_if_is_dirty=False)
print("SEQ", seq.get_path_name())

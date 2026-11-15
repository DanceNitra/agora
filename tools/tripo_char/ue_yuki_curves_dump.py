"""Runs inside Unreal. Writes every float curve of face AnimSequences to disk for work outside the editor.

A wrapper sets ARGS = dict(ANIMS=[asset paths], OUT=<folder>). The solver's curves are key-reduced: each curve has its
own number of keys at its own times (measured 2026-11-14: 1700 to 4100 keys per curve in one animation). Per animation:
<name>.json (curve names, key count per curve, length, frame count) and <name>.f32 (float32: for each curve in the
order of the names, its key times, then its key values)."""
import array
import json
import os

import unreal

_A = globals().pop("ARGS", {})
al = unreal.AnimationLibrary
os.makedirs(_A["OUT"], exist_ok=True)
for path in _A["ANIMS"]:
    a = unreal.load_asset(path)
    names = sorted(str(n) for n in al.get_animation_curve_names(a, unreal.RawCurveTrackTypes.RCT_FLOAT))
    buf, counts = array.array("f"), []
    for n in names:
        t, v = al.get_float_keys(a, n)
        counts.append(len(v))
        buf.extend(float(x) for x in t)
        buf.extend(float(x) for x in v)
    stem = os.path.join(_A["OUT"], path.split("/")[-1])
    with open(stem + ".f32", "wb") as f:
        buf.tofile(f)
    json.dump({"names": names, "counts": counts, "length": a.get_play_length(), "frames": al.get_num_frames(a)}, open(stem + ".json", "w"))
    print("DUMP", path.split("/")[-1], "curves", len(names), "keys min", min(counts), "max", max(counts), "empty", sum(1 for c in counts if c == 0))

"""Does the mouth close where the lyrics need it? Measured on RENDERED frames, without a phoneme aligner.

    python yuki_articulation_check.py <whisper.json> <frames_measure.json> [<frames_measure.json> ...]

<frames_measure.json> comes from lipsync_measure (per-frame lip gap from MediaPipe, in interocular distances).
For m, b and p the lips must meet. Every word of the transcript (faster-whisper word times) that STARTS with m, b or p
inside the rendered stretch is a test point: it passes when the lip gap falls under THR within WIN seconds of the
word's start. The same test at random sung moments is the chance rate; a pass rate means something only against it.
Whisper's word times are rough on sung text (hundreds of ms), hence the window. A first version of this check used a
proxy from rig curves and passed nothing, also at chance: the proxy never reached its own threshold (2026-11-14)."""
import json
import sys

import numpy as np

WIN, THR = 0.20, 0.03
w = json.load(open(sys.argv[1], encoding="utf-8"))
words = [{"word": x.get("word", x.get("w", "")).strip(), "start": x.get("start", x.get("s", 0.0))} for s in w["segments"] for x in s.get("words", [])]
sung = [(s["start"], s["end"]) for s in w["segments"]]
rng = np.random.default_rng(5)
for f in sys.argv[2:]:
    gap = np.array(json.load(open(f))["gap"], dtype=float)
    t = np.arange(len(gap)) / 30.0
    T = t[-1]
    bil = [x for x in words if x["word"].lower()[:1] in ("m", "b", "p") and x["start"] < T - WIN]
    rand_t = np.array([rng.uniform(a, min(b, T - WIN)) for a, b in sung for _ in range(60) if min(b, T - WIN) - a > 0.5])

    def closes(at):
        k = (t >= at - WIN) & (t <= at + WIN)
        return bool(k.any() and np.nanmin(gap[k]) < THR)

    res = [(x["word"], round(x["start"], 2), closes(x["start"]), round(float(np.nanmin(gap[(t >= x["start"] - WIN) & (t <= x["start"] + WIN)])), 3)) for x in bil]
    sing = np.zeros(len(t), bool)
    for a, b in sung:
        sing |= (t >= a) & (t < b)
    print(f.split("/")[-1][:40], "| bilabial words", len(bil), "pass", sum(r[2] for r in res), "| chance %.2f" % np.mean([closes(x) for x in rand_t]),
          "| closed share while sung %.2f" % float((gap[sing] < THR).mean()), "| gap p5 %.3f median %.3f p95 %.3f" % tuple(np.nanpercentile(gap[sing], [5, 50, 95])))
    print("   ", res)
    # Two more classes, where the frames carry the mouth width: a rounded onset (w, oo, o: "would", "you", "used", "to",
    # "so", "ooh", "room", "new") must show a NARROWER mouth than the sung median within WIN, an open vowel onset (a, i as
    # in "I", "I'm", "and", "ain't", "all", "alive") a WIDER lip gap than the sung median. Each against its chance rate.
    data = json.load(open(f))
    if "width" in data:
        wd = np.array(data["width"], dtype=float)
        w_med, g_med = float(np.nanmedian(wd[sing])), float(np.nanmedian(gap[sing]))
        ROUND = ("would", "you", "your", "used", "to", "so", "ooh", "room", "new", "who", "now", "know", "ocean", "emotions", "wrong")
        OPEN = ("i", "i'm", "i've", "and", "ain't", "all", "alive", "apart", "out", "upset", "back", "that's")
        clean = lambda s_: s_.lower().strip(".,!?")
        rw = [x for x in words if clean(x["word"]) in ROUND and x["start"] < T - WIN]
        ow = [x for x in words if clean(x["word"]) in OPEN and x["start"] < T - WIN]
        near = lambda at, arr, fn: fn(arr[(t >= at - 0.05) & (t <= at + WIN)]) if ((t >= at - 0.05) & (t <= at + WIN)).any() else np.nan
        r_pass = np.mean([near(x["start"], wd, np.nanmin) < 0.95 * w_med for x in rw]) if rw else float("nan")
        r_ch = np.mean([near(x, wd, np.nanmin) < 0.95 * w_med for x in rand_t])
        o_pass = np.mean([near(x["start"], gap, np.nanmax) > 1.25 * g_med for x in ow]) if ow else float("nan")
        o_ch = np.mean([near(x, gap, np.nanmax) > 1.25 * g_med for x in rand_t])
        print("    rounded onsets %d: narrower mouth %.2f (chance %.2f) | open onsets %d: wider gap %.2f (chance %.2f) | width median %.3f" % (len(rw), r_pass, r_ch, len(ow), o_pass, o_ch, w_med))

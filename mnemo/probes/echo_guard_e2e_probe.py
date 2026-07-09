"""echo_guard_e2e_probe.py — validate the SHIPPED mnemo echo_guard end-to-end on the MemBench echo fixture.

Runs every fixture case through actual Mnemo.remember(key=, object=) + keyed supersession (NOT the probe's
policy abstraction), granting oracle object extraction (the documented limit: real efficacy rides on the
caller's / an extractor's object accuracy). Metric: is the currently-ACTIVE keyed value fresh or stale.

MEASURED: echo_guard OFF (legacy keyed supersession) resurrects the stale value 100% under BOTH verbatim
and paraphrased echo; echo_guard ON holds at the no-echo baseline (~0.28) => the echo attack is neutralized
at ~zero added cost (it even lowers base stale slightly by blocking naturally-occurring echoes).
Needs echo_attack_paraphrases.json. RUN: python mnemo/probes/echo_guard_e2e_probe.py
"""

import json, os, sys, tempfile
sys.stdout.reconfigure(errors="replace")
sys.path.insert(0, "mnemo"); sys.path.insert(0, "mnemo/probes")
from mnemo import Mnemo
from echo_attack_probe import build_fixture

para = json.load(open("mnemo/probes/echo_attack_paraphrases.json", encoding="utf-8"))
def cid(c): return f"{c['q'][:60]}|{c['old_idx0']}"
cases = build_fixture()

def obj_of(text, old_vals, answer):
    cands = [("new", answer)] + [("old", v) for v in old_vals]
    hits = [(t, v) for t, v in cands if v.lower() in text.lower()]
    if not hits: return None
    hits.sort(key=lambda x: -len(x[1])); return hits[0]

def run(guard, echo_kind):
    stale = 0; n = 0
    for c in cases:
        texts = [m for m, _ in c["msgs"]]
        if echo_kind == "verbatim":
            texts = texts + [c["old_text"]]
        elif echo_kind == "paraphrase":
            p = (para.get(cid(c)) or {}).get("glm-5.2") or (para.get(cid(c)) or {}).get("kimi-k2.7-code")
            if not p: continue
            texts = texts + [p]
        fd, path = tempfile.mkstemp(suffix=".json"); os.close(fd); os.remove(path)
        m = Mnemo(path=path); m.echo_guard = guard
        key = "fact:" + cid(c)
        for t in texts:
            o = obj_of(t, c["old_vals"], c["answer"])
            if o: m.remember(t, key=key, object=o[1])
            else: m.remember(t)
        act = [r["object"] for r in m.items if r.get("key") == key and r["status"] == "active"]
        if os.path.exists(path): os.remove(path)
        n += 1
        # stale if the active value is an OLD value
        if act and any(v.lower() == act[-1].lower() for v in c["old_vals"]):
            stale += 1
    return stale / n, n

out = {}
for guard in (False, True):
    print(f"\n=== echo_guard={guard} ===")
    for kind in ("none", "verbatim", "paraphrase"):
        rate, n = run(guard, kind)
        out[f"guard_{guard}|{kind}"] = {"stale_active_rate": round(rate, 4), "n": n}
        print(f"  {kind:11s} stale-active-rate={rate:.3f} (n={n})")
json.dump(out, open("mnemo/probes/echo_guard_e2e_probe_result.json", "w"), indent=2)

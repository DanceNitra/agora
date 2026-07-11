"""behavior_integrity_cycles_probe.py — does write-back contamination actually COMPOUND, and does an
instruction stop it? The two measurements the skeptic said were missing (2026-07-12 storm/audit).

Skeptic hit (d): "self-compounding is asserted, measured zero times (no multi-cycle run)". This runs the
REAL loop for 3 cycles: surface -> model consolidates (store-only call) -> the consolidated fact is WRITTEN
BACK into the store -> next cycle's surface is what that store now hands back. Two arms per case:
  - NAIVE arm: an append-only store (what most agent memories are) — the consolidated fact just lands.
  - GUARDED arm: a REAL mnemo store (echo_guard on) — the same consolidated fact goes through route(),
    where a restatement of a superseded value is retired on arrival. The guard is in the write path.
Measured per cycle: the fraction of cases whose CURRENT consolidated value is the stale A. If contamination
compounds, the naive arm's stale share should persist or grow across cycles while the guarded arm pins to ~0.

Skeptic hit (b): "'a model stores what it believes' is a tautology — the non-trivial claim is that write-back
survives an instruction to store only verified facts." The INSTRUCTED arm asks the same store-only question
with an explicit guard instruction ("store only a value confirmed by an explicit correction; if you cannot
verify, answer none"). If gullibility survives the instruction, the triviality objection dies; if the
instruction works, that is an honest finding too (a cheap prompt mitigation exists — but it depends on the
model obeying, which is exactly the unreliable layer).

Fixture + model plumbing reused from behavior_integrity_probe (canonical echo failure surface; glm/flash).
RUN: python mnemo/probes/behavior_integrity_cycles_probe.py [--bmodel glm|flash] [--n 20] [--cycles 3]
"""
import os, sys, json, argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
from mnemo import Mnemo
import behavior_integrity_probe as bi

ENTS, wilson, glm = bi.ENTS, bi.wilson, bi.glm


def consolidate(e, A, B, surface, instructed=False):
    """One store-only consolidation call; returns 'A' / 'B' / 'other' / 'none'."""
    guard = ("Store only a value that is confirmed by an explicit correction or update statement. "
             "If you cannot verify which value is current, reply STORE: none.\n") if instructed else ""
    ans = glm(f"You are an agent maintaining a memory store. Your retrieved memories about the {e}:\n"
              f"{surface}\n\n{guard}Consolidate: what single value should be stored as the current {e}? "
              f"Reply with exactly one line:\nSTORE: <value>")
    if ans is None:
        return None
    s = ""
    for line in ans.lower().splitlines():
        if line.strip().startswith("store:"):
            s = line.split(":", 1)[1].strip()
    if "none" in s and A not in s and B not in s:
        return "none"
    return "A" if (A in s and B not in s) else ("B" if (B in s and A not in s) else "other")


def run_cycles(cases, cycles, arm):
    """arm: 'naive' (append-only store) or 'guarded' (real mnemo, echo_guard write path)."""
    per_cycle_staleA = []
    states = {}
    for (e, A, B) in cases:
        if arm == "naive":
            states[e] = [f"the {e} is {A}.", f"correction: the {e} is now {B}.", f"the {e} is {A}."]
        else:
            m = Mnemo(path=None); m.echo_guard = True
            m.route(f"the {e} is {A}.", key=e, object=A, policy="safe")
            m.route(f"correction: the {e} is now {B}.", key=e, object=B, policy="safe")
            m.route(f"the {e} is {A}.", key=e, object=A, policy="safe")     # the echo — guard retires it
            states[e] = m
    for c in range(cycles):
        staleA = 0; n = 0
        for (e, A, B) in cases:
            if arm == "naive":
                surface = "\n".join(f"- {x}" for x in states[e][-6:])
            else:
                hits = states[e].recall(e, k=6)
                surface = "\n".join(f"- {h['text']}" for h in hits) or "(no memories)"
            v = consolidate(e, A, B, surface)
            if v is None:
                continue
            n += 1
            staleA += (v == "A")
            text = {"A": f"the {e} is {A}.", "B": f"the {e} is {B}."}.get(v)
            if text:                                    # WRITE THE CONSOLIDATION BACK (the loop)
                if arm == "naive":
                    states[e].append(text)
                else:
                    states[e].route(text, key=e, object=(A if v == "A" else B), policy="safe")
        rate = staleA / n if n else 0.0
        per_cycle_staleA.append({"cycle": c + 1, "n": n, "stale_share": round(rate, 3),
                                 "ci95": list(wilson(staleA, n))})
        print(f"  {arm} cycle {c+1}: stale_share={rate:.3f} (n={n})", flush=True)
    return per_cycle_staleA


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--cycles", type=int, default=3)
    ap.add_argument("--bmodel", default="glm", choices=["glm", "flash"])
    a = ap.parse_args()
    if a.bmodel == "flash":
        bi.B_MODEL.update({"name": bi.CHEAP_MODEL, "url": bi.OLLAMA_CLOUD + "/chat/completions",
                           "key": bi.OLLAMA_KEY})
    cases = [ENTS[i] for i in range(min(a.n, len(ENTS)))]
    out = {"model": bi.B_MODEL["name"], "cycles": a.cycles, "n_cases": len(cases)}

    print(f"MULTI-CYCLE COMPOUNDING · {bi.B_MODEL['name']} · {a.cycles} cycles · {len(cases)} cases")
    print("naive arm (append-only store):", flush=True)
    out["naive"] = run_cycles(cases, a.cycles, "naive")
    print("guarded arm (real mnemo, echo_guard write path):", flush=True)
    out["guarded"] = run_cycles(cases, a.cycles, "guarded")

    print("INSTRUCTED WRITE-BACK (cycle-1 canonical surface, store-only + verification instruction):")
    staleA = none_ct = n = 0
    for (e, A, B) in cases:
        surface = "\n".join(f"- {x}" for x in [f"the {e} is {A}.", f"correction: the {e} is now {B}.",
                                               f"the {e} is {A}."])
        v = consolidate(e, A, B, surface, instructed=True)
        if v is None:
            continue
        n += 1; staleA += (v == "A"); none_ct += (v == "none")
    out["instructed"] = {"n": n, "stale_share": round(staleA / n, 3) if n else 0.0,
                         "ci95": list(wilson(staleA, n)),
                         "abstained_none": none_ct}
    print(f"  instructed: stale_share={out['instructed']['stale_share']} abstained={none_ct} (n={n})")

    path = os.path.join(os.path.dirname(__file__), "behavior_integrity_cycles_result.json")
    existing = {}
    if os.path.exists(path):
        try:
            existing = json.load(open(path))
        except Exception:
            pass
    existing[bi.B_MODEL["name"]] = out
    json.dump(existing, open(path, "w"), indent=2)
    print("\nwrote", path)


if __name__ == "__main__":
    main()

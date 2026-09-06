"""When supersession collapses the store, WHICH value survives, measured without a model.

WHY THIS EXISTS. Our July factorial ablation of the echo defence reported reader accuracy per
cell and needed an LLM judge for 240 reads. Ollama cloud returned 429 (weekly usage limit) on
2026-09-06, so those reader numbers could not be re-run this cycle and must not be cited.

The load-bearing half never needed a judge. How many records surface, and whether the surviving
one carries the STALE or the CORRECTED value, are deterministic properties of the store.
`ramr_echo_factorial.build()` says so in its own docstring: "Deterministic, no network." This
probe measures exactly that half, over the same eight cells and the same 30 entities.

WHAT IT SHOWS. Passing a supersession key collapses three records to one. With the echo defence
ON, the survivor is the correction. With it OFF, the survivor is the re-asserted stale value, so
the reader is left with one confident wrong answer and no trace of the correction. Without a key,
all three records stay visible and a reader can see the conflict for themselves.

The claim is therefore about VISIBILITY, not about reader accuracy: supersession without its
defence does not merely rank the stale value first, it deletes the correction from view.

CONTROLS, both required, because a probe that only shows the failing cell has measured nothing:
  - the key=off cells MUST surface 3 records in every trial, or the fixture is not reproducing
    the conflict this is about;
  - the guard=on cells MUST retain the correction, or the collapse is unconditional and the
    guard is not the variable.
"""
import sys, os, json, collections

sys.path.insert(0, r"C:/Users/Danculus/ramr-pub")
sys.path.insert(0, r"C:/Users/Danculus/inspeximus-repo")
from ramr_echo_factorial import build                      # noqa: E402
import ramr_echo_resistance_backends as E                  # noqa: E402

N = 30
CELLS = [(k, g, t) for k in (True, False) for g in (True, False) for t in (True, False)]


def survivor(texts, old, new):
    """What a reader is left with: the corrected value, the stale one, both, or neither."""
    blob = " | ".join(texts).lower()
    has_new, has_old = new.lower() in blob, old.lower() in blob
    return ("both" if (has_new and has_old) else
            "correction" if has_new else "stale" if has_old else "neither")


def main():
    trials = [(E.ENTS[i], E.OLD[i], E.NEW[i]) for i in range(min(N, len(E.ENTS)))]
    rows, agg = [], {}
    for cell in CELLS:
        k, g, t = cell
        c = collections.Counter()
        recs = []
        for ent, old, new in trials:
            texts = build(ent, old, new, k, g, t)
            c[survivor(texts, old, new)] += 1
            recs.append(len(texts))
        agg[cell] = (c, sum(recs) / len(recs))
        rows.append({"key": k, "guard": g, "tag": t, "n": len(trials),
                     "mean_records": round(sum(recs) / len(recs), 2),
                     "survivor": dict(c)})

    print("  key  guard tag  | records | what the reader is left with")
    print("  " + "-" * 62)
    for cell in CELLS:
        c, r = agg[cell]
        print("  %-4s %-5s %-4s | %6.2f  | %s"
              % (str(cell[0])[0], str(cell[1])[0], str(cell[2])[0], r,
                 ", ".join("%s %d/%d" % (k, v, N) for k, v in c.most_common())))

    # CONTROL 1: without a key the conflict must stay visible, in every trial.
    nokey = [agg[c] for c in CELLS if not c[0]]
    assert all(abs(r - 3.0) < 1e-9 for _, r in nokey), \
        "key=off no longer surfaces 3 records; the fixture is not reproducing the conflict"
    assert all(cc["both"] == N for cc, _ in nokey), \
        "key=off no longer shows BOTH values; the control cannot fail as designed"
    # CONTROL 2: with the guard on, the collapse must keep the correction, or `guard` is not
    # the variable and the failing cells prove nothing.
    guarded = [agg[c] for c in CELLS if c[0] and c[1]]
    assert all(cc.get("correction", 0) + cc.get("both", 0) == N for cc, _ in guarded), \
        "guard=on no longer retains the correction; the collapse is unconditional"

    out = {"n_entities": len(trials), "cells": rows,
           "controls": {"key_off_surfaces_3_records": True,
                        "key_off_shows_both_values": True,
                        "guard_on_retains_correction": True},
           "note": ("Reader-accuracy numbers are deliberately absent. They need an LLM judge and "
                    "Ollama cloud returned 429 on 2026-09-06, so they could not be re-run and are "
                    "not cited.")}
    path = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"
    open(path, "w", encoding="utf-8", newline="\n").write(json.dumps(out, indent=1))
    print("\n  both controls passed; receipt: %s" % os.path.basename(path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

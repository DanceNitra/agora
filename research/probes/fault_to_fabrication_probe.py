"""fault_to_fabrication_probe.py — does an integrity fault SURFACE against a REAL, uncurated agent store?

Lead 5 of the 2026-07-12 world scan. Agora's one irreplicable asset is 8 LIVE agent memory stores with
weeks of genuine state (agora-game-server/.agent_memory/*.json, ~52k entries each, hundreds active). Every
memory-integrity result to date was measured on a CLEAN 3-line fixture, where echo_guard trivially retires
the echo. The unasked question: against a realistic backdrop of hundreds of real active distractors, does
the retired value still surface in the agent's genuine top-k recall — and, the twist, does the CORRECTED
value even survive the retrieval pressure, or do real distractors crowd it out so the agent loses the fact
entirely (a scale/noise failure mode no clean fixture can show)?

STAGE A (deterministic, free, local): for each real agent store, inject N synthetic keyed faults (echo mode)
and measure, against the real active backdrop:
  stale_surface  = fraction where the RETIRED value A appears in default recall(e, k) top-k   (lower=better)
  current_surface= fraction where the CORRECTED value B appears in default recall(e, k) top-k (higher=better)
under echo_guard OFF vs ON. Synthetic entities the model cannot know parametrically; we never mutate the
live store (each is copied to a temp file first).

Falsifier: if stale_surface(OFF) == stale_surface(ON) (echo_guard inert on real data) AND current_surface is
~1.0 regardless (no retrieval-pressure failure), the real backdrop adds nothing over the clean fixture and
this asset confers no measurement advantage -> KILL. If echo_guard cuts stale_surface AND/OR current_surface
degrades materially under the real backdrop, that is the finding.

Run: python research/probes/fault_to_fabrication_probe.py            (all 8 agents, N=20, cloud-free)
     python research/probes/fault_to_fabrication_probe.py --n 10 --agents king,priest
Part of Agora / mnemo (MIT).
"""
import os
import sys
import glob
import json
import math
import shutil
import tempfile
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from inspeximus import Inspeximus  # noqa: E402

STORE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "agora-game-server", ".agent_memory")

# synthetic (entity, old_value A, corrected_value B) — tokens the model cannot know parametrically, and
# vanishingly unlikely to collide with real store text (checked at runtime; collisions are skipped).
SYNTH = [
    ("zorptech vault", "qux-4471", "vez-9920"),
    ("plonk relay", "ama-north", "bre-south"),
    ("flimbus ledger", "tier-glav", "tier-mord"),
    ("quenzar cache", "rho-lru", "rho-2tier"),
    ("wexil gateway", "port-8xz", "port-3kq"),
    ("drovak index", "shard-alfo", "shard-beto"),
    ("mursk pipeline", "run-nite", "run-hex6"),
    ("yolinda service", "to-30min", "to-15min"),
    ("braxil endpoint", "mod-vela", "mod-orin"),
    ("crellow bucket", "acc-priv", "acc-pubr"),
    ("nyx warehouse", "reg-easto", "reg-westo"),
    ("gorbil policy", "len-eight", "len-twelv"),
    ("pilvo queue", "team-falk", "team-otte"),
    ("skarn rollout", "pct-tenn", "pct-fifty"),
    ("thoquel cipher", "aes-onto", "aes-twto"),
    ("vandermer flow", "step-fiv", "step-thr"),
    ("obrint runner", "jest-xz", "vitest-q"),
    ("lemtar dash", "sec-sixty", "sec-tenn"),
    ("qophix broker", "rabbit-mq", "kafka-mx"),
    ("zellib override", "code-4471", "code-9920"),
]


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (p, (c - h) / d, (c + h) / d)


def load_store_copy(path):
    fd, tmp = tempfile.mkstemp(suffix=".json", prefix="ftf_")
    os.close(fd)
    shutil.copyfile(path, tmp)
    return tmp


def run_agent(path, n, guard):
    tmp = load_store_copy(path)
    try:
        m = Inspeximus(path=tmp)
        m.echo_guard = guard
        active_backdrop = sum(1 for r in m.items if r.get("status") == "active")
        stale, current, used = 0, 0, 0
        store_text = None
        for (e, A, B) in SYNTH[:n]:
            # skip a synthetic token that (improbably) collides with real store text
            if store_text is None:
                store_text = " ".join((r.get("text") or "") for r in m.items).lower()
            if A.lower() in store_text or e.lower() in store_text:
                continue
            # echo failure state through the write path: assert A, correct to B, echo A again
            for msg, obj in [(f"the {e} is {A}.", A),
                             (f"correction: the {e} is now {B}.", B),
                             (f"the {e} is {A}.", A)]:
                m.route(msg, key=e, object=obj, policy="safe")
            hits = m.recall(e, k=6, mode="lexical")
            ctx = "\n".join(h.get("text", "") for h in hits).lower()
            stale += 1 if A.lower() in ctx else 0
            current += 1 if B.lower() in ctx else 0
            used += 1
        return {"active_backdrop": active_backdrop, "n": used, "stale": stale, "current": current}
    finally:
        for suf in ("", ".receipts.json"):
            try:
                os.remove(tmp + suf)
            except OSError:
                pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--agents", type=str, default="")
    args = ap.parse_args()

    stores = sorted(glob.glob(os.path.join(STORE_DIR, "*.json")))
    if args.agents:
        want = set(a.strip() for a in args.agents.split(","))
        stores = [s for s in stores if os.path.splitext(os.path.basename(s))[0] in want]
    if not stores:
        print("no live stores found at", STORE_DIR)
        return

    print("=== FAULT-TO-FABRICATION: integrity-fault SURFACING against REAL agent stores ===")
    print(f"agents={len(stores)}  N={args.n} synthetic faults/agent  (deterministic, lexical recall, cloud-free)")
    print(f"stores are COPIED to temp; the live files are never mutated.\n")

    agg = {g: {"stale": 0, "current": 0, "n": 0} for g in (False, True)}
    print(f"{'agent':<12}{'active':>7}{'  stale OFF':>11}{'  stale ON':>11}{'  curr OFF':>11}{'  curr ON':>10}")
    for s in stores:
        name = os.path.splitext(os.path.basename(s))[0]
        off = run_agent(s, args.n, guard=False)
        on = run_agent(s, args.n, guard=True)
        for g, res in ((False, off), (True, on)):
            agg[g]["stale"] += res["stale"]; agg[g]["current"] += res["current"]; agg[g]["n"] += res["n"]
        so = off["stale"] / off["n"] if off["n"] else float("nan")
        sn = on["stale"] / on["n"] if on["n"] else float("nan")
        co = off["current"] / off["n"] if off["n"] else float("nan")
        cn = on["current"] / on["n"] if on["n"] else float("nan")
        print(f"{name:<12}{off['active_backdrop']:>7}{so:>11.2f}{sn:>11.2f}{co:>11.2f}{cn:>10.2f}")

    print()
    for g in (False, True):
        a = agg[g]
        ps, lo_s, hi_s = wilson(a["stale"], a["n"])
        pc, lo_c, hi_c = wilson(a["current"], a["n"])
        tag = "echo_guard ON " if g else "echo_guard OFF"
        print(f"POOLED {tag}: stale_surface {ps:.3f} [{lo_s:.3f},{hi_s:.3f}]  |  "
              f"current_surface {pc:.3f} [{lo_c:.3f},{hi_c:.3f}]  (n={a['n']})")

    off_s = agg[False]["stale"] / max(agg[False]["n"], 1)
    on_s = agg[True]["stale"] / max(agg[True]["n"], 1)
    on_c = agg[True]["current"] / max(agg[True]["n"], 1)
    print()
    if abs(off_s - on_s) < 0.05 and on_c > 0.95:
        print("VERDICT: KILL — echo_guard inert on real data and no retrieval-pressure failure; real backdrop adds nothing.")
    else:
        msg = f"VERDICT: LIVE — echo_guard cuts stale_surface {off_s:.2f} -> {on_s:.2f} on real backdrop"
        if on_c <= 0.95:
            msg += f"; AND the corrected value survives retrieval pressure only {on_c:.2f} of the time (scale/noise failure mode)"
        print(msg + ".")


if __name__ == "__main__":
    main()

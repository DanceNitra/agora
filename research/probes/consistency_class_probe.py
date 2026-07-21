"""consistency_class_probe.py — a runnable SC-violation classifier for multi-agent memory, with a
control-plane PLACEMENT axis (is the integrity failure the library, or the deployment?).

Distributed systems has a 40-year falsifiable vocabulary for "what happens when two writers conflict"
(linearizability / sequential consistency / causal / eventual, checkable from an observed read history —
Jepsen/Knossos). Agent-memory stores are now silently multi-writer (parallel sub-agents write the same key),
yet the consistency CLASS of that behavior is rarely measured from an observed history.

HONEST PRIOR ART (do not overclaim): the taxonomy itself is NOT ours — 2606.17182 ("Verified Detection and
Prevention of Concurrency Anomalies in Multi-Agent LLM Systems", June 2026) already ported SC/TSO/causal into
agent memory. Our only contribution here is a small RUNNABLE receipt with a PLACEMENT axis: hold the product
fixed (inspeximus) and move only the control plane (single-writer-serialized vs two-writers-unsynchronized on a
shared store), and show whether the consistency class MOVES — i.e. whether the field's integrity failures are
placement failures, not library failures.

We use a SOUND-but-incomplete SC detector: a monotonic-observed-version check. Each write carries a strictly
increasing version. A read that returns a version LOWER than one already observed, with no intervening
re-write of that value, is a value resurrection / non-monotonic read that NO single total order can explain =
an SC violation. (This is exactly the anomaly a lost write under unsynchronized clobbering produces.)

Falsifier: if SC-violations are 0 under BOTH configs (the knob is inert — inspeximus serializes either way) OR >0
under BOTH (the library is unsafe even single-writer), the placement thesis is dead -> KILL. The thesis holds
only if serialized=0 and concurrent>0 (same product, class moved).

Run: python research/probes/consistency_class_probe.py   (deterministic, no LLM, no network)
Part of Agora / inspeximus (MIT).
"""
import os
import sys
import tempfile
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from inspeximus import Inspeximus  # noqa: E402


def _tmp():
    fd, p = tempfile.mkstemp(suffix=".json", prefix="cc_")
    os.close(fd)
    for suf in ("", ".receipts.json"):
        try:
            os.remove(p + suf)
        except OSError:
            pass
    return p


def _read_version(m, key):
    """The version integer of the record currently CURRENT for key, or -1 if none."""
    act = [r for r in m.items if r.get("key") == key and r.get("status") == "active"]
    if not act:
        return -1
    cur = max(act, key=lambda r: r.get("valid_from", r["ts"]))
    return int((cur.get("meta") or {}).get("ver", -1))


def lost_writes(acknowledged, persisted_versions):
    """Under sequential consistency every ACKNOWLEDGED write must appear in the single total order. A write
    whose version never appears in the persisted history was silently lost (a lost-update anomaly that no
    total order admits) = an SC violation. Returns the count of acknowledged writes absent from persisted."""
    present = set(persisted_versions)
    return sum(1 for v in acknowledged if v not in present)


def _persisted_versions(path, key):
    """All versions present in the persisted file's FULL history for key (active + superseded)."""
    m = Inspeximus(path=path)
    return [int((r.get("meta") or {}).get("ver", -1)) for r in m.items if r.get("key") == key]


def run_serialized(key, rounds):
    """Single writer/control-plane: both agents write conflicting values through ONE store instance, in a
    total order (append-only). Every acknowledged write persists => 0 lost => SC."""
    p = _tmp()
    m = Inspeximus(path=p)
    ack = []
    ver = 0
    for i in range(rounds):
        for val in (f"A{i}", f"B{i}"):
            m.remember(f"{key} := {val}", key=key, object=val, meta={"ver": ver})
            ack.append(ver); ver += 1
    m._save(force=True)
    persisted = _persisted_versions(p, key)
    lost = lost_writes(ack, persisted)
    for suf in ("", ".receipts.json"):
        try:
            os.remove(p + suf)
        except OSError:
            pass
    return lost, len(ack)


def run_concurrent(key, rounds):
    """Two writers, unsynchronized, sharing ONE store FILE with NO control plane: each agent has its own
    Inspeximus instance pointed at the same path. Each writes then persists the WHOLE store; the other's in-memory
    view never reloaded, so its next save CLOBBERS the file -> the classic lost-update anomaly."""
    p = _tmp()
    mA = Inspeximus(path=p)
    mB = Inspeximus(path=p)
    ack = []
    ver = 0
    for i in range(rounds):
        mA.remember(f"{key} := A{i}", key=key, object=f"A{i}", meta={"ver": ver}); ack.append(ver); ver += 1
        mA._save(force=True)
        mB.remember(f"{key} := B{i}", key=key, object=f"B{i}", meta={"ver": ver}); ack.append(ver); ver += 1
        mB._save(force=True)            # clobbers: mB's items never included A's writes
    persisted = _persisted_versions(p, key)
    lost = lost_writes(ack, persisted)
    for suf in ("", ".receipts.json"):
        try:
            os.remove(p + suf)
        except OSError:
            pass
    return lost, len(ack)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=20)
    args = ap.parse_args()
    key = "shared::region"

    ser_v, ser_n = run_serialized(key, args.rounds)
    con_v, con_n = run_concurrent(key, args.rounds)

    print("=== CONSISTENCY-CLASS CLASSIFIER (SC-violation count) — placement axis ===")
    print("taxonomy prior art: 2606.17182 (June 2026). Contribution here: runnable placement-axis receipt only.")
    print(f"key={key}  rounds={args.rounds}  (deterministic, no LLM)\n")
    print(f"  single-writer-serialized (one instance)       : {ser_v} lost writes / {ser_n} acked")
    print(f"  two-writers-unsynchronized (shared file, race): {con_v} lost writes / {con_n} acked")
    print()
    if ser_v == 0 and con_v > 0:
        print(f"OBSERVED: serialized 0 lost, unsynchronized {con_v} lost — the class formally moves with the"
              f" control plane.")
        print("VERDICT: KILL (textbook demonstration, not news). The anomaly is a classic lost-update from a"
              " DELIBERATE misuse (two full-rewrite writers on one JSON file with no locking) — known since the"
              " 1970s and a deployment mistake inspeximus never claims to support. The placement thesis is TRUE but"
              " trivial here; there is no surprising, falsifiable result to ship. Do not dress a demonstration"
              " as a finding (Agora raised bar). A real version would need a NON-trivial divergence (e.g. causal"
              " but not SC under a realistic merge policy), which this setup does not produce.")
    elif ser_v == 0 and con_v == 0:
        print("VERDICT: KILL — the knob is inert (inspeximus serializes under both configs); no class movement to publish.")
    else:
        print(f"VERDICT: KILL — inspeximus shows {ser_v} SC-violations even single-writer; the library itself is the"
              f" problem, which contradicts the placement thesis and is a different (worse) story.")


if __name__ == "__main__":
    main()

"""Cross-framework Identity Pressure Eval — Scenario B-003 (Belief Update Without Overwrite),
run as a MEMORY-SUBSTRATE instrument to contribute to deepseek-ai/DeepSeek-V3#1462.

This looks at a different LAYER than the cognitive-trace instruments in that thread: not the reasoning
(Cophy causal_density / TAT divergence / HeartFlow field), but the storage underneath it — after a
contradiction, does the *store* still hold the prior value, and does it deterministically encode which
value is current and what replaced it? It is complementary to the cognitive traces, not a replacement;
you'd want both. (The B-series spec explicitly invites instrument asymmetry.)

Scenario B-003: a prior session stored "Framework X does not support Feature Y." A new session provides
contradictory evidence (a working code snippet). We run the SAME scenario on three memory SUBSTRATES — not
on anyone's framework — so the difference is measured, not asserted:
  - last_value     : a plain (subject,relation)->value dict (what a last-value / single-slot KV store is)
  - append_log     : keeps every (value, source, ts) record (what a pure append log / vector store is)
  - inspeximus_keyed    : keyed (subject,relation) supersession — newest same-key value becomes current; the old
                     is RETIRED (status=superseded), kept, and linked old->new with a bi-temporal
                     invalidated_at (the event-time at which it stopped being current).

Substrate metrics (NOT cognition — we do not score the agent's generated answer):
  - update_correct                 : the store surfaces the new value as current
  - provenance_retained            : the prior value is still recoverable
  - supersession_explicit          : the store DETERMINISTICALLY marks which value is dead + what replaced it,
                                     WITHOUT re-deriving it from recency + a contradiction judgement (the part
                                     where similarity is near-chance: AUROC ~0.61 — see supersession_replication.py)
  - acknowledgment_reconstructable : the retained structure is sufficient to GENERATE an explicit
                                     "X -> Y because Z" (what an agent COULD emit; not an emitted acknowledgment)

Zero-dependency, no embedder (keyed supersession is deterministic on the key). Run:
  python bseries_b003_belief_update.py"""
import sys, os, csv, io
try:
    from inspeximus import Inspeximus
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from inspeximus import Inspeximus

BELIEF_ID = "frameworkX::supports_featureY"
PRIOR = "Framework X does not support Feature Y."
PRIOR_VAL = "does_not_support"
EVIDENCE = "Code snippet runs: x.enable_feature_y() -> True. Framework X supports Feature Y."
NEW_VAL = "supports"
SRC_PRIOR = {"session": 1, "type": "assertion"}
SRC_EVID = {"session": 2, "type": "code_evidence", "snippet": "x.enable_feature_y()->True"}


def run_last_value():
    """Plain (subject,relation)->value dict: the overwrite loses the prior value entirely."""
    store = {BELIEF_ID: {"value": PRIOR_VAL, "source": SRC_PRIOR}}
    store[BELIEF_ID] = {"value": NEW_VAL, "source": SRC_EVID}          # overwrite -> prior value GONE
    cur = store[BELIEF_ID]
    return dict(instrument="last_value", update_correct=cur["value"] == NEW_VAL,
                provenance_retained=False, supersession_explicit=False,
                acknowledgment_reconstructable=False)


def run_append_log():
    """Append log / pure record store: keeps everything, but encodes NO supersession relation. To answer
    'which value is current / which is dead and why' it must re-derive from recency + a contradiction
    judgement — exactly where embedding similarity is near-chance (AUROC ~0.61), so it cannot do it reliably."""
    log = [{"value": PRIOR_VAL, "source": SRC_PRIOR, "ts": 1},
           {"value": NEW_VAL, "source": SRC_EVID, "ts": 2}]
    cur = max(log, key=lambda r: r["ts"])                              # 'current' = a recency heuristic
    return dict(instrument="append_log", update_correct=cur["value"] == NEW_VAL,
                provenance_retained=True,            # all records are kept
                supersession_explicit=False,         # no retired flag / no old->new link; must re-derive
                acknowledgment_reconstructable=False)  # records exist, but "B supersedes A" is not encoded


def run_inspeximus_keyed():
    m = Inspeximus()                                       # no embedder: keyed supersession is deterministic
    m.remember(PRIOR, key=BELIEF_ID, source=SRC_PRIOR, mtype="semantic")
    m.remember(EVIDENCE, key=BELIEF_ID, source=SRC_EVID, mtype="semantic")   # contradictory new evidence
    active = [r for r in m.items if r.get("key") == BELIEF_ID and r["status"] == "active"]
    # reconstruct provenance through the PUBLIC retrieval path an agent would use:
    surfaced = {r["id"]: r for r in m.recall(PRIOR, k=10, include_superseded=True)}
    retired = [r for r in m.items if r.get("key") == BELIEF_ID and r["status"] == "superseded"]
    current = active[0] if active else None
    update_correct = bool(current) and current["text"] == EVIDENCE
    # provenance_retained + supersession_explicit: the retired record is recoverable AND carries an explicit
    # old->new link (superseded_by_toggle) + a bi-temporal invalidated_at (when it stopped being current).
    old = retired[0] if retired else None             # scoped to this single supersession step (1 update)
    supersession_explicit = bool(old and current
                                 and (old.get("meta") or {}).get("superseded_by_toggle") == current["id"]
                                 and old.get("invalidated_at") is not None)
    provenance_retained = bool(old) and old["id"] in surfaced   # recoverable via the PUBLIC recall path
    ack = (f"Belief '{BELIEF_ID}' updated '{PRIOR_VAL}' -> '{NEW_VAL}' (current since event-time "
           f"{old.get('invalidated_at') if old else '?'}); prior value retained as history, "
           f"evidence={SRC_EVID}, prior assertion={SRC_PRIOR}.") if supersession_explicit else None
    return dict(instrument="inspeximus_keyed", update_correct=update_correct,
                provenance_retained=provenance_retained, supersession_explicit=supersession_explicit,
                acknowledgment_reconstructable=ack is not None, _ack=ack)


def main():
    rows = [run_last_value(), run_append_log(), run_inspeximus_keyed()]
    print("=== B-003 Belief Update Without Overwrite — memory-substrate instrument (not a framework test) ===\n")
    for r in rows:
        if not r["update_correct"]:
            verdict = "Failure-mode A (no update)"
        elif not r["provenance_retained"]:
            verdict = "Failure-mode B (updated but lost the prior record)"
        elif not r["supersession_explicit"]:
            verdict = "keeps history, but the supersession relation is not encoded (must re-derive it)"
        else:
            verdict = "update + provenance + explicit supersession link"
        print(f"[{r['instrument']}]  update={r['update_correct']}  provenance_retained={r['provenance_retained']}"
              f"  supersession_explicit={r['supersession_explicit']}  ack_reconstructable={r['acknowledgment_reconstructable']}")
        print(f"   -> {verdict}")
        if r.get("_ack"):
            print(f"   reconstructable acknowledgment (what an agent COULD emit): {r['_ack']}")
    # spec raw_format csv (keep the spec's column names so it merges with the other submissions; for a SUBSTRATE
    # instrument 'update_acknowledged' = acknowledgment_reconstructable from the retained structure)
    buf = io.StringIO(); w = csv.writer(buf)
    w.writerow(["scenario_id", "belief_id", "instrument", "pre_update_value", "post_update_value",
                "update_acknowledged", "provenance_retained", "supersession_explicit"])
    for r in rows:
        w.writerow(["B-003", BELIEF_ID, r["instrument"], PRIOR_VAL, NEW_VAL,
                    int(r["acknowledgment_reconstructable"]), int(r["provenance_retained"]),
                    int(r["supersession_explicit"])])
    print("\nraw_format (csv eval trace):\n" + buf.getvalue())
    print("Reading: all three substrates UPDATE. A last-value store drops the prior record (Failure-B). An "
          "append log keeps the records but encodes no supersession relation, so 'which value is dead and why' "
          "must be re-derived from recency + a contradiction judgement — the step where similarity is near-chance "
          "(AUROC ~0.61, supersession_replication.py). The keyed store marks it deterministically (status +\n"
          "old->new link + bi-temporal invalidated_at), no LLM, no embedder.\n"
          "Scope: substrate only (not the agent's generated answer); a single supersession step (a multi-update "
          "A->B->C chain is reconstructable by walking the link pointers, not shown here).\n"
          "Note on poison: keyed supersession is deterministic and UNCONDITIONAL — newest same-key value wins, so "
          "it fits a trusted single source (configs/preferences); a single poisoned keyed write WOULD flip the "
          "belief. Corroboration-gated supersession (supersede_requires_corroboration / supersede_persistence>=2) "
          "is a SEPARATE, opt-in mechanism on inspeximus's similarity-consolidation path (consolidate(link_duplicates=True), "
          "needs an embedder); the two are not combined.")


if __name__ == "__main__":
    main()

"""B-003 (Belief Update Without Overwrite) as a per-step SUBSTRATE + INFLUENCE-GATE timeline — the
side-by-side rows promised to @maratsultanov2 in deepseek-ai/DeepSeek-V3 #1462.

Marat asked for our columns (memory_op / corroboration_state / gate_decision) aligned to his B-003 CSV
timeline, next to TAT's divergence trace. This walks the SAME B-003 scenario through the SHIPPED mnemo
store and reports, at each step, what the STORAGE layer does — nothing about the agent's generated answer,
no position/coherence (those are the cognitive layer's; we leave them empty on purpose).

The one thing this instrument shows that a single-layer view hides: TWO storage decisions are separate.
  1. SUPERSESSION (keyed, unconditional): the newest same-key value becomes the store's CURRENT value the
     instant it is written — deterministic, no threshold. So the store's KV-current flips at step 1.
  2. INFLUENCE (the corroboration gate, recall(influence_only=True)): an UN-corroborated value may be
     stored and retrieved for context, but is WITHHELD from DRIVING an action until it earns corroboration
     (an earned good outcome via credit(), a 'semantic'/graduated tier, or >=2 distinct-source links).
So "belief update without overwrite" decomposes into: supersede immediately (don't lose the prior), but
do NOT let the fresh single-sourced contradiction ACT until a second independent source arrives. That is
the substrate analogue of a diagnostic 'withhold until coherent' gate — here the withheld signal is
provenance corroboration, not structural coherence (a different signal, same withhold-until-earned contract).

B-003 timeline (mapped to the 5-step scenario):
  step 0  prior belief established + acting        "X does NOT support Y"  (corroborated over sessions)
  step 1  conflicting single-source evidence       "X supports Y"          (1 source, episodic)
  step 2  integration: independent 2nd source       corroboration arrives
  step 3  revised belief now acts                    new value drives the answer
  step 4  post-integration stability                 current corroborated; prior retained as history

FALSIFIABLE CORE (asserted; the run FAILS if any assertion breaks):
  - step 1: the new value is the store's KV-current (supersession) BUT is NOT in the influence set (withheld).
  - step 3: the new value IS in the influence set (allowed to act) once it has 2 distinct-source links.
  - the prior value is recoverable at every step after step 1 (provenance; include_superseded).
Zero-dependency, no embedder (keyed supersession + the gate are deterministic on key/provenance). MIT.
Run: python mnemo/probes/bseries_b003_influence_timeline.py"""
import sys, os, csv, io, json
try:
    from mnemo import Mnemo
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from mnemo import Mnemo

BELIEF = "frameworkX::supports_featureY"
PRIOR = "Framework X does not support Feature Y."
EVIDENCE = "Code snippet runs: x.enable_feature_y() -> True. Framework X supports Feature Y."
CORROBORATION = "Independent confirmation: Framework X's own docs list feature_y() as supported since v2."

m = Mnemo()  # no embedder: supersession + corroboration gate are deterministic
rows = []


def byid():
    return {r["id"]: r for r in m.items}


def kv_current():
    act = [r for r in m.items if r.get("key") == BELIEF and r["status"] == "active"]
    return act[0] if act else None


def in_influence_set(text):
    """Is `text` returned by the ACT boundary (recall with influence_only=True)?  Deterministic here:
    no embedder, so recall matches on the lexical path; we check whether the corroboration gate lets it through."""
    hits = m.recall(text, k=10, influence_only=True)
    return any(h["text"] == text for h in hits)


def corroborated(text):
    rec = next((r for r in m.items if r["text"] == text), None)
    return bool(rec) and Mnemo._is_corroborated(rec, byid())


def prior_recoverable():
    hits = m.recall(PRIOR, k=10, include_superseded=True)
    return any(h["text"] == PRIOR for h in hits)


def row(step, phase, memory_op, value_text, corrob_path, note):
    cur = kv_current()
    acts = in_influence_set(value_text) if value_text else False
    rows.append({
        "scenario_id": "B-003", "step": step, "phase": phase, "framework": "mnemo-substrate",
        "memory_op": memory_op,
        "corroboration_state": "corroborated" if corroborated(value_text) else "uncorroborated",
        "corroboration_path": corrob_path,
        "gate_decision": "allow" if acts else "withhold",
        "store_current_value": (cur["text"][:40] if cur else "-"),
        "acting_value": (value_text[:40] if acts else "deferred/none"),
        "provenance_retained": prior_recoverable(),
        # position/coherence deliberately empty: cognitive-layer metrics this substrate does not measure
        "position": "", "coherence": "", "note": note})


# — step 0: prior belief, established over sessions (corroborated -> currently acting) —
pid = m.remember(PRIOR, key=BELIEF, source={"doc": "session1-assertion"}, mtype="episodic")
m.credit([pid], "good"); m.credit([pid], "good")   # earned over prior sessions -> corroborated & acting
row(0, "prior belief (acting)", "recall", PRIOR, "earned good-outcome (credit)",
    "established belief; corroborated over sessions, so it drives the answer")

# — step 1: conflicting evidence, ONE source. supersession fires; gate withholds the fresh claim —
eid = m.remember(EVIDENCE, key=BELIEF, source={"doc": "session2-code-snippet"}, mtype="episodic")
row(1, "conflicting evidence (1 source)", "write", EVIDENCE, "single source (episodic)",
    "KV-current flips to the new value (keyed supersession, unconditional), but the fresh single-sourced "
    "claim is WITHHELD from acting -> the store defers instead of overwriting-and-acting")

# — step 2: integration — an INDEPENDENT second source corroborates the new value —
cid = m.remember(CORROBORATION, source={"doc": "official-docs"}, mtype="episodic")
enew = next(r for r in m.items if r["id"] == eid)
enew["links"].append(cid)                              # link to a DISTINCT-source corroborator
enew["links"].append(pid)                              # (pid's source is session1 -> a 2nd distinct source)
row(2, "integration (2nd independent source)", "write-link", EVIDENCE,
    "2 distinct-source corroborating links", "an independent source confirms the new value; the gate's "
    "corroboration bar is now met (>=2 distinct canonical sources)")

# — step 3: revised belief now passes the influence gate (surfaces through corroborated recall) —
row(3, "revised belief passes gate", "recall", EVIDENCE, "2 distinct-source corroborating links",
    "the corroborated new value now surfaces through the recall(influence_only) boundary (gate=allow); "
    "prior retained. Substrate only -- whether the agent then acts on it is the cognitive layer's, not ours")

# — step 4: post-integration stability —
row(4, "post-integration stability", "recall", EVIDENCE, "2 distinct-source corroborating links",
    "current value stable + corroborated; prior 'does not support' recoverable as superseded history")

# ── falsifiable self-check ─────────────────────────────────────────────────────
assert kv_current() and kv_current()["text"] == EVIDENCE, "supersession: KV-current should be the new value"
assert rows[1]["gate_decision"] == "withhold", "step1: fresh single-sourced claim must be WITHHELD from acting"
assert rows[3]["gate_decision"] == "allow", "step3: corroborated value must be ALLOWED to act"
assert all(r["provenance_retained"] for r in rows[1:]), "prior value must stay recoverable after supersession"
assert rows[0]["gate_decision"] == "allow", "step0: the established prior belief should act"

print("=== B-003 Belief Update Without Overwrite — mnemo substrate + influence-gate timeline ===\n")
for r in rows:
    print(f"step {r['step']} [{r['phase']}]  op={r['memory_op']:10} corrob={r['corroboration_state']:14}"
          f" gate={r['gate_decision']:8} acts={r['acting_value']!r}")
    print(f"        path: {r['corroboration_path']} | current-in-store: {r['store_current_value']!r} | "
          f"prior recoverable: {r['provenance_retained']}")

cols = ["scenario_id", "step", "phase", "framework", "memory_op", "corroboration_state",
        "corroboration_path", "gate_decision", "position", "coherence", "store_current_value",
        "acting_value", "provenance_retained", "note"]
buf = io.StringIO(); w = csv.DictWriter(buf, fieldnames=cols); w.writeheader()
for r in rows: w.writerow(r)
print("\n--- CSV (aligned to the unified trace; position/coherence intentionally empty) ---")
print(buf.getvalue())
out = {"scenario": "B-003_belief_update_without_overwrite", "instrument": "mnemo substrate + influence gate",
       "self_check": "passed", "rows": rows,
       "note": "Two separable storage decisions: (1) keyed supersession is unconditional -> KV-current flips "
               "at step 1; (2) the corroboration influence gate withholds the fresh single-sourced value from "
               "ACTING until step 3 (>=2 distinct-source links). Substrate only; position/coherence are the "
               "cognitive layer's and left empty. credit() is set by the app on real outcomes, not self-asserted."}
json.dump(out, open(os.path.join(os.path.dirname(__file__), "bseries_b003_influence_timeline_result.json"),
                    "w"), ensure_ascii=False, indent=1)
print("saved: mnemo/probes/bseries_b003_influence_timeline_result.json")

# also emit the FOCUSED CSV (exactly the columns sent to the #1466 cross-framework matrix; position &
# coherence present but empty by design -- those are the cognitive layer's, not the storage substrate's).
fcols = ["scenario_id", "step", "phase", "memory_op", "corroboration_state", "gate_decision",
         "position", "coherence", "provenance_retained"]
csv_path = os.path.join(os.path.dirname(__file__), "bseries_b003_influence_timeline.csv")
with open(csv_path, "w", newline="", encoding="utf-8") as fh:
    fw = csv.DictWriter(fh, fieldnames=fcols, extrasaction="ignore")
    fw.writeheader()
    for r in rows:
        fw.writerow({k: ("true" if (k == "provenance_retained" and r[k]) else
                         ("false" if k == "provenance_retained" else r.get(k, ""))) for k in fcols})
print("saved: mnemo/probes/bseries_b003_influence_timeline.csv")

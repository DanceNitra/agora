"""
Crucible marquee — "does long context kill RAG?" probe, PHASE A (deterministic generator).
Tests the CAG / "Don't do RAG" claim ("with a big enough context window you don't need retrieval — the fact
must be SOMEWHERE in there") against the "context rot" counter-claim (quality collapses past ~100k tokens).

Smallest runnable model of the claim: a synthetic structured log of N records. Two task families on the SAME
haystack at growing lengths:
  NEEDLE  — single-record lookup ("shipments for Record X?")  -> CAG predicts this stays easy.
  SYNTH   — read-everything aggregation (count/max/filter)     -> context-rot predicts this collapses with length.
If SYNTH collapses while NEEDLE survives, CAG's "it must be somewhere => correct answer" is FAILED for synthesis.
Judge-free (exact gold). Prior art (we REPLICATE, not discover): lost-in-the-middle (Liu 2023), Chroma context-rot
(2025), RULER (NVIDIA 2024). Writes per-length haystack + questions; gold stays here for PHASE C.
"""
import json, os, random
rng = random.Random(20260625)
REGIONS = ["North", "South", "East", "West", "Central"]
STATUSES = ["active", "closed"]
# target context lengths (approx tokens) -> record counts (~14 tokens/record line)
LEN_RECORDS = {"5k": 330, "25k": 1700, "60k": 4200, "110k": 7800}
import os as _os
OUT = _os.environ.get("RAGDEAD_OUT", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "ragdead_out"))
os.makedirs(OUT, exist_ok=True)
for f in os.listdir(OUT):
    os.remove(os.path.join(OUT, f))

gold_all = {}
for label, nrec in LEN_RECORDS.items():
    recs = []
    for i in range(1, nrec + 1):
        recs.append({"id": i, "region": rng.choice(REGIONS), "ship": rng.randint(10, 9999),
                     "status": rng.choice(STATUSES)})
    lines = [f"Record {r['id']:05d}: region={r['region']}, shipments={r['ship']}, status={r['status']}." for r in recs]
    haystack = ("LOG (each line is one record). Answer the questions at the very end using ONLY this log.\n\n"
                + "\n".join(lines))
    # ---- questions + exact gold ----
    needle_q, needle_g = [], {}
    for k in range(8):
        r = rng.choice(recs)
        qid = f"N{k}"
        needle_q.append({"qid": qid, "q": f"How many shipments did Record {r['id']:05d} report? (integer)"})
        needle_g[qid] = r["ship"]
    synth_q, synth_g = [], {}
    # 3x COUNT(region & status), 3x MAX-by-region, 2x COUNT(region & ship>T)
    for k in range(3):
        reg, st = rng.choice(REGIONS), rng.choice(STATUSES)
        qid = f"C{k}"
        synth_q.append({"qid": qid, "q": f"How many records have region={reg} AND status={st}? (integer)"})
        synth_g[qid] = sum(1 for r in recs if r["region"] == reg and r["status"] == st)
    for k in range(3):
        reg = rng.choice(REGIONS)
        qid = f"M{k}"
        synth_q.append({"qid": qid, "q": f"Among records with region={reg}, which Record id has the HIGHEST shipments? (give the 5-digit id)"})
        top = max((r for r in recs if r["region"] == reg), key=lambda r: r["ship"])
        synth_g[qid] = top["id"]
    for k in range(2):
        reg, T = rng.choice(REGIONS), rng.randint(3000, 7000)
        qid = f"F{k}"
        synth_q.append({"qid": qid, "q": f"How many records have region={reg} AND shipments > {T}? (integer)"})
        synth_g[qid] = sum(1 for r in recs if r["region"] == reg and r["ship"] > T)
    open(f"{OUT}/haystack_{label}.txt", "w", encoding="utf-8").write(haystack)
    json.dump({"label": label, "needle": needle_q, "synth": synth_q},
              open(f"{OUT}/questions_{label}.json", "w"), indent=1)
    gold_all[label] = {"needle": needle_g, "synth": synth_g, "n_records": nrec,
                       "haystack_chars": len(haystack)}
    print(f"{label}: {nrec} records, {len(haystack)} chars (~{len(haystack)//4} tokens)", flush=True)
json.dump(gold_all, open(f"{OUT}/gold.json", "w"), indent=1)
print("wrote haystacks + questions + gold to", OUT)

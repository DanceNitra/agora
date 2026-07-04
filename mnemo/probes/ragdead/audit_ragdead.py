"""
ADVERSARIAL AUDIT of the published RAG-dead claim (independent re-derivation, multi-angle).
Checks, from scratch:
 1. GOLD CORRECTNESS — re-parse each haystack from disk and re-derive the needle+synth answers INDEPENDENTLY
    (not trusting gold.json), confirm they match gold.json. (catches a gold bug)
 2. SCORING CORRECTNESS — recompute needle/synth accuracy from the agent answers vs the re-derived gold.
 3. GREP-CHEAT CHECK — show, per length, the agent's SYNTH answers vs gold. If the agent had grepped/scripted,
    synth would be ~exact (≈100%). If synth answers are WRONG by varying amounts, that's genuine model failure
    (the collapse is real, not a tooling artifact). Print the actual numbers so we can eyeball it.
 4. NEEDLE SANITY — confirm needle answers are exact (lookup genuinely works).
Cloud-free, deterministic, no agents.
"""
import json, re, os
import os as _os
OUT = _os.environ.get("RAGDEAD_OUT", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "ragdead_out"))
LENGTHS = ["5k", "25k", "60k", "110k"]
gold = json.load(open(f"{OUT}/gold.json"))


def parse_haystack(label):
    """Re-parse the records from the haystack file on disk (independent of gold.json)."""
    txt = open(f"{OUT}/haystack_{label}.txt", encoding="utf-8").read()
    recs = {}
    for m in re.finditer(r"Record (\d{5}): region=(\w+), shipments=(\d+), status=(\w+)\.", txt):
        rid = int(m.group(1)); recs[rid] = {"region": m.group(2), "ship": int(m.group(3)), "status": m.group(4)}
    return recs


def rederive(label, recs):
    """Re-derive answers for this length's questions, straight from the parsed records."""
    q = json.load(open(f"{OUT}/questions_{label}.json"))
    g = {}
    for item in q["needle"]:
        m = re.search(r"Record (\d{5})", item["q"]); rid = int(m.group(1))
        g[item["qid"]] = recs[rid]["ship"]
    for item in q["synth"]:
        qt = item["q"]
        if "highest shipments" in qt.lower():
            reg = re.search(r"region=(\w+)", qt).group(1)
            g[item["qid"]] = max((r for r in recs if recs[r]["region"] == reg), key=lambda r: recs[r]["ship"])
        elif "shipments >" in qt:
            reg = re.search(r"region=(\w+)", qt).group(1); T = int(re.search(r"> (\d+)", qt).group(1))
            g[item["qid"]] = sum(1 for r in recs.values() if r["region"] == reg and r["ship"] > T)
        else:  # count region & status
            reg = re.search(r"region=(\w+)", qt).group(1); st = re.search(r"status=(\w+)", qt).group(1)
            g[item["qid"]] = sum(1 for r in recs.values() if r["region"] == reg and r["status"] == st)
    return g


def norm(v):
    if isinstance(v, (int, float)): return int(v)
    m = re.search(r"-?\d+", str(v).replace(",", "")); return int(m.group(0)) if m else None


print("=== AUDIT: RAG-dead ===")
for L in LENGTHS:
    recs = parse_haystack(L)
    mine = rederive(L, recs)                       # my independent gold
    gj = {**gold[L]["needle"], **gold[L]["synth"]}  # published gold
    # 1+2: does my independent gold match the published gold?
    gold_mismatch = [k for k in gj if norm(mine.get(k)) != norm(gj.get(k))]
    ans = json.load(open(f"{OUT}/answers_{L}.json"))
    nq = list(gold[L]["needle"]); sq = list(gold[L]["synth"])
    n_acc = sum(norm(ans.get(k)) == norm(mine[k]) for k in nq) / len(nq)
    s_acc = sum(norm(ans.get(k)) == norm(mine[k]) for k in sq) / len(sq)
    # 3: synth answers vs gold (eyeball grep-cheat: are wrongs genuinely off?)
    synth_detail = [(k, norm(ans.get(k)), mine[k]) for k in sq]
    print(f"\n[{L}] records parsed={len(recs)} | gold-vs-published mismatches={len(gold_mismatch)} "
          f"| needle_acc={n_acc:.2f} synth_acc={s_acc:.3f}")
    print("   synth (qid, agent_answer, true_gold):")
    for k, a, t in synth_detail:
        flag = "OK" if a == t else "WRONG"
        print(f"     {k}: agent={a} gold={t}  [{flag}]")

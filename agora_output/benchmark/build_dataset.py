"""RAMR point-2 hardening: FREEZE a versioned dataset to disk (kills the 'dataset regenerated each run' attack).
Generates the contamination-resistant synthetic items ONCE with fixed seeds and writes them as inspectable JSONL +
a manifest (version, seeds, counts, schema, content hash). After this, runs LOAD the frozen file instead of
regenerating -> reproducible, citable, diffable. Pure-synthetic, no LLM/GPU needed -> instant. ASCII prints.

Families frozen here (the LLM-reader metrics that share the 3-hop chain generator):
  chains  : N 3-hop chains for CONVERSION / CHAIN-FRAGILITY / DISTRACTION (gold facts, answer, a fixed dropped-hop
            index for partial, and a fixed distractor pool per item so noisy conditions are reproducible too).
The memory-side families (FACT-RETENTION, OUTCOME-RANKED-RECALL) have their own deterministic generators in their
scripts (fixed seeds already); they are referenced in the manifest but not re-serialized here."""
import os, sys, json, hashlib
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ramr_v0_conversion as v0

VERSION = "0.1.0"
N_CHAINS = int(os.getenv("RAMR_N", "300"))
SEED = 20260623
DIST_PER_ITEM = 60        # fixed distractor pool per item (subsample first k for any distraction level)
OUTDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def build_chains():
    r = np.random.default_rng(SEED)
    items = []
    for i in range(N_CHAINS):
        ch = v0.gen_chain(r)
        dpool = v0.distractors(r, DIST_PER_ITEM)
        items.append({
            "id": f"chain-{i:04d}",
            "question": ch["q"],
            "gold_facts": ch["facts"],          # the complete chain (CONVERSION uses all)
            "answer": ch["answer"],
            "drop_index": int(r.integers(len(ch["facts"]))),   # fixed hop to drop for PARTIAL (deterministic)
            "distractor_pool": dpool,           # fixed irrelevant facts for DISTRACTION (take first k)
        })
    return items


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    items = build_chains()
    path = os.path.join(OUTDIR, f"ramr_chains_v{VERSION}.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=True) + "\n")
    # content hash over the canonical serialization -> any change to the dataset changes the manifest
    h = hashlib.sha256()
    for it in items:
        h.update(json.dumps(it, sort_keys=True, ensure_ascii=True).encode())
    manifest = {
        "name": "RAMR", "version": VERSION,
        "description": "Retrieval-Augmented Memory Reliability -- contamination-resistant synthetic benchmark.",
        "generator_seed": SEED, "hops": v0.HOPS,
        "files": {os.path.basename(path): {"n": len(items), "sha256": h.hexdigest()}},
        "schema": {"id": "str", "question": "str", "gold_facts": "list[str] (complete chain)",
                   "answer": "str", "drop_index": "int (hop dropped for PARTIAL)",
                   "distractor_pool": f"list[str] (len {DIST_PER_ITEM}, take first k for DISTRACTION)"},
        "metrics": ["CONVERSION (gold acc)", "CHAIN-FRAGILITY (gold-partial)", "DISTRACTION (gold-noisy)"],
        "contamination_note": "entities are random synthetic tokens -> closed-book accuracy ~0 (uncontaminated).",
        "memory_families_external": {
            "FACT-RETENTION": "ramr_factret.py (deterministic gen_facts seeds)",
            "OUTCOME-RANKED-RECALL": "ramr_outcome_ranked.py (embed-once fixed pool, seed 99)"},
    }
    mpath = os.path.join(OUTDIR, "manifest.json")
    json.dump(manifest, open(mpath, "w"), indent=2)
    print(f"FROZEN RAMR v{VERSION}", flush=True)
    print(f"  {path}", flush=True)
    print(f"    {len(items)} chains, sha256 {manifest['files'][os.path.basename(path)]['sha256'][:16]}...", flush=True)
    print(f"  {mpath}", flush=True)
    print(f"  sample item: {json.dumps(items[0])[:160]}...", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()

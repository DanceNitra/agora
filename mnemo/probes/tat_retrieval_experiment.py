"""
tat_retrieval_experiment.py  --  the exact joint experiment for @maratsultanov2 (DeepSeek-V3 #1466). MIT.

Question: does adding a TAT 5-D chunk (Theme, Role, Emotion, Meaning, Goal) to mnemo's recall -- as a HARD
`where=` filter or a SOFT `prefer=` weight -- measurably beat plain semantic recall on a retrieval task?

This file is the harness, validated END-TO-END on synthetic B-trace-like data so the input spec is proven
consumable BEFORE any real run. Point it at real data with --records/--queries (JSONL) to get the real number.

INPUT SPEC (what to send):
  records.jsonl : one per line  {"id": "...", "text": "<text that gets embedded/recalled>",
                                 "chunk": {"theme": "...","role":"...","emotion":"...","meaning":"...","goal":"..."},
                                 "t": <order-or-timestamp, optional>}
  queries.jsonl : one per line  {"query": "<query text>",
                                 "chunk": {"theme":"...", ...},   # the QUERY's own 5-D context (used by arms B/C;
                                                                  #   query-side info, no answer leakage)
                                 "relevant_ids": ["id1","id2", ...]}   # ground-truth correct records

THREE ARMS (same base retrieval, fair):
  A plain  : recall(query, k)
  B filter : recall(query, k, where={theme: query.chunk.theme})        # HARD single-dim filter
  C prefer : recall(query, k, prefer=[{cond:{dim:val},trust} for all 5 dims], ...)   # SOFT product weight
Metrics: recall@k and MRR against relevant_ids. Honest: on the SYNTHETIC set the 5-D signal is injected, so
B/C SHOULD win -- that only validates the pipeline detects signal WHEN PRESENT; the real question is whether
Marat's real B-traces carry that signal. Win or lose, reported straight.

Run:  python tat_retrieval_experiment.py                 # synthetic validation
      python tat_retrieval_experiment.py --records r.jsonl --queries q.jsonl   # real data
"""
import os, sys, json, argparse, random
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "mnemo")))
from mnemo import Mnemo

DIMS = ("theme", "role", "emotion", "meaning", "goal")


def _store():
    import tempfile
    fd, p = tempfile.mkstemp(suffix=".json"); os.close(fd); os.remove(p)
    try:
        return Mnemo(path=p)
    except TypeError:
        return Mnemo()


def load(m, records):
    id_map = {}
    for r in records:
        chunk = {d: (r.get("chunk") or {}).get(d) for d in DIMS}
        mid = m.remember(r["text"], meta=chunk)
        id_map[r["id"]] = mid          # map external id -> internal mnemo id
    return id_map


def _ids(hits):
    return [h["id"] for h in hits]


def evaluate(m, queries, id_map, k=10):
    def recall_at_k(hit_ids, rel):
        rel_internal = {id_map[x] for x in rel if x in id_map}
        if not rel_internal:
            return None
        return len(set(hit_ids[:k]) & rel_internal) / len(rel_internal)

    def mrr(hit_ids, rel):
        rel_internal = {id_map[x] for x in rel if x in id_map}
        for i, h in enumerate(hit_ids):
            if h in rel_internal:
                return 1.0 / (i + 1)
        return 0.0

    arms = {"A_plain": [], "B_where": [], "C_prefer": []}
    mrrs = {"A_plain": [], "B_where": [], "C_prefer": []}
    for q in queries:
        rel = q.get("relevant_ids", [])
        qc = q.get("chunk") or {}
        # A: plain
        a = _ids(m.recall(q["query"], k=k))
        # B: hard where on the single most-carrying dim available (theme, else first present)
        wdim = next((d for d in ("theme", "role", "goal", "meaning", "emotion") if qc.get(d)), None)
        b = _ids(m.recall(q["query"], k=k, where={wdim: qc[wdim]})) if wdim else a
        # C: soft prefer over all present dims (product composition)
        prefer = [{"cond": {d: qc[d]}, "trust": 0.7} for d in DIMS if qc.get(d)]
        c = _ids(m.recall(q["query"], k=k, prefer=prefer)) if prefer else a
        for name, hits in (("A_plain", a), ("B_where", b), ("C_prefer", c)):
            r = recall_at_k(hits, rel)
            if r is not None:
                arms[name].append(r); mrrs[name].append(mrr(hits, rel))
    return arms, mrrs


def synth(n_topics=12, per_topic=8, distractors_per_topic=6, seed=7):
    """B-trace-like: each topic has records sharing a chunk; DISTRACTORS are lexically similar but a DIFFERENT
    chunk -- so plain recall is confusable and the 5-D cue can disambiguate (the realistic case)."""
    rng = random.Random(seed)
    themes = ["identity", "capability", "style", "safety", "planning", "memory"]
    vocab = [f"w{i}" for i in range(40)]
    records, queries = [], []
    rid = 0
    for tp in range(n_topics):
        theme = themes[tp % len(themes)]
        chunk = {"theme": theme, "role": rng.choice(["user", "assistant", "system"]),
                 "emotion": rng.choice(["steady", "neutral", "tense"]),
                 "meaning": f"m{tp}", "goal": f"g{tp}"}
        topic_words = rng.sample(vocab, 6)
        rel = []
        for _ in range(per_topic):
            txt = " ".join(rng.sample(topic_words, 4) + rng.sample(vocab, 2))
            records.append({"id": f"r{rid}", "text": txt, "chunk": dict(chunk)}); rel.append(f"r{rid}"); rid += 1
        # distractors: same words, DIFFERENT chunk (a different topic's structure)
        for _ in range(distractors_per_topic):
            dtheme = rng.choice([t for t in themes if t != theme])
            txt = " ".join(rng.sample(topic_words, 4) + rng.sample(vocab, 2))
            records.append({"id": f"r{rid}", "text": txt,
                            "chunk": {"theme": dtheme, "role": rng.choice(["user", "assistant"]),
                                      "emotion": "neutral", "meaning": f"m{100+rid}", "goal": f"g{100+rid}"}}); rid += 1
        qtext = " ".join(rng.sample(topic_words, 5))
        queries.append({"query": qtext, "chunk": dict(chunk), "relevant_ids": rel})
    return records, queries


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--records"); ap.add_argument("--queries"); ap.add_argument("-k", type=int, default=10)
    a = ap.parse_args()
    if a.records and a.queries:
        records = [json.loads(l) for l in open(a.records, encoding="utf-8") if l.strip()]
        queries = [json.loads(l) for l in open(a.queries, encoding="utf-8") if l.strip()]
        src = f"REAL data ({len(records)} records, {len(queries)} queries)"
    else:
        records, queries = synth()
        src = f"SYNTHETIC validation ({len(records)} records, {len(queries)} queries; 5-D signal injected)"
    m = _store()
    id_map = load(m, records)
    arms, mrrs = evaluate(m, queries, id_map, k=a.k)
    print(f"=== TAT 5-D retrieval experiment -- {src} ===")
    print(f"arm         recall@{a.k}    MRR      (n_queries scored = {len(arms['A_plain'])})")
    for name in ("A_plain", "B_where", "C_prefer"):
        r = arms[name]; mr = mrrs[name]
        if r:
            print(f"{name:11} {sum(r)/len(r):.3f}       {sum(mr)/len(mr):.3f}")
    base = sum(arms["A_plain"]) / len(arms["A_plain"]) if arms["A_plain"] else 0
    for name in ("B_where", "C_prefer"):
        if arms[name]:
            d = sum(arms[name]) / len(arms[name]) - base
            print(f"  {name} vs plain: {'+' if d>=0 else ''}{d:.3f} recall@{a.k}")
    if not (a.records and a.queries):
        print("\nVALIDATION NOTE: synthetic 5-D signal is injected, so B/C beating A only proves the harness")
        print("detects the cue WHEN present. The real question is whether Marat's B-traces carry it -- same")
        print("harness, real numbers, reported win-or-lose. Send records.jsonl + queries.jsonl in the spec above.")


if __name__ == "__main__":
    main()

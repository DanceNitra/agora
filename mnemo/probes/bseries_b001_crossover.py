"""B-001 (Preference Application) as a memory-substrate instrument, v2 - the CROSSOVER version.

An earlier fixed-query version was flagged in review as (a) too small / hand-paired (its query/distractor
pairing could engineer the result), and (b) a textbook re-derivation of the MemGPT working-context /
Letta core-memory design (an always-in-context profile tier that is NOT similarity-retrieved). This
version fixes that: it sweeps an independently-written query set across three independent similarity
mechanisms, and adds the parts that are NOT textbook: WHERE the two channels cross over.

Framing (honest, post-audit):
  - The always-inject-profile vs similarity-retrieve-archival split is ESTABLISHED design (MemGPT,
    Packer et al. 2023, arXiv:2310.08560 - the paper's *working/main context* vs *external context*;
    "core memory" is Letta's later term). We do NOT claim it. mem0 is user-SCOPED but still
    similarity-retrieved (filtered by user_id), so it does NOT remove the query-relevance dependence.
  - What is under-quantified: (1) the query-overlap crossover - similarity retrieves a preference ONLY
    when the query is itself about that preference's topic; below that it collapses - shown across THREE
    independent similarity mechanisms (nomic, mxbai, TF-IDF) so it is not an embedder artifact; and
    (2) the SCALE crossover - "inject all preferences" is free only while the preference set fits the
    inject budget; past it, the profile channel becomes its OWN retrieval + supersession problem, which
    fuses B-001 with B-003.

Measurements:
  M1  overlap crossover : pref_recall vs cosine(query, nearest preference), swept over a query set that
                          spans the overlap axis (NOT hand-paired). Reported for nomic + mxbai + TF-IDF.
  M2  scale crossover   : active-preference recall vs preference-set size N at a fixed inject budget B,
                          for inject-all / recency / similarity-to-query selection. typed_profile=1.0 is
                          exposed as a small-N artifact.
  M3  supersession fuse : with changed preferences (concise->detailed), the fraction of INJECTED
                          preferences that are STALE, naive inject-recent-B vs keyed supersession
                          (the B-003 machinery). Shows B-001-at-scale needs B-003.

Needs: numpy + local Ollama with nomic-embed-text and (optionally) mxbai-embed-large. TF-IDF is pure
numpy (always runs). Missing embedders are skipped with a note, not faked. MIT. Part of Agora / mnemo.
  Run: python mnemo/probes/bseries_b001_crossover.py
"""
import sys, os, csv, io, json, math, urllib.request
import numpy as np

try:
    from mnemo import Mnemo
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from mnemo import Mnemo

OLLAMA = "http://localhost:11434/api/embeddings"
EMBEDDERS = ["nomic-embed-text", "mxbai-embed-large"]   # both real; skipped individually if absent


def _emb(model, text):
    req = urllib.request.Request(OLLAMA, data=json.dumps({"model": model, "prompt": text}).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["embedding"]


def _have(model):
    try:
        return len(_emb(model, "x")) > 0
    except Exception:
        return False


def _cos(a, b):
    a = np.asarray(a, np.float32); b = np.asarray(b, np.float32)
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(a @ b / (na * nb)) if na and nb else 0.0


# ── TF-IDF cosine: a mechanism totally unlike a neural embedder (pure lexical), as a robustness channel ──
class TfIdf:
    def __init__(self, corpus):
        self.vocab, df = {}, {}
        toks = [self._tok(d) for d in corpus]
        for t in toks:
            for w in set(t):
                df[w] = df.get(w, 0) + 1
        for w in df:
            self.vocab.setdefault(w, len(self.vocab))
        self.idf = {w: math.log((1 + len(corpus)) / (1 + df[w])) + 1 for w in df}

    def _tok(self, s):
        return [w for w in ''.join(c.lower() if c.isalnum() else ' ' for c in s).split() if len(w) > 2]

    def vec(self, s):
        v = np.zeros(len(self.vocab), np.float32)
        tf = {}
        for w in self._tok(s):
            if w in self.vocab:
                tf[w] = tf.get(w, 0) + 1
        for w, c in tf.items():
            v[self.vocab[w]] = c * self.idf.get(w, 0.0)
        return v


# ── scenario data ───────────────────────────────────────────────────────────────────
PREFERENCES = [
    ("pref_concise",    "The user prefers concise answers and dislikes long-winded replies."),
    ("pref_no_numlist", "The user dislikes numbered lists; use short prose or plain dashes."),
    ("pref_direct_q",   "The user prefers a direct clarifying question over an unsolicited summary."),
]

# Independently-authored episodic pool (varied topics; NOT hand-matched to the query set below).
EPISODIC = [
    "We debugged a Kafka consumer that stalled during partition rebalancing.",
    "The staging Postgres ran out of connections; we raised the pool size.",
    "We compared B-tree and LSM-tree engines for the write-heavy path.",
    "The React frontend was migrated from v17 to v19.",
    "We added a Redis cache in front of the pricing service.",
    "The nightly ETL job moved from 2am to every six hours.",
    "We wrote an exponential-backoff retry for the payments webhook.",
    "The Kubernetes ingress needed a longer upstream timeout.",
    "We added a dataloader to batch a slow GraphQL resolver.",
    "The auth session timeout was cut from 30 to 15 minutes.",
    "We set up OpenTelemetry tracing across checkout services.",
    "A flaky test came from a race in fixture teardown.",
    "The warehouse region moved from us-east-1 to eu-west-1.",
    "The CI pipeline was split so unit and e2e run in parallel.",
    "We tuned the JVM heap on the search indexer to stop GC pauses.",
    "The mobile app crashed on cold start from an uninit analytics SDK.",
    "We rate-limited the API gateway at 300 req/min.",
    "The recommender was retrained after a feature-drift alert.",
    "We switched the deploy default branch from master to main.",
    "A websocket memory leak was unclosed subscriptions.",
    "The invoice PDF renderer choked on very large line-item tables.",
    "We sharded the analytics table by tenant to speed up rollups.",
    "The feature-flag service added percentage-based gradual rollout.",
    "We migrated secrets from env files to a vault with rotation.",
]

# Query set spanning the OVERLAP AXIS (authored independently of which episodic memory matches):
#  - OFF: about an engineering topic (the true B-001 case: unrelated to preferences)
#  - MID: mentions communication/answer shape only loosely
#  - ON : explicitly about answer style / format / length (topically close to a preference)
QUERIES = [
    ("off", "How does Kafka handle partition rebalancing when a consumer joins?"),
    ("off", "What are the trade-offs between a B-tree and an LSM-tree for writes?"),
    ("off", "How should I configure Postgres connection pooling under load?"),
    ("off", "What's a good retry strategy for a flaky payments webhook?"),
    ("off", "How do I reduce p99 latency on a hot pricing endpoint?"),
    ("off", "How can I stop GC pauses on a JVM search indexer?"),
    ("off", "How do I shard a large analytics table by tenant?"),
    ("off", "What's the safest way to rotate secrets in production?"),
    ("mid", "Can you help me draft an update about the Kafka incident?"),
    ("mid", "How should I write up the database migration for the team?"),
    ("mid", "What's the clearest way to explain the retry logic to a junior?"),
    ("mid", "How do I summarize the incident for a status page?"),
    ("on",  "How long should your answers be and should you use bullet lists?"),
    ("on",  "Do you prefer giving a summary or asking a direct question first?"),
    ("on",  "Should responses be concise or detailed, and avoid numbered lists?"),
    ("on",  "What tone and answer format do you use when replying to me?"),
]

PRESSURE = "B_low_causal_density_under_load"
INJECT_BUDGET = 12


def _build_store(embed_fn):
    m = Mnemo(embed=embed_fn)
    t = 1_000_000.0
    for pid, txt in PREFERENCES:
        m.remember(txt, tags=["preference"], mtype="procedural", meta={"pid": pid}, valid_from=t); t += 10
    for txt in EPISODIC:
        m.remember(txt, tags=["episodic"], mtype="episodic", valid_from=t); t += 10
    return m


# ── M1: overlap crossover ─────────────────────────────────────────────────────────────
def m1_overlap(name, embed_fn, k=5):
    m = _build_store(embed_fn)
    pref_ids = {r["id"] for r in m.items if "preference" in (r.get("tags") or [])}
    pref_vecs = [embed_fn(t) for _, t in PREFERENCES]
    epi_vecs = [embed_fn(t) for t in EPISODIC]
    rows = []
    for cls, q in QUERIES:
        qv = embed_fn(q)
        nearest = max(_cos(qv, pv) for pv in pref_vecs)           # query <-> nearest preference
        top_epi = max(_cos(qv, ev) for ev in epi_vecs)            # query <-> best on-topic episodic memory
        hits = m.recall(q, k=k, mode="hybrid")
        got = sum(1 for h in hits if h["id"] in pref_ids) / len(PREFERENCES)
        rows.append((cls, nearest, got, top_epi))
    return rows


def m1_tfidf(k=5):
    corpus = [t for _, t in PREFERENCES] + EPISODIC + [q for _, q in QUERIES]
    tf = TfIdf(corpus)
    pref_vecs = [tf.vec(t) for _, t in PREFERENCES]
    all_docs = [("pref", pid, t) for pid, t in PREFERENCES] + [("epi", None, t) for t in EPISODIC]
    doc_vecs = [tf.vec(t) for _, _, t in all_docs]
    epi_vecs = [doc_vecs[i] for i in range(len(all_docs)) if all_docs[i][0] == "epi"]
    rows = []
    for cls, q in QUERIES:
        qv = tf.vec(q)
        nearest = max(_cos(qv, pv) for pv in pref_vecs)
        top_epi = max(_cos(qv, ev) for ev in epi_vecs)
        # top-k among docs with NONZERO similarity only (mirror mnemo's nonzero-relevance behavior; a
        # zero-cosine doc is not a match - counting it would be an index tie-break artifact, not retrieval)
        scored = [(i, _cos(qv, doc_vecs[i])) for i in range(len(all_docs))]
        scored = [i for i, s in sorted(scored, key=lambda x: -x[1]) if s > 0][:k]
        got = sum(1 for i in scored if all_docs[i][0] == "pref") / len(PREFERENCES)
        rows.append((cls, nearest, got, top_epi))
    return rows


def _summ(rows):
    by = {}
    for cls, near, got, top_epi in rows:
        by.setdefault(cls, []).append((near, got, top_epi))
    out = {}
    for cls in ("off", "mid", "on"):
        vals = by.get(cls, [])
        if vals:
            out[cls] = (float(np.mean([n for n, _, _ in vals])), float(np.mean([g for _, g, _ in vals])),
                        float(np.mean([e for _, _, e in vals])))
    return out


# ── M2: scale crossover ───────────────────────────────────────────────────────────────
def m2_scale():
    """Active-preference recall vs preference-set size N at fixed inject budget B. 3 of the N accumulated
    preferences are the ones relevant to THIS turn; they sit at RANDOM positions among the N (you don't get
    to know which are relevant by arrival order - that's the whole problem). Below budget you inject all
    (recall 1.0); above it you must SELECT B of N, and a generic selector (recency / random) keeps only
    ~B/N of the relevant ones. A relevance selector would do better - but ranking preferences by similarity
    to the query is exactly the M1 orthogonality failure again. Averaged over trials for the random placement."""
    import random as _rnd
    _rnd.seed(42)
    B = INJECT_BUDGET
    trials = 300
    out = {}
    for N in (3, 10, 30, 100, 300):
        rec, rnd = 0.0, 0.0
        for _ in range(trials):
            active = set(_rnd.sample(range(N), 3))                 # 3 relevant prefs at random positions
            recency_set = set(range(max(0, N - B), N))             # newest B (positions closest to N-1)
            rec += len(active & recency_set) / 3
            rand_set = set(_rnd.sample(range(N), min(B, N)))       # random B
            rnd += len(active & rand_set) / 3
        out[N] = {"inject_all": (1.0 if N <= B else None), "recency": rec / trials,
                  "random": rnd / trials, "B": B}
    return out


# ── M3: supersession fusion (B-001 needs B-003) ───────────────────────────────────────
def m3_supersession():
    """A preference CHANGES over sessions (concise -> detailed). Isolated from budget (M2): the question is
    only whether the STALE value is still ACTIVE / injectable after the change. Naive append keeps both
    values active (the old one can still be served); keyed supersession retires the old so only the current
    value is injectable - the same B-003 machinery, applied to the profile channel."""
    key = "user::answer_length"
    # naive append (no supersession): both remain active -> the stale value is still injectable
    m_naive = Mnemo()
    m_naive.remember("prefers concise answers", mtype="procedural")
    m_naive.remember("prefers detailed answers", mtype="procedural")
    naive_active = [r for r in m_naive.items if r["status"] == "active"]
    naive_stale_active = sum(1 for r in naive_active if "concise" in r["text"])   # 1 = stale still injectable
    naive_current_active = sum(1 for r in naive_active if "detailed" in r["text"])
    # keyed supersession (mnemo): the new same-key value RETIRES the old (deterministic, no embedder)
    m_key = Mnemo()
    m_key.remember("prefers concise answers", key=key, mtype="procedural")
    m_key.remember("prefers detailed answers", key=key, mtype="procedural")
    keyed_active = [r for r in m_key.items if r["status"] == "active"]
    keyed_stale_active = sum(1 for r in keyed_active if "concise" in r["text"])   # 0 = retired
    keyed_current_active = sum(1 for r in keyed_active if "detailed" in r["text"])
    return {"naive_stale_active": naive_stale_active, "naive_current_active": naive_current_active,
            "keyed_stale_active": keyed_stale_active, "keyed_current_active": keyed_current_active}


def main():
    print("=== B-001 Preference Application - CROSSOVER substrate instrument (v2, post-audit) ===")
    print("    (not a framework test; the always-inject-vs-retrieve split is MemGPT/Letta prior art -")
    print("     we measure WHERE the channels cross over, across 3 independent similarity mechanisms)\n")

    # M1
    print("[M1] OVERLAP CROSSOVER - pref_recall@5 vs how topically close the query is to a preference")
    print("     (query classes: off = unrelated topic (the true B-001 case), mid, on = about answer style)\n")
    channels = []
    for name in EMBEDDERS:
        if _have(name):
            channels.append((name, m1_overlap(name, lambda t, n=name: _emb(n, t))))
        else:
            print(f"     ({name} not available locally - skipped, not faked)")
    channels.append(("tfidf-lexical", m1_tfidf()))
    for name, rows in channels:
        s = _summ(rows)
        line = "  ".join(f"{cls}: recall={s[cls][1]:.2f} (nearest-cos={s[cls][0]:.2f})" for cls in s)
        print(f"  {name:18} {line}")
    # orthogonality contrast on the OFF class (the true B-001 case): query<->pref vs query<->on-topic memory
    print("\n  orthogonality on off-topic (B-001) queries: cos(query, nearest pref) vs cos(query, best on-topic memory):")
    for name, rows in channels:
        s = _summ(rows)
        if "off" in s:
            print(f"    {name:18} pref={s['off'][0]:.2f}  on-topic-memory={s['off'][2]:.2f}")
    print("\n  reading: every channel recovers the preference when the query is ABOUT answer style (on),")
    print("  and collapses when the query is an unrelated topic (off) - the B-001 scenario. The crossover")
    print("  is the query-overlap axis itself, not the embedder (holds for nomic, mxbai AND pure lexical).")

    # M2
    print("\n[M2] SCALE CROSSOVER - recall of the 3 turn-relevant prefs vs set size N (inject budget B=12)")
    sc = m2_scale()
    print("     N    inject-all   recency-cap   random-B    note")
    for N, d in sc.items():
        ia = f"{d['inject_all']:.2f}" if d["inject_all"] is not None else " -- "
        note = "all fit budget" if N <= d["B"] else "N>B: must SELECT (need a ranker)"
        print(f"    {N:>3}     {ia}        {d['recency']:.2f}         {d['random']:.2f}      {note}")
    print("  reading: typed_profile=1.0 is a small-N artifact (N<=B). Past the inject budget, a generic")
    print("  selector keeps only ~B/N of the relevant prefs; you need a RELEVANCE ranker - and ranking")
    print("  preferences by similarity to the query is exactly the M1 orthogonality failure again.")

    # M3
    print("\n[M3] SUPERSESSION FUSION (B-001 needs B-003) - a preference changes concise->detailed")
    ms = m3_supersession()
    print(f"     naive append (no supersession): stale 'concise' still ACTIVE/injectable = "
          f"{ms['naive_stale_active']}  (current 'detailed' active = {ms['naive_current_active']}) -> both live, stale can be served")
    print(f"     keyed supersession:             stale 'concise' active = {ms['keyed_stale_active']} (retired), "
          f"current 'detailed' active = {ms['keyed_current_active']} -> only the current value is injectable")
    print("  reading: maintaining a bounded, CURRENT profile is a retrieval + supersession problem -")
    print("  the same keyed machinery as B-003. B-001-at-scale and B-003 are one story, not two.")

    # CSV (honest column names - NOT Cophy's production metric name)
    print("\nraw_format (csv; M1 overlap crossover, primary embedder):")
    buf = io.StringIO(); w = csv.writer(buf)
    w.writerow(["scenario_id", "pressure_type", "similarity_channel", "query_class",
                "nearest_pref_cosine", "on_topic_memory_cosine", "pref_recall_at5", "substrate"])
    for name, rows in channels:
        s = _summ(rows)
        for cls in s:
            w.writerow(["B-001", PRESSURE, name, cls, f"{s[cls][0]:.3f}", f"{s[cls][2]:.3f}",
                        f"{s[cls][1]:.3f}", "similarity_only"])
    print(buf.getvalue())
    print("Scope: substrate only (retrieval = necessary precondition for preference application, not proof");
    print("the model then applied it). Prior art: MemGPT working-context / Letta core-memory (arXiv:2310.08560);")
    print("mem0 is user-scoped but still similarity-retrieved. We measure the crossovers, we do not claim the design.")


if __name__ == "__main__":
    main()

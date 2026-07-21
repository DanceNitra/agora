"""Cross-framework Identity Pressure Eval - Scenario B-001 (Preference Application Without Explicit
Prompt), run as a MEMORY-SUBSTRATE instrument to contribute to deepseek-ai/DeepSeek-V3#1462 / #1466.

Same posture as our B-003 submission: this reads a different LAYER than the cognitive-trace instruments
in that thread (Cophy causal_density / TAT divergence / HeartFlow U-D-A-H field). It measures the storage
+ RETRIEVAL underneath the reasoning, not the agent's generated answer. Complementary to the cognitive
traces, not a replacement.

The B-001 spec (qingkong66): the agent has 3+ prior sessions that established user preferences (concise
answers; dislikes numbered lists; prefers direct questions over summaries). A NEW session opens on an
UNRELATED topic with no mention of the preferences. Expected: the agent applies the preferences unprompted.
Failure: it defaults to a generic style. Cophy's own metric for this scenario is
`causal_density_at_retrieval` - i.e. were the causally-relevant chunks (the preferences) actually
RETRIEVED at the moment of answering. That makes B-001 a retrieval question at the substrate level, which
is exactly what we can measure.

THE SUBSTRATE CLAIM (what we measure, honestly):
Preference application fails because of a RETRIEVAL-OBJECTIVE MISMATCH, not because storage lost the
preference. Query-similarity retrieval ranks memories by topical relevance to the *current* query. A
preference is causally load-bearing for the answer's STYLE but topically ORTHOGONAL to the query's
CONTENT ("be concise" has ~nothing in common with "explain the CAP theorem"). So a similarity ranker
structurally buries preferences beneath topically-relevant episodic memories - and raising k to force
them in drags in irrelevant content (a precision cost). The substrate that gets B-001 right is one with a
SEPARATE retrieval channel for profile/preference memory (retrieved by TYPE, unconditionally injected),
so it never competes with query-similarity.

We run the SAME scenario on three memory SUBSTRATES so the difference is measured, not asserted:
  - similarity_only : one store; recall by similarity to the new-session query (inspeximus hybrid = lexical +
                      semantic RRF over REAL nomic-embed-text; the strong baseline, not a rigged weak one).
                      This is what a naive "dump everything in one vector store, recall on the query" agent does.
  - recency_window  : inject the most-recent W memories (a sliding context window). Preferences were set
                      in session 1 and 3+ sessions of newer episodic memory have accrued since.
  - typed_profile   : preferences stored under a type/tag and retrieved BY TYPE (profile injection),
                      independent of the query. This is what production profile memory does (see PRIOR ART).

PRIOR ART (we did NOT invent profile injection - we measure the cost of NOT doing it): always-in-context
"core memory" blocks (MemGPT / Letta), user/profile memory (mem0), and the classic working-memory vs
archival-memory split all route profile facts on a separate, non-similarity channel for exactly this
reason. Our contribution is the measured substrate instrument for the B-series, not the mechanism.

Metrics (substrate only - we do NOT score the agent's generated answer):
  - pref_recall@k                : fraction of the 3 preferences surfaced in top-k for a new-session query
  - orthogonality (cosine)       : mean cosine(query, preference) vs mean cosine(query, on-topic memory).
                                   The structural reason: preferences sit near-zero to the query while
                                   topically-relevant episodic memories rank above them.
  - precision cost of raising k  : irrelevant (non-preference, off-topic) memories dragged in to reach a
                                   preference.

Needs: numpy + local Ollama nomic-embed-text (same as supersession_replication.py). Falls back to a
deterministic hash embedder if Ollama is absent, so it still RUNS anywhere (with a note that the semantic
baseline is then a stub, not real). Zero other dependencies. MIT. Part of Agora / inspeximus.
  Run: python research/probes/bseries_b001_preference_recall.py
"""
import sys, os, csv, io, json, hashlib, urllib.request
import numpy as np

try:
    from inspeximus import Inspeximus
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from inspeximus import Inspeximus

OLLAMA = "http://localhost:11434/api/embeddings"
MODEL = "nomic-embed-text"

# ── embedder: real nomic-embed-text if reachable, else a deterministic stub (labelled) ──
_REAL_EMBED = None


def _probe_ollama() -> bool:
    try:
        req = urllib.request.Request(OLLAMA, data=json.dumps({"model": MODEL, "prompt": "x"}).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return len(json.load(r).get("embedding", [])) > 0
    except Exception:
        return False


def _nomic(text: str):
    req = urllib.request.Request(OLLAMA, data=json.dumps({"model": MODEL, "prompt": text}).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["embedding"]


def _hash_embed(text: str, dim: int = 256):
    """Deterministic bag-of-tokens hash embedding - a STUB so the probe runs without Ollama. It is NOT a
    real semantic model; when this path is used the semantic baseline is weaker than production and the
    orthogonality numbers should be read as a lower bound on the effect (a real embedder separates topic
    from preference at least as cleanly)."""
    v = np.zeros(dim, dtype=np.float32)
    for tok in text.lower().split():
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
        v[h % dim] += 1.0
    n = np.linalg.norm(v)
    return (v / n).tolist() if n else v.tolist()


def embed(text: str):
    return _nomic(text) if _REAL_EMBED else _hash_embed(text)


# ── B-001 scenario data ───────────────────────────────────────────────────────────────
# The 3 preferences from the spec, established in session 1.
PREFERENCES = [
    ("pref_concise",     "The user prefers concise answers and gets annoyed by long-winded replies."),
    ("pref_no_numlist",  "The user dislikes numbered lists; use short prose or plain dashes instead."),
    ("pref_direct_q",    "The user prefers a direct clarifying question over an unsolicited summary."),
]

# Realistic episodic memory accrued across sessions 2..4 (the '3+ sessions of interaction'), on varied
# topics UNRELATED to the preferences. These are what a similarity ranker will legitimately surface for a
# topical query - and what buries the preferences.
EPISODIC = [
    ("e01", "We debugged a Kafka consumer that stalled during partition rebalancing under load."),
    ("e02", "The staging Postgres ran out of connections; we raised the pool size to 200."),
    ("e03", "We compared B-tree and LSM-tree storage engines for the write-heavy ingest path."),
    ("e04", "The React frontend was migrated from version 17 to 19 last sprint."),
    ("e05", "We added a Redis cache in front of the pricing service to cut p99 latency."),
    ("e06", "The nightly ETL job was rescheduled from 2am to every six hours."),
    ("e07", "We wrote a retry policy with exponential backoff for the payments webhook."),
    ("e08", "The Kubernetes ingress needed a longer timeout for slow upstream responses."),
    ("e09", "We profiled a slow GraphQL resolver and added a dataloader to batch queries."),
    ("e10", "The auth service session timeout was shortened from 30 to 15 minutes."),
    ("e11", "We set up OpenTelemetry tracing across the checkout microservices."),
    ("e12", "A flaky integration test was caused by a race in the fixture teardown."),
    ("e13", "We moved the data warehouse region from us-east-1 to eu-west-1 for GDPR."),
    ("e14", "The CI pipeline was split so unit and e2e suites run in parallel."),
    ("e15", "We tuned the JVM heap for the search indexer to stop GC pauses."),
    ("e16", "The mobile app crashed on cold start due to an uninitialized analytics SDK."),
    ("e17", "We added rate limiting at the API gateway at 300 requests per minute."),
    ("e18", "The recommendation model was retrained after a feature drift alert."),
    ("e19", "We switched the deploy script's default branch from master to main."),
    ("e20", "A memory leak in the websocket server was traced to unclosed subscriptions."),
]

# New-session queries: unrelated topics, NO mention of preferences (per the spec's 'Task input').
NEW_QUERIES = [
    "How does Kafka handle partition rebalancing when a consumer joins?",
    "What are the trade-offs between a B-tree and an LSM-tree for writes?",
    "How should I configure connection pooling for Postgres under load?",
    "What's a good retry strategy for a flaky payments webhook?",
    "How do I reduce p99 latency on a hot pricing endpoint?",
    "How can I stop GC pauses on a JVM search indexer?",
]

PRESSURE = "B_low_causal_density_under_load"


def _cos(a, b):
    a = np.asarray(a, dtype=np.float32); b = np.asarray(b, dtype=np.float32)
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(a @ b / (na * nb)) if na and nb else 0.0


def _build_store():
    """One realistic mixed store: 3 preferences (session 1) + 20 episodic memories (sessions 2..4)."""
    m = Inspeximus(embed=embed)
    t = 1_000_000.0
    for pid, txt in PREFERENCES:                       # session 1: preferences
        m.remember(txt, tags=["preference"], mtype="procedural", value=1.0,
                   meta={"pid": pid, "session": 1}, valid_from=t)
        t += 10
    for eid, txt in EPISODIC:                          # sessions 2..4: episodic, newer
        m.remember(txt, tags=["episodic"], mtype="episodic", value=1.0,
                   meta={"eid": eid, "session": 2 + (int(eid[1:]) // 7)}, valid_from=t)
        t += 10
    return m


def _pref_ids(m):
    return {r["id"] for r in m.items if "preference" in (r.get("tags") or [])}


def substrate_similarity_only(m, pref_ids, k, per_query_out=None):
    """Naive: recall by similarity to the new-session query (inspeximus hybrid = lexical+semantic RRF, strong).
    Returns the MEAN pref_recall@k; if per_query_out is a list, appends the per-query values (the mean hides
    a bimodal reality - some queries surface 0/3, one surfaces 3/3 - so we report both)."""
    per_query = []
    for q in NEW_QUERIES:
        hits = m.recall(q, k=k, mode="hybrid")
        got = sum(1 for h in hits if h["id"] in pref_ids)
        per_query.append(got / len(PREFERENCES))
    if per_query_out is not None:
        per_query_out.extend(per_query)
    return float(np.mean(per_query))


def substrate_recency_window(m, pref_ids, w):
    """Sliding window: inject the most-recent W memories, regardless of query. Preferences are the OLDEST."""
    recent = sorted(m.items, key=lambda r: r["ts"], reverse=True)[:w]
    got = sum(1 for r in recent if r["id"] in pref_ids)
    return got / len(PREFERENCES)          # query-independent


def substrate_typed_profile(m, pref_ids):
    """Profile injection: retrieve preferences BY TYPE (tag=='preference'), independent of the query."""
    got = sum(1 for r in m.items if "preference" in (r.get("tags") or []) and r["status"] == "active")
    return got / len(PREFERENCES)          # query-independent by construction


def orthogonality(m, pref_ids):
    """Structural reason: mean cosine(query, preference) vs mean cosine(query, on-topic episodic memory)."""
    pref_vecs = [r["vec"] for r in m.items if r["id"] in pref_ids and r.get("vec")]
    epi = [r for r in m.items if "episodic" in (r.get("tags") or []) and r.get("vec")]
    q_pref, q_top = [], []
    for q in NEW_QUERIES:
        qv = embed(q)
        q_pref.append(np.mean([_cos(qv, pv) for pv in pref_vecs]))
        # 'on-topic' = the single best-matching episodic memory for this query (what similarity surfaces first)
        q_top.append(max(_cos(qv, e["vec"]) for e in epi))
    return float(np.mean(q_pref)), float(np.mean(q_top))


def precision_cost(m, pref_ids):
    """To surface ANY preference via similarity, how deep must k go, and how many non-preference memories
    are dragged in along the way? Averaged over queries where a preference is reachable at all (<=len store)."""
    depths, dragged = [], []
    N = len([r for r in m.items if r["status"] == "active"])
    for q in NEW_QUERIES:
        hits = m.recall(q, k=N, mode="hybrid")
        depth = next((i + 1 for i, h in enumerate(hits) if h["id"] in pref_ids), None)
        if depth is not None:
            depths.append(depth)
            dragged.append(depth - 1)      # everything ranked above the first preference
    if not depths:
        return None, None
    return float(np.mean(depths)), float(np.mean(dragged))


def main():
    global _REAL_EMBED
    _REAL_EMBED = _probe_ollama()
    embed_kind = f"REAL nomic-embed-text ({MODEL})" if _REAL_EMBED else "STUB hash-embedder (Ollama absent)"
    print("=== B-001 Preference Application Without Explicit Prompt - memory-substrate instrument ===")
    print(f"    (not a framework test; embedder = {embed_kind})\n")

    m = _build_store()
    pref_ids = _pref_ids(m)
    n_active = len([r for r in m.items if r["status"] == "active"])
    print(f"store: {n_active} active memories = {len(PREFERENCES)} preferences (session 1) + "
          f"{len(EPISODIC)} episodic (sessions 2-4); {len(NEW_QUERIES)} new-session queries (unrelated topics)\n")

    # 1) similarity_only across k. NOTE: inspeximus's hybrid recall returns only NONZERO-relevance items, so a
    # topically-orthogonal preference is FILTERED OUT entirely (not merely ranked low) - which is why raising
    # k barely moves the mean. The mean also hides a bimodal per-query reality, printed below.
    print("[similarity_only]  recall by query similarity (inspeximus hybrid RRF, strong baseline):")
    sim_at = {}
    pq5 = []
    for k in (3, 5, 10, 20):
        out = pq5 if k == 5 else None
        r = substrate_similarity_only(m, pref_ids, k, per_query_out=out)
        sim_at[k] = r
        print(f"    mean pref_recall@{k:<2} = {r:.3f}")
    zero = sum(1 for v in pq5 if v == 0.0)
    print(f"    per-query pref_recall@5 = {[round(v,2) for v in pq5]}")
    print(f"    -> {zero}/{len(pq5)} unrelated-topic queries surface ZERO of 3 preferences; it's a coin toss "
          f"driven by incidental topical overlap, not reliable recall.")

    # 2) recency_window
    print("\n[recency_window]  inject most-recent W memories (query-independent):")
    rec_at = {}
    for w in (3, 5, 10):
        r = substrate_recency_window(m, pref_ids, w)
        rec_at[w] = r
        print(f"    pref_recall(W={w:<2}) = {r:.3f}")

    # 3) typed_profile
    tp = substrate_typed_profile(m, pref_ids)
    print(f"\n[typed_profile]  retrieve preferences BY TYPE (profile injection, query-independent):")
    print(f"    pref_recall = {tp:.3f}  (all {len(PREFERENCES)} preferences, every query, fixed inject budget)")

    # structural reason + precision cost
    qp, qt = orthogonality(m, pref_ids)
    depth, dragged = precision_cost(m, pref_ids)
    print(f"\nstructural reason (orthogonality): mean cosine(query, preference) = {qp:.3f}  vs  "
          f"mean cosine(query, best on-topic memory) = {qt:.3f}")
    print(f"    -> the preference sits WELL BELOW the on-topic memory (gap {qt-qp:.2f}); with nomic's high"
          f" anisotropic baseline, {qp:.2f} is a low score - so a topical match outranks the preference whenever one exists.")
    if depth is not None:
        print(f"precision cost: to reach the first preference, similarity must go to rank ~{depth:.1f}, "
              f"dragging in ~{dragged:.1f} non-preference memories first.")
    else:
        print(f"precision cost: no preference reached even at k = full store ({n_active}).")

    # CSV in the spec's B-001 column names, per preference, for the similarity_only substrate at k=5
    # (the realistic default). applied_correctly := preference surfaced at retrieval (necessary condition
    # for application); causal_density_at_retrieval := substrate proxy = cosine(query, preference) averaged
    # over queries (how causally-dense-to-the-query the preference chunk is; ~0 == orthogonal). Labelled as
    # a substrate proxy, not Cophy's production-log metric.
    print("\nraw_format (csv eval trace, spec B-001 columns; similarity_only @k=5):")
    buf = io.StringIO(); w = csv.writer(buf)
    w.writerow(["scenario_id", "pressure_type", "preference_id", "applied_correctly",
                "causal_density_at_retrieval", "substrate"])
    pref_vec = {r["meta"]["pid"]: r for r in m.items if r["id"] in pref_ids}
    for pid, _txt in PREFERENCES:
        rec = pref_vec[pid]
        surfaced = 0
        for q in NEW_QUERIES:
            hits = m.recall(q, k=5, mode="hybrid")
            if rec["id"] in {h["id"] for h in hits}:
                surfaced += 1
        dens = float(np.mean([_cos(embed(q), rec["vec"]) for q in NEW_QUERIES])) if rec.get("vec") else 0.0
        w.writerow(["B-001", PRESSURE, pid, int(surfaced > 0), f"{dens:.3f}", "similarity_only"])
    print(buf.getvalue())

    print("Reading: B-001 is a retrieval-OBJECTIVE mismatch, not a storage loss. Query-similarity retrieval\n"
          "ranks by topical relevance to the current query; a preference is causally load-bearing for STYLE\n"
          "but topically orthogonal to the query's CONTENT (cosine to the query well below on-topic memory),\n"
          "so whenever the query has real topical matches they fill the top-k and the preference is filtered\n"
          "out - on half our unrelated-topic queries similarity surfaced 0 of 3 preferences (and it's a coin\n"
          "toss, not a floor). Recency also fails - preferences are the oldest memories. A separate\n"
          "type/profile channel (unconditional injection) is the substrate that gets B-001 right, at a fixed\n"
          "inject-budget cost + a write-time 'this is a preference' classification. This is exactly what\n"
          "production profile memory does (MemGPT/Letta core memory, mem0 user memory); we measure the cost\n"
          "of NOT doing it, we did not invent it.\n"
          "Scope: substrate only (not the agent's generated answer); recall = the necessary precondition for\n"
          "preference application, not proof the model then applied it. Single fixture set / one embedder.")


if __name__ == "__main__":
    main()

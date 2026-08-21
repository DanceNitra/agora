#!/usr/bin/env python3
"""Two-writer retrieval-coherence self-check — "step 6" of the shared-team-memory two-writer test.

Context: the two-writer test discussed on anthropics/claude-code#38536 checks the AUTHORITY layer (a stale
writer must not silently overwrite accepted truth). This fixture checks the layer under it: whatever the
store's governance says, what does RETRIEVAL actually serve after a correction, and after a stale writer
re-asserts the superseded value? Append-only + promotion can be perfectly governed and retrieval can still
rank the retired value first — that's a stale serve the receiving agent never sees.

The script drives each backend's OWN write/correct/read operations:
  1. writer A stores V1 for a subject;
  2. writer A corrects it to V2 (the backend's own correction mechanism — keyed supersession, update(),
     or delete+add where nothing better exists);
  3. a stale writer B re-asserts V1 verbatim (the re-ingested old summary / stale mirror case);
  checks, after each step, whether top-1 retrieval for the subject serves the CURRENT value:
  * serve_correction  — after (2), top-1 is V2;
  * echo_resistance   — after (3), top-1 is STILL V2;
  * witness           — can the backend hand back a state receipt after (2) that DETECTS (3) happened?
                        (capability check: supported / not supported — not a pass/fail.)

Honest scope (read before drawing conclusions):
  * This is a MINIMAL, single-subject fixture, not a benchmark: one fact, one correction, one echo. It tells
    you whether the failure mode is POSSIBLE in your stack, not how often it happens at scale.
  * A raw vector/list store has no correction primitive; we emulate correction as delete+add — failing
    echo_resistance there is a statement about that COMPOSITION, not a bug in the store.
  * Retrieval quality depends on the embedder; backends that need one use MiniLM on CPU, deterministically.
    The inspeximus and naive rows are zero-dependency lexical.
  * The result is YOURS: run it against the stack you actually operate. No claim is made about any vendor.

Usage:  python two_writer_coherence.py             # auto-detect installed backends
        python two_writer_coherence.py inspeximus naive # or name them
"""
import json
import os
import sys
import tempfile
import time

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("OPENAI_API_KEY", "sk-none")   # mem0 default LLM init; we only use its embedder

SUBJECT = "staging database host"
V1 = "The staging database host is db-old.internal"
V2 = "The staging database host is db-new.internal"
QUERY = "what is the staging database host?"


def _emb():
    from sentence_transformers import SentenceTransformer
    m = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
    return lambda t: m.encode([t])[0].tolist()


CHECKS = {}   # name -> callable() -> dict row


def check_inspeximus():
    """inspeximus: keyed supersession + echo_guard; witness() is the state receipt."""
    from inspeximus import Inspeximus
    d = tempfile.mkdtemp()
    m = Inspeximus(path=os.path.join(d, "s.json"))
    m.echo_guard = True
    top = lambda: (m.recall(QUERY, k=1) or [{}])[0].get("text", "")
    m.remember(V1, key="staging-db-host")                      # 1. writer A stores V1
    m.remember(V2, key="staging-db-host")                      # 2. writer A corrects to V2
    serve = V2 == top() or "db-new" in top()
    w = m.witness()                                            #    state receipt after the correction
    m.remember(V1, key="staging-db-host")                      # 3. stale writer B re-asserts V1
    echo = "db-new" in top()
    witness_detects = not m.verify_witness(w)["digest_match"]
    return {"serve_correction": serve, "echo_resistance": echo,
            "witness": "supported", "witness_detects_echo": witness_detects}
CHECKS["inspeximus"] = check_inspeximus


def check_naive():
    """Naive append-only list + lexical-overlap ranking, recency tiebreak — the 'append-only + ranking
    handles it' composition, with no supersession and no receipt. The fixture's falsifier: if this row
    PASSED echo_resistance, the test could not fail and would be a demonstration, not a test."""
    store = []

    def add(text):
        store.append({"text": text, "seq": len(store)})        # deterministic recency: insertion order

    def top():
        q = {w.strip("?.,!") for w in QUERY.lower().split()}
        return max(store, key=lambda r: (len(q & {w.strip("?.,!") for w in r["text"].lower().split()}),
                                         r["seq"]))["text"]

    add(V1)                                                    # 1
    add(V2)                                                    # 2. "correction" = just a newer write
    serve = "db-new" in top()
    add(V1)                                                    # 3. stale echo is newest now
    echo = "db-new" in top()
    return {"serve_correction": serve, "echo_resistance": echo, "witness": "not supported"}
CHECKS["naive"] = check_naive


def check_mem0():
    """mem0 (raw adds, infer=False, local MiniLM): correction via its own update(); echo = new add of V1."""
    from mem0 import Memory
    d = tempfile.mkdtemp()
    mm = Memory.from_config({
        "embedder": {"provider": "huggingface", "config": {"model": "all-MiniLM-L6-v2"}},
        "vector_store": {"provider": "qdrant", "config": {"path": os.path.join(d, "qd"),
                                                          "embedding_model_dims": 384, "on_disk": True}},
        "history_db_path": os.path.join(d, "history.db")})
    a = mm.add(V1, user_id="u", infer=False)                   # 1
    rid = (a.get("results") or [{}])[0].get("id") if isinstance(a, dict) else None
    if rid:
        mm.update(rid, V2)                                     # 2. mem0's own correction op
    top = lambda: ((mm.search(QUERY, filters={"user_id": "u"}, limit=1) or {}).get("results") or [{}])[0].get("memory", "")
    serve = "db-new" in top()
    mm.add(V1, user_id="u", infer=False)                       # 3. stale echo as a fresh memory
    echo = "db-new" in top()
    return {"serve_correction": serve, "echo_resistance": echo, "witness": "not supported"}
CHECKS["mem0"] = check_mem0


def check_chroma():
    """Chroma (raw vector store): no correction primitive — correction emulated as delete+add."""
    import chromadb
    d = tempfile.mkdtemp()
    emb = _emb()
    col = chromadb.PersistentClient(path=d).create_collection("twc")
    col.add(ids=["a1"], documents=[V1], embeddings=[emb(V1)])              # 1
    col.delete(ids=["a1"]); col.add(ids=["a2"], documents=[V2], embeddings=[emb(V2)])   # 2
    top = lambda: (col.query(query_embeddings=[emb(QUERY)], n_results=1)["documents"] or [[""]])[0][0]
    serve = "db-new" in top()
    col.add(ids=["b1"], documents=[V1], embeddings=[emb(V1)])              # 3
    echo = "db-new" in top()
    return {"serve_correction": serve, "echo_resistance": echo, "witness": "not supported"}
CHECKS["chroma"] = check_chroma


def main(argv):
    names = [a for a in argv[1:] if a in CHECKS] or list(CHECKS)
    rows = {}
    for n in names:
        try:
            rows[n] = CHECKS[n]()
        except ImportError:
            rows[n] = {"skipped": "not installed"}
        except Exception as e:                                  # a backend crashing is a result, not a halt
            rows[n] = {"error": f"{type(e).__name__}: {e}"[:200]}
    out = {"fixture": "two_writer_coherence", "subject": SUBJECT, "v1": V1, "v2": V2, "query": QUERY,
           "iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "rows": rows}
    os.makedirs(os.path.join(os.path.dirname(__file__) or ".", "results"), exist_ok=True)
    path = os.path.join(os.path.dirname(__file__) or ".", "results", "two_writer_coherence.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"{'backend':10} {'serve_correction':>16} {'echo_resistance':>16}  witness")
    for n, r in rows.items():
        if "skipped" in r or "error" in r:
            print(f"{n:10} {r.get('skipped') or r.get('error')}")
            continue
        print(f"{n:10} {str(r['serve_correction']):>16} {str(r['echo_resistance']):>16}  {r.get('witness')}"
              + ("  (witness detected the echo)" if r.get("witness_detects_echo") else ""))
    print(f"\nreceipt -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

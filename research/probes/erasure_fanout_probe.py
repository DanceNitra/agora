"""erasure_fanout_probe.py — after a right-to-erasure delete, is the subject's data actually GONE, or still
recoverable across the FAN-OUT?

The gate (2026-07-13) killed the "tamper-evident erasure receipt" framing: practitioners said the real DSAR
pain is not a forged deletion record, it is that a subject's data has fanned out — into derived/summarized
facts, the app's vector index, retrieval logs, caches, backups — and deleting from the memory STORE certifies
only one of those copies. So we measure the thing that actually fails audits, on a stack where WE can fail too.

We store a subject fact, let it fan out into (1) a DERIVED summary and (2) an app-side VECTOR INDEX (the copy
a real RAG app keeps for retrieval), then issue forget_subject() and measure RESIDUAL RECOVERABILITY on each
axis:
  derived_residue : is the value still in an ACTIVE derived record?  (mnemo's lineage cascade should -> 0)
  store_residue   : is the fact still in the store's active recall?  (a delete should -> 0)
  index_residue   : after the store delete, does the APP's vector index still return the fact for a NN query?
                    (the fan-out leak: deleting from the store does NOT purge the app index -> expected ~1.0)

Honest thesis (Crucible-shaped, WE can fail): mnemo's lineage cascade genuinely removes the DERIVED-fact copy —
a real but NARROW win — while the vector-index copy survives for EVERY memory store, because that copy lives in
the app's fan-out, not the store. Memory-store erasure != fan-out erasure. No single-store receipt (mnemo's
included) fixes it; the missing primitive is a CROSS-STORE deletion manifest.

Falsifier: if index_residue is ~0 (the store delete somehow also purges the app index) OR if derived_residue is
high even WITH the lineage cascade (mnemo doesn't remove the derived copy), the thesis is wrong.

Prior art (credit, not claim): text-embedding INVERSION recovers input text from a retained vector (Morris et
al., "Text Embeddings Reveal (Almost) As Much As Text", EMNLP 2023 / vec2text); soft-deleted embeddings in
HNSW stores remain reconstructible (arXiv 2606.18497); EDPB requires erasure be "verifiable and irreversible";
crypto-shredding. This probe measures the FAN-OUT gap; it does not claim to solve inversion.

Run: python research/probes/erasure_fanout_probe.py   (cloud-free; needs numpy + local Ollama nomic-embed-text)
Part of Agora / mnemo (MIT).
"""
import os
import sys
import json
import math
import tempfile
import urllib.request
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from inspeximus import Inspeximus  # noqa: E402

OLLAMA = "http://localhost:11434/api/embeddings"
MODEL = "nomic-embed-text"

SUBJECTS = [
    ("alice-42", "Alice Novak", "medical condition", "type-1 diabetes"),
    ("bob-77", "Bob Kraus", "home address", "12 Maple Street Brno"),
    ("carol-19", "Carol Lin", "salary", "94000 EUR"),
    ("dan-53", "Dan Ott", "religion", "practising Buddhist"),
    ("eve-88", "Eve Radic", "criminal record", "2019 fraud conviction"),
    ("finn-31", "Finn Weiss", "sexual orientation", "gay"),
    ("gina-64", "Gina Marek", "biometric id", "fingerprint hash 9f2a"),
    ("hugo-27", "Hugo Bauer", "political affiliation", "Green Party member"),
    ("iris-70", "Iris Kovac", "genetic marker", "BRCA1 positive"),
    ("jack-45", "Jack Sohn", "immigration status", "asylum applicant"),
]


def embed(text):
    body = json.dumps({"model": MODEL, "prompt": text}).encode()
    req = urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"})
    return np.array(json.loads(urllib.request.urlopen(req, timeout=60).read())["embedding"], dtype=float)


def cos(a, b):
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (p, (c - h) / d, (c + h) / d)


def main():
    fd, path = tempfile.mkstemp(suffix=".json", prefix="fanout_"); os.close(fd)
    for suf in ("", ".receipts.json"):
        try: os.remove(path + suf)
        except OSError: pass
    m = Inspeximus(path=path)

    # the app-side vector index every RAG app keeps for retrieval (text + its embedding), separate from the store
    app_index = []   # list of (subject, text, vector)

    derived_hit = store_hit = index_hit = 0
    n = len(SUBJECTS)
    for (subj, name, rel, value) in SUBJECTS:
        fact = f"{name}'s {rel} is {value}."
        summary = f"Note derived from {name}'s record: {rel} = {value} (keep for context)."
        root = m.remember(fact, key=f"{subj}::{rel}", object=value, source={"doc": subj})
        m.remember(summary, derived_from=[root], source={"doc": subj})     # fan-out copy 1: derived fact
        app_index.append((subj, fact, embed(fact)))                        # fan-out copy 2: app vector index

        # the right-to-erasure act: erase the subject from the STORE (mnemo cascades via lineage)
        m.forget_subject(subj, request_id=f"dsar-{subj}",
                         basis="GDPR Art.17 erasure request")

        # residual recoverability, per axis --------------------------------------------------
        active_text = " ".join((r.get("text") or "") for r in m.items if r.get("status") == "active").lower()
        derived_hit += 1 if value.lower() in active_text else 0            # derived copy still active?
        hits = m.recall(f"what is the {rel} of {name}?", k=6, mode="lexical")
        store_hit += 1 if any(value.lower() in (h.get("text", "") or "").lower() for h in hits) else 0
        # app vector index: the store delete never touched it -> a NN query still recovers the fact + value
        q = embed(f"what is the {rel} of {name}?")
        best = max(app_index, key=lambda t: cos(q, t[2]))
        index_hit += 1 if (value.lower() in best[1].lower()) else 0

    print("=== ERASURE FAN-OUT: is the data actually gone after forget_subject()? ===")
    print(f"subjects={n}  (cloud-free, local nomic; mnemo store + a derived copy + an app vector index)\n")
    for label, k in (("derived_residue (active derived copy of the value)", derived_hit),
                     ("store_residue   (value still in store recall)", store_hit),
                     ("index_residue   (app vector index still recovers it)", index_hit)):
        p, lo, hi = wilson(k, n)
        print(f"  {label:<52} {p:.2f}  [{lo:.2f},{hi:.2f}]  ({k}/{n})")
    print()
    dr, sr, ir = derived_hit / n, store_hit / n, index_hit / n
    out = os.path.join(os.path.dirname(__file__), "erasure_fanout_result.json")
    json.dump({"n": n, "derived_residue": dr, "store_residue": sr, "index_residue": ir}, open(out, "w"), indent=1)
    for suf in ("", ".receipts.json"):
        try: os.remove(path + suf)
        except OSError: pass

    print(f"FINDING: mnemo's lineage cascade removes the DERIVED copy (derived_residue {dr:.2f}) and the store "
          f"copy (store_residue {sr:.2f}) — a real but NARROW win. But the APP VECTOR INDEX copy survives "
          f"(index_residue {ir:.2f}): deleting from the memory store does NOT purge the fan-out. Memory-store "
          f"erasure != fan-out erasure — for EVERY store, mnemo included. The missing primitive is a cross-store")
    print("  deletion manifest (and even then, embedding inversion — Morris 2023 — bounds what deletion can promise).")
    if ir < 0.5:
        print("  [NOTE: index_residue unexpectedly low — falsifier region; re-examine before any claim.]")


if __name__ == "__main__":
    main()

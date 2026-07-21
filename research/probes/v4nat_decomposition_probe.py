"""v4nat_decomposition_probe.py — Marat's cosine result reproduced, localized, and RESOLVED (2026-07-12).

Marat Sultanov reported that plain cosine similarity (candidate vs the four context lines) solves the
naturalized v4 heldout at F1 0.905 / AUROC 0.964 — directly contradicting our published audit line
"cosine (cand vs old/new line): F1 0.481". He was right; our audit's cosine variant compared the candidate
only against the VALUE-BEARING action lines (selected by value-token presence) and never against the ROLE
lines, where the signal lives (the candidate references its anchor by role). One family member tested,
whole family declared dead — our error.

This probe measures the full picture on the heldout split (46 rows), one shared embedding pass:

  1. REPRODUCTION — Marat's method as stated (cosine vs 4 lines, positional old/new = lines [0,2] vs [1,3]).
  2. SHUFFLE — same method with context order destroyed: collapses to chance. The old/new half of his
     method rides the fixture's FIXED line order — a construction artifact standing in for metadata.
  3. DECOMPOSITION (the resolution, not an escape to a v5): the task factorizes into
       (a) reference resolution — candidate -> best-matching context line (structure match, Marat's step), then
       (b) old-vs-new attribution — NOT a text problem: in any real memory system this is LEDGER metadata
           (who set which value; supersession order). With explicit ledger metadata and order destroyed,
           the detector holds. The fixture's "positional leak" was accidentally simulating the provenance
           metadata every real store has.
  4. RESIDUAL — the surviving false positives are candidates whose target role matches NEITHER context role
     (unresolvable references); similarity guesses where the correct behavior is abstention.

The channel-separation thesis is sharpened, not harmed: the ROLE-REFERENCED subfamily is decidable from
text + ledger; the truly value-obscuring twin (no reference at all) remains undecidable from text alone.

Needs the local embedder (Ollama nomic-embed-text). RUN: python research/probes/v4nat_decomposition_probe.py
"""
import json, urllib.request, random, pathlib, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = pathlib.Path(__file__).resolve().parents[2]
FIX = ROOT / "agora_output" / "public_fixtures" / "value_obscuring_reversion_heldout_v4nat.jsonl"


def embed(texts):
    body = json.dumps({"model": "nomic-embed-text", "input": texts}).encode()
    r = urllib.request.urlopen(urllib.request.Request(
        "http://localhost:11434/api/embed", data=body,
        headers={"Content-Type": "application/json"}), timeout=180)
    return json.loads(r.read())["embeddings"]


def f1_of(preds, ys):
    tp = sum(p == 1 and y == 1 for p, y in zip(preds, ys))
    fp = sum(p == 1 and y == 0 for p, y in zip(preds, ys))
    fn = sum(p == 0 and y == 1 for p, y in zip(preds, ys))
    tn = sum(p == 0 and y == 0 for p, y in zip(preds, ys))
    prec = tp / (tp + fp) if tp + fp else 0
    rec = tp / (tp + fn) if tp + fn else 0
    return (2 * prec * rec / (prec + rec) if prec + rec else 0.0), (tn, fp, fn, tp)


rows = [json.loads(l) for l in open(FIX, encoding="utf-8")]
held = [r for r in rows if r.get("split") == "heldout"]
data = []
for r in held:
    embs = embed([r["candidate"]] + r["context"])
    c = embs[0]
    data.append((r, [sum(a * b for a, b in zip(c, e)) for e in embs[1:]]))
ys = [r["reopens_stale"] for r, _ in data]
R = {"heldout_n": len(held)}

# 1. Marat's method, positional (fixture order: [0]=old action, [1]=new action, [2]=old role, [3]=new role)
p1 = [1 if max(cos[0], cos[2]) > max(cos[1], cos[3]) else 0 for _, cos in data]
R["1_marat_positional_F1"], R["1_confusion"] = f1_of(p1, ys)

# 2. same method, context order shuffled per row (deterministic) — position carries nothing
p2 = []
for r, cos in data:
    idx = list(range(4)); random.Random(r["id"]).shuffle(idx)
    cc = [cos[i] for i in idx]
    p2.append(1 if max(cc[0], cc[2]) > max(cc[1], cc[3]) else 0)
R["2_shuffled_positional_F1"], _ = f1_of(p2, ys)

# 3. decomposition: structure match on SHUFFLED order + ledger metadata (who set which value)
p3 = []; fp_rows = []
for r, cos in data:
    idx = list(range(4)); random.Random(r["id"]).shuffle(idx)
    ctx = [r["context"][i] for i in idx]; cs = [cos[i] for i in idx]
    anchor = None
    for i in sorted(range(4), key=lambda j: -cs[j]):
        line = ctx[i].lower()
        if r["anchor_old"].lower() in line and r["anchor_current"].lower() not in line:
            anchor = "old"; break
        if r["anchor_current"].lower() in line and r["anchor_old"].lower() not in line:
            anchor = "new"; break
    pred = 1 if anchor == "old" else 0        # LEDGER: anchor_old is who set old_value (provenance metadata)
    p3.append(pred)
    if pred == 1 and r["reopens_stale"] == 0:
        fp_rows.append(r)
R["3_decomposition_F1"], R["3_confusion"] = f1_of(p3, ys)

# 4. residual: are the FPs unresolvable references (target role present in neither context role line)?
R["4_residual_fp"] = len(fp_rows)
R["4_fp_all_unresolvable_references"] = all(
    r["role_target"] not in (r["role_old"], r["role_current"]) for r in fp_rows)

print(json.dumps(R, indent=2))
ok = (R["1_marat_positional_F1"] > 0.85 and R["2_shuffled_positional_F1"] < 0.65
      and R["3_decomposition_F1"] > 0.85 and R["4_fp_all_unresolvable_references"])
print("\nREADING: Marat's result is real (1). Its old/new half rode the fixture's fixed line order (2). But")
print("that order was a stand-in for the provenance metadata every real store has: with explicit ledger")
print("metadata the detector holds with order destroyed (3) — the task factorizes into structure-matching")
print("(text) + recency attribution (ledger). The residual failures are unresolvable references, where the")
print("correct behavior is abstention, not a guess (4).")
print("\nALL PASS" if ok else "\nFAIL")
sys.exit(0 if ok else 1)

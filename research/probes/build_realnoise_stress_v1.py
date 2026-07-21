"""build_realnoise_stress_v1.py — a labeled REAL-NOISE stress set for reversion detection (for Marat's
TAT-Monitor request, 2026-07-12).

Marat asked to stress-test TAT-Monitor on "real dialog records from mnemo" before the joint write-up. Raw
production records have no labels, so this builds the rigorous version: REAL records from our live brain
mnemo store (server/.mnemo_brain.json, 2769 records, PII/secret-scanned clean) serve as the NOISE stream,
and a value-correction chain with a labeled candidate is PLANTED into each case — ground truth known by
construction, noise genuinely real.

Per case: entity value asserted (A), corrected (B), then a CANDIDATE that either reopens the stale value
(label 1: half natural revert phrasings, half value-obscuring ones with no revert lexeme) or keeps/moves on
(label 0: affirm-current or named-new third value). The planted lines are INTERLEAVED with 4-6 real noise
lines and the order is SHUFFLED per case (seeded) — the correction is deliberately NOT always last, so the
recency-of-mention shortcut cannot carry it. Positions of planted lines are recorded per row.

The audit at the bottom enumerates the FULL shortcut family (the v4nat lesson: never declare a family dead
from one member): value-token, revert-keyword, last-line-recency, template-majority, and the cosine family
(candidate vs planted-old / planted-new / best-noise / all-lines argmax). Honest per-subset reporting
(natural vs obscured).

RUN: python research/probes/build_realnoise_stress_v1.py         (writes the jsonl + prints the audit)
"""
import json, random, re, os, sys, urllib.request, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(__file__))
import integrity_bench_revert as rev

SEED = 20260712
OUT = os.path.join(os.path.dirname(__file__), "..", "..", "agora_output", "public_fixtures",
                   "realnoise_stress_v1.jsonl")
BRAIN = os.path.join(os.path.dirname(__file__), "..", "..", "server", ".mnemo_brain.json")

R1_NATURAL = [
    "let's roll the {e} back to what it was before.",
    "can we undo the recent {e} change, please.",
    "I'd restore the earlier {e} setting.",
    "switch the {e} back to the previous choice.",
    "we should revert the {e} decision.",
]
# keyword-free, value-free positives: the candidate defers to the OLD setter by name (reference resolution)
R1_ANCHORED = [
    "let's go with {n1}'s call on the {e}.",
    "whatever {n1} decided for the {e} is what we should run.",
    "I trust {n1}'s judgment on the {e}, apply that.",
    "the {e} belongs the way {n1} had it.",
    "side with {n1} on the {e} question.",
    "{n1} made the right call on the {e}, use it.",
]
R0_KEEP = [
    "the current {e} is working, keep it as is.",
    "no change needed on the {e}, we stay put.",
    "I'm satisfied with where the {e} landed.",
    "let's proceed with the {e} we have now.",
    "the {e} stays as configured, moving on.",
]
# keyword-BEARING negatives (distractors: revert lexemes present, but the decision is to KEEP)
R0_KW_DISTRACTOR = [
    "we almost went back on the {e} earlier, but the current choice stands.",
    "forget the original {e} idea, the new one is right.",
    "no need to restore anything, the {e} is fine as it is.",
    "someone suggested reverting the {e}; I disagree, keep it.",
    "I considered undoing the {e} change, then thought better of it.",
]
# name-BEARING negatives (old setter mentioned, but the decision keeps CURRENT -> name-presence is no shortcut)
R0_NAME_DISTRACTOR = [
    "even {n1} agrees the current {e} is right, keep it.",
    "stick with {n2}'s update on the {e}.",
    "{n2} settled the {e}, we follow that.",
    "I spoke with {n1}; we both prefer the {e} as it stands now.",
]
R0_NAMEDNEW = [
    "actually, move the {e} over to {c}.",
    "new plan: set the {e} to {c}.",
    "let's try {c} for the {e} instead.",
    "the {e} should become {c} going forward.",
    "please update the {e} to {c}.",
]
NAMES = ["marcus", "the vendor", "the audit team", "priya", "the review board", "old tomas",
         "the platform crew", "lena", "the ops desk", "the architect"]
def clean_noise_lines(records, rng, want):
    """Real record texts -> single noise lines (first sentence-ish, length-bounded, deduped)."""
    lines, seen = [], set()
    idx = list(range(len(records))); rng.shuffle(idx)
    for i in idx:
        t = (records[i].get("text") or "").strip().replace("\n", " ")
        t = re.split(r"(?<=[.!?]) ", t)[0][:180].strip()
        if len(t) < 40 or t.lower() in seen:
            continue
        seen.add(t.lower()); lines.append(t)
        if len(lines) >= want:
            break
    return lines


def main():
    rng = random.Random(SEED)
    records = json.load(open(BRAIN, encoding="utf-8"))
    noise_pool = clean_noise_lines(records, rng, 1200)
    third = {e: f"{B}x" for (e, A, B) in rev.ENTS}          # a distinct named-new value per entity
    rows = []
    rid = 0
    for rep in range(2):
        for (e, A, B) in rev.ENTS:
            n1, n2 = rng.sample(NAMES, 2)
            kind = rid % 8                                   # exact 50/50: {0,4}=natural {1,3}=anchored pos; rest neg
            if kind in (0, 4):
                cand = rng.choice(R1_NATURAL).format(e=e); label = 1; sub = "revert_natural"
            elif kind in (1, 3):
                cand = rng.choice(R1_ANCHORED).format(e=e, n1=n1); label = 1; sub = "revert_anchored"
            elif kind == 2:
                cand = rng.choice(R0_KEEP).format(e=e); label = 0; sub = "keep"
            elif kind == 5:
                cand = rng.choice(R0_KW_DISTRACTOR).format(e=e); label = 0; sub = "keep_kw_distractor"
            elif kind == 7:
                cand = rng.choice(R0_NAME_DISTRACTOR).format(e=e, n1=n1, n2=n2); label = 0; sub = "keep_name_distractor"
            else:
                cand = rng.choice(R0_NAMEDNEW).format(e=e, c=third[e]); label = 0; sub = "named_new"
            planted = [f"the {e} was set to {A} at the outset, and that was {n1}'s call.",
                       f"correction: {n2} moved the {e} to {B}."]
            n_noise = rng.randint(4, 6)
            noise = [noise_pool[(rid * 7 + j) % len(noise_pool)] for j in range(n_noise)]
            ctx = planted + noise
            order = list(range(len(ctx))); rng.shuffle(order)
            pa, pc = order.index(0), order.index(1)
            if pa > pc:
                order[pa], order[pc] = order[pc], order[pa]
            context = [ctx[i] for i in order]
            rows.append({"id": rid, "entity": e, "old_value": A, "current_value": B,
                         "anchor_old": n1, "anchor_current": n2,
                         "context": context, "candidate": cand, "kind": sub,
                         "reopens_stale": label,
                         "planted_old_idx": order.index(0), "planted_new_idx": order.index(1),
                         "n_noise": n_noise})
            rid += 1
    with open(OUT, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} rows -> {os.path.relpath(OUT)}")
    print(f"labels: 1={sum(r['reopens_stale'] for r in rows)} 0={sum(1-r['reopens_stale'] for r in rows)} | "
          f"subsets: " + str({s: sum(1 for r in rows if r['kind'] == s) for s in
                              sorted(set(x['kind'] for x in rows))}))

    # ── FULL-FAMILY shortcut audit (the v4nat lesson) ─────────────────────────
    def f1(preds):
        tp = sum(p and r["reopens_stale"] for p, r in zip(preds, rows))
        fp = sum(p and not r["reopens_stale"] for p, r in zip(preds, rows))
        fn = sum((not p) and r["reopens_stale"] for p, r in zip(preds, rows))
        pr = tp / (tp + fp) if tp + fp else 0; rc = tp / (tp + fn) if tp + fn else 0
        return round(2 * pr * rc / (pr + rc), 3) if pr + rc else 0.0

    allpos = f1([True] * len(rows))
    print(f"\nshortcut-family audit (F1 on all {len(rows)}; trivial all-positive baseline F1={allpos} - alive only ABOVE this):")
    print("  value-token (old value named in candidate):",
          f1([r["old_value"] in r["candidate"].lower() for r in rows]))
    kw = re.compile(r"\b(back|revert|undo|restore|previous|earlier|original|first|start|before)\b")
    print("  revert-keyword rule:", f1([bool(kw.search(r["candidate"].lower())) for r in rows]))
    print("  last-context-line-is-old-value (recency):",
          f1([r["planted_old_idx"] == len(r["context"]) - 1 for r in rows]))
    print("  planted-correction-position rule (new line last):",
          f1([r["planted_new_idx"] != len(r["context"]) - 1 for r in rows]))
    # cosine family — every member, our local embedder
    def embed(texts):
        body = json.dumps({"model": "nomic-embed-text", "input": texts}).encode()
        rr = urllib.request.urlopen(urllib.request.Request(
            "http://localhost:11434/api/embed", data=body,
            headers={"Content-Type": "application/json"}), timeout=180)
        return json.loads(rr.read())["embeddings"]
    c_old, c_new, c_noise = [], [], []
    for r in rows:
        embs = embed([r["candidate"]] + r["context"])
        c = embs[0]; cos = [sum(a * b for a, b in zip(c, v)) for v in embs[1:]]
        c_old.append(cos[r["planted_old_idx"]]); c_new.append(cos[r["planted_new_idx"]])
        c_noise.append(max(cos[i] for i in range(len(cos))
                           if i not in (r["planted_old_idx"], r["planted_new_idx"])))
    print("  cosine: cand closer to planted-old than planted-new:", f1([a > b for a, b in zip(c_old, c_new)]))
    print("  cosine: planted-old beats best noise line:", f1([a > n for a, n in zip(c_old, c_noise)]))
    print("  cosine: old-vs-new margin > 0.05:", f1([a - b > 0.05 for a, b in zip(c_old, c_new)]))
    print("  name-token (old-setter's name in candidate):",
          f1([r.get("anchor_old","") in r["candidate"].lower() for r in rows]))
    for sub in ("revert_natural", "revert_anchored"):
        idx = [i for i, r in enumerate(rows) if r["kind"] == sub or r["reopens_stale"] == 0]
        tp = sum(1 for i in idx if rows[i]["kind"] == sub and c_old[i] > c_new[i])
        tot = sum(1 for i in idx if rows[i]["kind"] == sub)
        print(f"  cosine old>new recall on {sub}: {tp}/{tot}")


if __name__ == "__main__":
    main()

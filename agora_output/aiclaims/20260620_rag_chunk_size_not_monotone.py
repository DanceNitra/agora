"""
CLAIM: Smaller chunks improve RAG retrieval quality -- 'when in doubt, chunk smaller.'

TEST: numpy only, deterministic. A document is a length-D relevance vector with ONE
contiguous gold span. Fixed-grid chunking (boundaries independent of the span).
Score each chunk by gold DENSITY (rewards small focused chunks = the precision force),
retrieve top-k=3, measure RECOVERY = distinct gold tokens recovered / span length.

Two opposing forces, both built in, no LLM needed:
  - small c maximizes density (precision force, favors 'smaller is better')
  - small c SPLITS the contiguous span into many pieces a k=3 budget cannot reassemble
    (recall loss, the force that breaks the folklore)

CONTROL (negative case): k = large (>= D//c, retrieve ALL chunks). Then there is NO
budget limit, fragmentation is harmless, and recovery must be ~1.0 for every c. If the
control did NOT flatten, the harness itself would be rigging the result -- so the
control proves the effect comes from the k=3 budget, not from a baked-in bias.

DECISION (main, k=3):
  REPRODUCED only if mean recovery is monotonically NON-INCREASING in c
                (each larger c <= next smaller, tolerance +0.01).
  FAILED if smallest c=10 is NOT the maximum, i.e. some larger c beats it by > 0.02.
Robustness: seeds {7,8,9} x L_rel {30,40,50}; final verdict = majority.
ASCII output only.
"""
import numpy as np

D = 200
CHUNKS = [10, 20, 40, 80, 200]
TR = 6000
TOPK = 3


def mean_recovery(c, L_rel, seed, topk):
    rng = np.random.default_rng(seed)
    edges = list(range(0, D, c)) + [D]
    # de-dup in case D is a multiple of c (e.g. c=200 -> [0,200,200])
    bounds = []
    for i in range(len(edges) - 1):
        a, b = edges[i], edges[i + 1]
        if b > a:
            bounds.append((a, b))
    recs = np.empty(TR)
    for t in range(TR):
        off = int(rng.integers(0, D - L_rel + 1))
        gold = np.zeros(D, dtype=bool)
        gold[off:off + L_rel] = True
        dens = np.array([gold[a:b].mean() for (a, b) in bounds])
        k = min(topk, len(bounds)) if topk is not None else len(bounds)
        # top-k chunks by density; deterministic tie-break by chunk index
        order = np.lexsort((np.arange(len(dens)), -dens))
        sel = order[:k]
        recovered = np.zeros(D, dtype=bool)
        for j in sel:
            a, b = bounds[j]
            recovered[a:b] |= gold[a:b]
        recs[t] = recovered.sum() / L_rel
    return recs.mean()


def verdict_for(L_rel, seed):
    rec = {c: mean_recovery(c, L_rel, seed, TOPK) for c in CHUNKS}
    smallest = CHUNKS[0]
    best_c = max(rec, key=lambda c: rec[c])
    # FAILED if some larger c beats c=10 by > 0.02
    failed = any(rec[c] - rec[smallest] > 0.02 for c in CHUNKS if c > smallest)
    # REPRODUCED if non-increasing within tolerance
    non_incr = all(rec[CHUNKS[i + 1]] <= rec[CHUNKS[i]] + 0.01 for i in range(len(CHUNKS) - 1))
    if failed:
        v = "FAILED"
    elif non_incr:
        v = "REPRODUCED"
    else:
        v = "NOT_COMPUTABLE"
    return v, rec, best_c


def main():
    print("=" * 70)
    print("CLAIM: smaller chunks -> better RAG retrieval ('chunk smaller')")
    print("D=%d, top-k=%d, trials=%d per cell" % (D, TOPK, TR))
    print("=" * 70)

    # ---- CONTROL: no budget limit (retrieve ALL chunks) ----
    print("\nCONTROL (negative case): topk=ALL, no budget -> fragmentation harmless")
    ctrl = {c: mean_recovery(c, 40, 7, None) for c in CHUNKS}
    for c in CHUNKS:
        print("  c=%3d  recovery=%.3f" % (c, ctrl[c]))
    ctrl_flat = all(abs(ctrl[c] - 1.0) < 1e-9 for c in CHUNKS)
    print("  CONTROL flat at 1.000 for all c: %s" % ctrl_flat)
    if not ctrl_flat:
        print("  WARNING: control not flat -> harness may be biased")

    # ---- MAIN sweep, primary cell (seed 7, L_rel 40) ----
    print("\nMAIN k=3 sweep, primary cell (seed=7, L_rel=40):")
    v0, rec0, best0 = verdict_for(40, 7)
    for c in CHUNKS:
        print("  c=%3d  mean recovery=%.3f" % (c, rec0[c]))
    print("  best chunk size = %d  (smallest c=10 recovery=%.3f)" % (best0, rec0[10]))
    print("  primary-cell verdict: %s" % v0)

    # ---- ROBUSTNESS: seeds x L_rel, majority ----
    print("\nROBUSTNESS grid (seeds {7,8,9} x L_rel {30,40,50}):")
    tally = {"REPRODUCED": 0, "FAILED": 0, "NOT_COMPUTABLE": 0}
    for seed in (7, 8, 9):
        for L_rel in (30, 40, 50):
            v, rec, best = verdict_for(L_rel, seed)
            tally[v] += 1
            print("  seed=%d L_rel=%2d -> %-14s best_c=%3d  c10=%.3f c20=%.3f c40=%.3f"
                  % (seed, L_rel, v, best, rec[10], rec[20], rec[40]))
    final = max(tally, key=lambda k: tally[k])
    print("\nTally: %s" % tally)

    print("\n" + "=" * 70)
    print("MEASURED (primary): c=10 -> %.3f ; best chunk size = %d (recovery %.3f)"
          % (rec0[10], best0, rec0[best0]))
    print("VERDICT: %s  (majority over 9 cells)" % final)
    print("=" * 70)


if __name__ == "__main__":
    main()

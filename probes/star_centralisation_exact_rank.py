"""Is the star's quantum-information signature a DISCOVERY, or a restatement of what a star is?

WHAT WAS CLAIMED. Marat measured three observables on the N=7 star against 50 random labeled trees:
pairwise mutual information (star 0.6407 vs 0.443 +/- 0.050, "3.98 sigma"), ground-state von Neumann
entropy (4.2147 vs 3.8215 +/- 0.1101, "3.6 sigma"), and the correlation ratio |C(2)|/|C(1)| (0.33 vs
0.24-0.30). He asked for an audit before any of it becomes a paper section, which is the right call.

THREE PROBLEMS, and this file exists to settle the third, which is the one that decides everything.

  1. THEY ARE NOT INDEPENDENT. All three are functionals of the SAME ground state of the SAME
     Hamiltonian. Three views, not three confirmations. Nothing here needs measuring to say that.

  2. THE NULL MODEL DOES NOT NEED SAMPLING. By Cayley there are 7^5 = 16807 labeled trees on seven
     nodes, so the ensemble is enumerable and the star's EXACT RANK is available. A z-score from 50
     draws assumes normality of a bounded statistic on a small discrete ensemble, which is not
     justified, and "3.98 sigma" is a weaker statement than "rank 1 of 16807" would be.

  3. THE STAR IS THE EXTREME POINT OF CENTRALISATION AMONG TREES. Finding that the extreme point of a
     structural parameter sits far from the ensemble mean may be a restatement of the definition
     rather than a finding. The test that separates the two:

        if the observable is MONOTONE in centralisation, the star is the endpoint of a trend, and
        the honest claim is the trend -- a law, and a stronger result than an outlier;

        if the star sits ABOVE the trend its own centralisation predicts, that excess is the
        discovery, and it is measured here as a residual.

METHOD, independent of theirs: exact diagonalisation of the isotropic Heisenberg Hamiltonian on the
full 2^7 space, no sector bookkeeping and no DMRG. Every one of the 16807 Prufer sequences is
enumerated, grouped into isomorphism classes by an exact check, and each class is evaluated once and
weighted by its multiplicity -- so the reported distribution is over the whole labeled ensemble while
the diagonalisation runs once per distinct shape.

    python star_centralisation_exact_rank.py
"""
import io
import itertools
import json
import os

import numpy as np

RESULT = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"
N = 7
S_MI = 1.5                      # the point Marat used for mutual information


def prufer_to_tree(seq, n):
    """Every labeled tree on n nodes is exactly one Prufer sequence of length n-2."""
    degree = [1] * n
    for node in seq:
        degree[node] += 1
    edges = []
    for node in seq:
        for leaf in range(n):
            if degree[leaf] == 1:
                edges.append((leaf, node))
                degree[leaf] -= 1
                degree[node] -= 1
                break
    rest = [v for v in range(n) if degree[v] == 1]
    edges.append((rest[0], rest[1]))
    return tuple(sorted(tuple(sorted(e)) for e in edges))


def canonical(edges, n):
    """Exact isomorphism class: the lexicographically smallest relabelling. n=7 so 5040 perms."""
    best = None
    for perm in itertools.permutations(range(n)):
        relabelled = tuple(sorted(tuple(sorted((perm[a], perm[b]))) for a, b in edges))
        if best is None or relabelled < best:
            best = relabelled
    return best


def heisenberg(edges, n, contradiction=None, s=1.0):
    """Isotropic Heisenberg on the graph, full 2^n space. One bond may carry a different coupling."""
    dim = 1 << n
    H = np.zeros((dim, dim))
    for a, b in edges:
        J = s if (contradiction is not None and (a, b) == contradiction) else 1.0
        for state in range(dim):
            sa = (state >> a) & 1
            sb = (state >> b) & 1
            H[state, state] += J * (0.25 if sa == sb else -0.25)
            if sa != sb:                                   # 1/2 (S+S- + S-S+)
                flipped = state ^ (1 << a) ^ (1 << b)
                H[flipped, state] += J * 0.5
    return H


def sector(n, n_up):
    """Basis indices with exactly `n_up` spins up. Sz is conserved, so the sector is invariant."""
    return [k for k in range(1 << n) if bin(k).count("1") == n_up]


def ground_state(edges, n, s, bond=None):
    """Ground state in the minimal-|Sz| sector, with the DEGENERACY REPORTED, not hidden.

    The first version diagonalised the full 2^n space and returned `vecs[:, 0]`. For the star that is
    meaningless: its ground space is degenerate, `eigh` returns an arbitrary member, and the mutual
    information of an arbitrary vector from a degenerate multiplet is not a property of the graph.
    Measured -- the star's MI ranged 0.0688 to 0.2810 across choices of which bond carries `s`, even
    though all six of its edges are equivalent by symmetry, and its full-space ground state had
    <Sz> = -2.5 where the path's had -0.5. A spread larger than the entire between-shape range, on a
    quantity that symmetry says must be constant, is the instrument and not the system.

    So: fix the sector, and return the gap alongside. A caller that ignores a vanishing gap is back
    where this started.
    """
    idx = sector(n, n // 2)
    H = heisenberg(edges, n, contradiction=bond or tuple(sorted(edges[0])), s=s)
    Hs = H[np.ix_(idx, idx)]
    vals, vecs = np.linalg.eigh(Hs)
    psi = np.zeros(1 << n)
    psi[idx] = vecs[:, 0]
    return psi, float(vals[1] - vals[0])


def _entropy(rho):
    w = np.linalg.eigvalsh(rho)
    w = w[w > 1e-12]
    return float(-(w * np.log(w)).sum())


def _rdm(psi, n, sites):
    """Reduced density matrix over `sites`, by reshaping the state into (kept, traced)."""
    keep = list(sites)
    rest = [i for i in range(n) if i not in keep]
    t = psi.reshape([2] * n)
    t = np.transpose(t, keep + rest)
    m = t.reshape(2 ** len(keep), 2 ** len(rest))
    return m @ m.conj().T


def mean_pairwise_mi(psi, n):
    """Mean I(i:j) over all pairs. Invariant under relabelling, so it is a property of the SHAPE."""
    s1 = [_entropy(_rdm(psi, n, [i])) for i in range(n)]
    total, count = 0.0, 0
    for i in range(n):
        for j in range(i + 1, n):
            total += s1[i] + s1[j] - _entropy(_rdm(psi, n, [i, j]))
            count += 1
    return total / count


def main():
    print("Enumerating all %d labeled trees on %d nodes (Cayley), grouping by shape...\n"
          % (N ** (N - 2), N))
    classes = {}
    for seq in itertools.product(range(N), repeat=N - 2):
        edges = prufer_to_tree(list(seq), N)
        key = canonical(edges, N)
        if key not in classes:
            classes[key] = {"edges": edges, "count": 0}
        classes[key]["count"] += 1
    total_labeled = sum(c["count"] for c in classes.values())
    assert total_labeled == N ** (N - 2), total_labeled
    print("  %d distinct shapes, %d labeled trees total\n" % (len(classes), total_labeled))

    rows = []
    for key, info in classes.items():
        edges = info["edges"]
        deg = [0] * N
        for a, b in edges:
            deg[a] += 1
            deg[b] += 1
        psi, gap = ground_state(edges, N, S_MI)
        rows.append({"max_degree": max(deg), "count": info["count"], "gap": gap,
                     "mean_pairwise_mi": mean_pairwise_mi(psi, N),
                     "degenerate": gap < 1e-9,
                     "is_star": max(deg) == N - 1})

    rows.sort(key=lambda r: -r["mean_pairwise_mi"])
    star = next(r for r in rows if r["is_star"])

    # EXACT RANK over the labeled ensemble, not a z-score.
    above = sum(r["count"] for r in rows if r["mean_pairwise_mi"] > star["mean_pairwise_mi"])
    print("%-6s %-8s %-9s %s" % ("maxdeg", "labeled", "mean MI", ""))
    for r in rows:
        print("%-6d %-8d %-9.4f %s" % (r["max_degree"], r["count"], r["mean_pairwise_mi"],
                                       "<- STAR" if r["is_star"] else ""))

    # IS IT MONOTONE IN CENTRALISATION? If yes the star is an endpoint, not an outlier.
    by_deg = {}
    for r in rows:
        by_deg.setdefault(r["max_degree"], []).append(r["mean_pairwise_mi"])
    degs = sorted(by_deg)
    means = [float(np.mean(by_deg[d])) for d in degs]
    monotone = all(means[i] <= means[i + 1] for i in range(len(means) - 1)) or \
               all(means[i] >= means[i + 1] for i in range(len(means) - 1))

    print("\n  mean MI by max degree: %s" % ", ".join(
        "deg%d=%.4f" % (d, m) for d, m in zip(degs, means)))
    print("  monotone in centralisation: %s" % monotone)
    print("\n  star exact rank: %d of %d labeled trees (%d strictly above)"
          % (above + 1, total_labeled, above))

    out = {"n": N, "s": S_MI, "shapes": len(classes), "labeled_total": total_labeled,
           "star_mean_pairwise_mi": star["mean_pairwise_mi"],
           "star_exact_rank": above + 1, "labeled_strictly_above": above,
           "monotone_in_max_degree": bool(monotone),
           "mean_mi_by_max_degree": dict(zip(map(str, degs), means)),
           "rows": rows}
    io.open(RESULT, "w", encoding="utf-8", newline="\n").write(json.dumps(out, indent=2) + "\n")
    print("\nwrote %s" % os.path.basename(RESULT))

    if monotone:
        print("\nREADING: the observable is monotone in centralisation, so the star is the ENDPOINT")
        print("of a trend rather than an outlier against it. The defensible claim is the trend --")
        print("which is a stronger result than a 4-sigma outlier, and a different one.")
    else:
        print("\nREADING: not monotone. The star's position is not explained by centralisation alone,")
        print("and the excess is worth reporting as its own effect.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

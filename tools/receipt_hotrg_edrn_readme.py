"""Receipt for agora_output/hotrg_edrn/README.md — the document a co-authored manuscript cites.

WHY THIS ONE FIRST. Its data-availability line is quoted in luoxuejian000/edrn-dmrg-verification#2,
so its figures travel further than anything else we publish. And it is where 0.1902 stood for weeks:
an "exact L2 local valley depth" whose definition of "local" was never recorded, which we could not
reproduce when finally asked, and which we have now marked unverified.

A receipt is not "the number appears somewhere". It opens the document, re-derives each figure from
code, and fails on a mismatch. It must also SAY WHICH FIGURES IT CANNOT REACH — a green check over
half a document is the same defect one level up.

    python tools/receipt_hotrg_edrn_readme.py           # verify
    python tools/receipt_hotrg_edrn_readme.py --list    # what it covers and what it cannot

Runtime a couple of minutes: the depth figures need 151-point scans in four configurations.
"""
from __future__ import annotations

import argparse
import importlib.util
import pathlib
import sys
import time

import networkx as nx
import numpy as np
from scipy.sparse.linalg import eigsh

# This console is cp1250. The README quotes its energies with U+2212 MINUS SIGN, so echoing them back
# kills the process on the LAST line, after 72 seconds of correct computation -- a receipt that
# cannot report is a receipt that did not run.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:                                                  # noqa: BLE001
    pass

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOOL = ROOT / "agora_output" / "hotrg_edrn"
DOC = TOOL / "README.md"

spec = importlib.util.spec_from_file_location("sg", TOOL / "scan_guard.py")
SG = importlib.util.module_from_spec(spec)
spec.loader.exec_module(SG)

# Figures the README states that NOTHING here can re-derive, each with the reason. Naming them is
# the point: an unlisted gap reads as coverage.
OUT_OF_REACH = {
    "−49.3": "an L3 (42-spin) RG extrapolation. Beyond exact diagonalisation; only the RG produces "
             "it, and the README already marks its convergence as the open question.",
    "0.1902": "the figure whose definition of 'local' was never recorded. Marked unverified in the "
              "README on 2026-08-18; reconstruction brackets it at 0.181144 / 0.200462 without "
              "reaching it. It stays out of reach BY DESIGN until the definition is stated.",
    "0.24 / 0.08 / 0.20": "the L3 truncation wander. Requires the impurity RG at three bond "
                          "dimensions on hardware that did not converge it.",
    "~86% / ~20%": "far-bath vs uniform truncation recovery, both impurity-RG runs, not ED.",
}

checks: list[tuple[str, bool, str]] = []


def ck(name, ok, detail):
    checks.append((name, bool(ok), detail))


def ground_energy(level: int, isotropic: bool = False) -> float:
    G = SG.sierpinski_gasket(level)
    n = G.number_of_nodes()
    e = sorted(tuple(sorted(x)) for x in G.edges())
    h = SG._H(n, e, [1.0] * len(e), SG._z(n), isotropic)
    if n <= 13:
        return float(np.linalg.eigvalsh(h.toarray())[0])
    w = eigsh(h, k=2, which="SA", tol=0, maxiter=300000,
              v0=np.random.default_rng(1).standard_normal(1 << n), return_eigenvectors=False)
    return float(np.sort(w)[0])


def _gasket_labelled():
    """The collaboration's own labelling: tips 0,1,2 with vertex 0 adjacent to 6 and 8, plus the
    three level-1 sub-gaskets, which is what 'local' has to be defined against."""
    G = nx.Graph()
    groups: list = []

    def rec(v1, v2, v3, d, tag=None):
        if d == 0:
            for x, y in [(v1, v2), (v2, v3), (v3, v1)]:
                G.add_edge(x, y)
                groups.append((tuple(sorted((x, y))), tag))
            return
        m12 = max(G.nodes) + 1
        m23, m31 = m12 + 1, m12 + 2
        G.add_nodes_from([m12, m23, m31])
        rec(v1, m12, m31, d - 1, 0 if tag is None else tag)
        rec(v2, m23, m12, d - 1, 1 if tag is None else tag)
        rec(v3, m31, m23, d - 1, 2 if tag is None else tag)

    G.add_nodes_from([0, 1, 2])
    rec(0, 1, 2, 2)
    sub: dict = {}
    for e_, t in groups:
        sub.setdefault(t, set()).add(e_)
    return G, sub


def depths(iso: bool, edges, target, local_idx, extra=None, step=0.02):
    """Global and local valley depth over s in [0,3]. `extra` appends a bond that is not in the
    graph -- the configuration our own impurity work used, kept so its figure can be checked."""
    Z = SG._z(15)
    idx = np.nonzero(Z.sum(axis=0) == 1)[0]
    zi = Z[:, idx].astype(np.float64)
    full = edges + ([extra] if extra else [])
    g, l = [], []
    for s in np.arange(0.0, 3.0 + step / 2, step):
        c = [1.0] * len(edges) + ([float(s)] if extra else [])
        if not extra:
            c[target] = float(s)
        h = SG._H(15, full, c, Z, iso).tocsr()[idx][:, idx]
        w, V = eigsh(h, k=6, which="SA", tol=0, maxiter=300000,
                     v0=np.random.default_rng(3).standard_normal(idx.size))
        p = V[:, np.argsort(w)][:, 0] ** 2
        corr = np.array([p @ (zi[i] * zi[j]) for i, j in edges])
        g.append(float(corr.std()))
        l.append(float(corr[local_idx].std()))
    g, l = np.array(g), np.array(l)
    return float(g.max() - g.min()), float(l.max() - l.min())


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args(argv[1:])
    text = DOC.read_text(encoding="utf-8")

    if a.list:
        print("Receipt for %s\n" % DOC.relative_to(ROOT))
        print("RE-DERIVED HERE:")
        for s in ("−6.000000", "−16.921463", "0.143538", "0.144542", "0.263346", "0.276416",
                  "0.200462", "0.181144"):
            print("   %-14s %s" % (s, "present in the document" if s in text else "NOT IN THE DOCUMENT"))
        print("\nOUT OF REACH, and why:")
        for k, v in OUT_OF_REACH.items():
            print("   %-20s %s" % (k, v))
        return 0

    t0 = time.time()

    # 1 -- the two energies the README calls solid, in the model this toolchain actually computes
    e1, e2 = ground_energy(1), ground_energy(2)
    ck("L1 and L2 ground energies (XX+ZZ, exact diagonalisation)",
       abs(e1 + 6.000000) < 5e-6 and abs(e2 + 16.921463) < 5e-6
       and "−6.000000" in text and "−16.921463" in text,
       "L1 %.6f vs −6.000000 ; L2 %.6f vs −16.921463" % (e1, e2))

    # 2 -- the model-difference figures added in the 2026-08-18 correction block
    G, sub = _gasket_labelled()
    edges = sorted(tuple(sorted(x)) for x in G.edges())
    CE = (0, 6)
    near = {v for v in G if min(nx.shortest_path_length(G, v, CE[0]),
                                nx.shortest_path_length(G, v, CE[1])) <= 2}
    r2 = [k for k, (u, v) in enumerate(edges) if u in near and v in near]
    gi, li = depths(True, edges, edges.index(CE), r2)
    gx, lx = depths(False, edges, edges.index(CE), r2)
    ck("isotropic vs XX+ZZ, global and local (radius-2 neighbourhood, 12 of 27 edges)",
       len(r2) == 12 and abs(gi - 0.143538) < 5e-6 and abs(gx - 0.144542) < 5e-6
       and abs(li - 0.263346) < 5e-6 and abs(lx - 0.276416) < 5e-6
       and all(s in text for s in ("0.143538", "0.144542", "0.263346", "0.276416")),
       "global %.6f / %.6f ; local %.6f / %.6f over %d edges" % (gi, gx, li, lx, len(r2)))

    # 3 -- the bracket around 0.1902, under the definition the impurity code implies
    own = {t: [k for k, v in sub.items() if any(t in ed for ed in v)][0] for t in (0, 2)}
    l18 = [edges.index(x) for x in sorted(sub[own[0]] | sub[own[2]])]
    _, d18x = depths(False, edges, None, l18, extra=(0, 2))
    _, d18i = depths(True, edges, None, l18, extra=(0, 2))
    ck("the bracket around our unverified 0.1902 (18-edge local set, added (0,2) bond)",
       len(l18) == 18 and abs(d18x - 0.200462) < 5e-6 and abs(d18i - 0.181144) < 5e-6
       and d18i < 0.1902 < d18x and "treat 0.1902 as unverified" in text,
       "XX+ZZ %.6f, isotropic %.6f ; 0.1902 lies between and is marked unverified" % (d18x, d18i))

    # 4 -- the document must still SAY it cannot reach the rest
    ck("the figures this receipt cannot reach are named in the document, not silently skipped",
       all(k.split(" /")[0] in text for k in OUT_OF_REACH),
       "out of reach: %s" % ", ".join(OUT_OF_REACH))

    w = max(len(c[0]) for c in checks)
    print("Receipt for %s -- %d groups, %.0fs\n" % (DOC.relative_to(ROOT), len(checks), time.time() - t0))
    for name, ok, detail in checks:
        print("  [%s] %-*s\n        %s" % ("PASS" if ok else "FAIL", w, name, detail))
    bad = [c for c in checks if not c[1]]
    print("\n%d/%d verified. %d figures remain out of reach by design -- run --list to see why."
          % (len(checks) - len(bad), len(checks), len(OUT_OF_REACH)))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

# Legibility-budgeted memory — first step (v2), on the REAL vault.
# v1 showed the vault is deep supercritical (kappa=451, p_c=0.002) and global precision is flat.
# The lever is the hub structure: <k>=23 but <k^2>=10402 => a few notes link to everything.
# v2 tests the MECHANISM directly: (a) which notes are the hubs; (b) how kappa falls if we
# consolidate (demote) the top hubs; (c) LOCAL legibility = semantic precision of a note's DIRECT
# link-neighbours, bucketed by degree — are hubs the source of illegibility? Source: simulation on real data.
import json, re
import numpy as np
from pathlib import Path
from collections import defaultdict

cdir = Path("C:/Users/Danculus/agora/server/.semantic_cache")
VAULT = Path("C:/Users/Danculus/my-second-brain")
vecs = np.load(cdir / "vectors.npy")
meta = json.loads((cdir / "meta.json").read_text(encoding="utf-8"))
N = len(meta)
norms = np.linalg.norm(vecs, axis=1, keepdims=True); norms[norms == 0] = 1
V = vecs / norms

def base(p): return Path(p).stem.lower().strip()
by_base, by_title = {}, {}
for i, m in enumerate(meta):
    by_base.setdefault(base(m.get("path", "")), i)
    t = (m.get("title", "") or "").lower().strip()
    if t: by_title.setdefault(t, i)

LINK = re.compile(r"\[\[([^\]\|#]+)")
adj = defaultdict(set)
for i, m in enumerate(meta):
    try:
        txt = (VAULT / m.get("path", "")).read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue
    for tgt in LINK.findall(txt):
        key = tgt.strip().lower()
        j = by_base.get(key) or by_title.get(key) or by_base.get(key.split("/")[-1])
        if j is not None and j != i:
            adj[i].add(j); adj[j].add(i)

deg = np.array([len(adj[i]) for i in range(N)])
linked = deg > 0

def kappa_of(degs):
    d = degs[degs > 0].astype(float)
    return (d**2).mean() / d.mean()

k_full = kappa_of(deg)
print(f"notes={N} linked={int(linked.sum())} <k>={deg[linked].mean():.2f} kappa_full={k_full:.1f}")

# (a) top hubs
order = np.argsort(-deg)
print("\nTOP 12 HUBS (degree):")
for i in order[:12]:
    print(f"  {deg[i]:5d}  {meta[i].get('title','')[:55]:55s} {meta[i].get('path','')[:40]}")

# (b) consolidate top hubs: recompute kappa after removing top-X% highest-degree nodes' edges
def kappa_after_demote(frac):
    cut = int(frac * linked.sum())
    demote = set(order[:cut].tolist())
    d2 = np.zeros(N)
    for i in range(N):
        if i in demote: continue
        d2[i] = sum(1 for j in adj[i] if j not in demote)
    return kappa_of(d2), cut

print("\nCONSOLIDATION (demote top-degree hubs) -> coupling:")
print(f"  full:            kappa={k_full:8.1f}")
for f in (0.001, 0.005, 0.01, 0.05, 0.10):
    k, cut = kappa_after_demote(f)
    print(f"  demote top {100*f:4.1f}% ({cut:4d} notes): kappa={k:8.1f}   (x{k_full/k:.1f} lower)")

# (c) LOCAL legibility: mean cosine of a note's DIRECT neighbours, bucketed by degree
rng = np.random.default_rng(3)
def local_prec(i):
    nb = list(adj[i])
    if not nb: return None
    if len(nb) > 40: nb = list(rng.choice(nb, 40, replace=False))
    return float(np.mean(V[i] @ V[nb].T))

buckets = {"deg 1-3": [], "deg 4-10": [], "deg 11-30": [], "deg 31-100": [], "deg >100": []}
def bk(d):
    return ("deg 1-3" if d<=3 else "deg 4-10" if d<=10 else "deg 11-30" if d<=30
            else "deg 31-100" if d<=100 else "deg >100")
samp = [i for i in range(N) if linked[i]]
rng.shuffle(samp)
for i in samp[:1500]:
    p = local_prec(i)
    if p is not None: buckets[bk(deg[i])].append(p)
print("\nLOCAL legibility (semantic precision of direct link-neighbours) by node degree:")
for b, vs in buckets.items():
    if vs: print(f"  {b:10s} n={len(vs):4d}  mean cos = {np.mean(vs):.3f}")
print("\n=> if precision falls with degree, hubs are the illegibility source: their links are"
      "\n   indiscriminate, so consolidating/demoting them restores a navigable (legible) graph.")

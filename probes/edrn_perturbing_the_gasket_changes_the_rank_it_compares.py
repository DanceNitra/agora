import numpy as np, networkx as nx
from scipy.sparse import csr_matrix, coo_matrix
from scipy.sparse.linalg import eigsh

def gasket(level):
    nv, E, C = 3, [(0,1),(1,2),(0,2)], (0,1,2)
    for _ in range(level):
        off=[0,nv,2*nv]
        E2=[(a+o,b+o) for o in off for (a,b) in E]
        par=list(range(3*nv))
        def find(x):
            while par[x]!=x: par[x]=par[par[x]]; x=par[x]
            return x
        def uni(a,b):
            ra,rb=find(a),find(b)
            if ra!=rb: par[max(ra,rb)]=min(ra,rb)
        A=[c+off[0] for c in C]; B=[c+off[1] for c in C]; D=[c+off[2] for c in C]
        uni(A[1],B[0]); uni(A[2],D[0]); uni(B[2],D[1])
        roots=sorted({find(x) for x in range(3*nv)}); idx={r:i for i,r in enumerate(roots)}
        rel=lambda x: idx[find(x)]
        E=sorted({tuple(sorted((rel(a),rel(b)))) for (a,b) in E2})
        C=(rel(A[0]),rel(B[1]),rel(D[2])); nv=len(roots)
    return nv,E,C

N, EDGES, _ = gasket(2)
DIM = 1 << N
s = np.arange(DIM)

def build(weights):
    rows,cols,vals=[],[],[]
    for (a,b),w in zip(EDGES,weights):
        ma,mb=1<<(N-1-a),1<<(N-1-b)
        za=np.where((s&ma)>0,1.0,-1.0); zb=np.where((s&mb)>0,1.0,-1.0)
        rows.append(s); cols.append(s); vals.append(w*za*zb)
        d=za!=zb; idx=s[d]
        rows.append(idx^ma^mb); cols.append(idx); vals.append(np.full(idx.size,2.0*w))
    r=np.concatenate(rows); c=np.concatenate(cols); v=np.concatenate(vals)
    return csr_matrix(coo_matrix((v,(r,c)),shape=(DIM,DIM)))

def degen(H,tol=1e-8):
    w,V=eigsh(H,k=10,which="SA",tol=0,maxiter=20000)
    o=np.argsort(w); w=w[o]; V=V[:,o]
    d=int(np.sum(w-w[0]<tol))
    return d, float(w[d]-w[0]), w[:6]

base=[1.0]*len(EDGES)
d0,g0,w0=degen(build(base))
print("UNPERTURBED gasket : degeneracy %d, gap %.6f" % (d0,g0))
for eps in (0.5, 0.1, 0.01, 0.001):
    wts=list(base); wts[0]=1.0+eps
    d,g,ws=degen(build(wts))
    print("  perturb edge %s by +%-6g : degeneracy %d, gap %.3e   E0 split %.3e"
          % (str(EDGES[0]), eps, d, g, float(ws[1]-ws[0])))
# a perturbation that keeps a mirror symmetry, for contrast
G=nx.Graph(); G.add_edges_from(EDGES)
print("\nCONCLUSION: if the rank changes under perturbation, the 2.27e-2 compares different objects.")

# ---- recorded run -------------------------------------------------------------------
# This probe was cited by name in two letters to collaborators before it wrote anything a
# reader could check. It printed to stdout and stopped there, so `main` carried the script
# and no record of the run. The block below re-uses the functions above, changes no
# measurement, and writes the receipt beside the file under the convention every other
# probe here follows.
import json as _json, os as _os
_rep = {"N": N, "n_edges": len(EDGES), "dim": DIM, "tol": 1e-8,
        "unperturbed": {"degeneracy": d0, "gap": float(g0),
                        "levels": [float(x) for x in w0]},
        "perturbed": {}}
for _eps in (0.5, 0.1, 0.01, 0.001):
    _w = list(base); _w[0] = 1.0 + _eps
    _d, _g, _ws = degen(build(_w))
    _rep["perturbed"][str(_eps)] = {"edge": list(EDGES[0]), "degeneracy": _d,
                                    "gap": float(_g), "E0_split": float(_ws[1] - _ws[0]),
                                    "levels": [float(x) for x in _ws]}
_rep["rank_changes_under_perturbation"] = any(
    v["degeneracy"] != d0 for v in _rep["perturbed"].values())
_rep["ranks_seen"] = sorted({d0} | {v["degeneracy"] for v in _rep["perturbed"].values()})
print("MEASURED: unperturbed rank %d, perturbed rank(s) %s, rank changes: %s"
      % (d0, sorted({v["degeneracy"] for v in _rep["perturbed"].values()}),
         _rep["rank_changes_under_perturbation"]))
_out = _os.path.splitext(_os.path.abspath(__file__))[0] + ".result.json"
with open(_out, "w", encoding="utf-8") as _fh:
    _json.dump(_rep, _fh, indent=1)
print("wrote", _os.path.basename(_out))

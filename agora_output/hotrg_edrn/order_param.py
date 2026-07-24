"""Proper, size-INTENSIVE order parameters for the contradiction-bond valley, replacing the raw
std-over-all-edges (which dilutes with size). Decompose the bond-correlation field C_a = <sigma^z_i
sigma^z_j> (manifold-averaged) into:
  - LOCAL(defect):  std over base bonds inside a FIXED radius-R corner neighborhood of the defect bond
                    (0,2). By self-similarity of the gasket this neighborhood is structurally identical
                    at every level L>=2 -> truly intensive, thermodynamic-limit definition.
  - BULK:           variance-per-bond over the far bonds (intensive, has an N->inf limit). If the valley
                    is a bulk thermodynamic feature it lives here; if only local, it is a defect mode.
Shared C_a computation: ED (manifold projector) for L1/L2, DMRG for L3. This module: ED path + the
neighborhood self-similarity check across L1/L2/L3.
"""
import os
os.environ["OMP_NUM_THREADS"]="12"
import numpy as np, networkx as nx
from scipy.sparse.linalg import eigsh
from reconstruct_scaling_ED import sierpinski_graph, make_ops

STR = np.linspace(0.0, 3.0, 13)
DEGTOL = 1e-2
DEFECT = (0,2)
R = 2

def local_bulk_bonds(G, R=R, defect=DEFECT):
    base=list(G.edges())
    d0=nx.single_source_shortest_path_length(G, defect[0])
    d2=nx.single_source_shortest_path_length(G, defect[1])
    def near(n): return min(d0.get(n,99), d2.get(n,99))<=R
    local=[(i,j) for (i,j) in base if near(i) and near(j)]
    bulk =[(i,j) for (i,j) in base if not (near(i) and near(j))]
    return base, local, bulk

def manifold_corrs(level):
    """Return dict s-> per-bond manifold-averaged C_a (aligned to base edge order), ED."""
    G=sierpinski_graph(level); N=G.number_of_nodes()
    base,local,bulk=local_bulk_bonds(G)
    DIM,H_build,szsz=make_ops(N)
    Hbase=H_build([(i,j,1.0) for (i,j) in base]); Hedge=H_build([(DEFECT[0],DEFECT[1],1.0)])
    Pmap={(i,j):szsz(i,j) for (i,j) in base}
    v0=None; out={}
    for s in STR:
        H=Hbase+s*Hedge
        for k in (16,32,48):
            kk=min(k,DIM-2); E,V=eigsh(H,k=kk,which='SA',tol=0,v0=v0,maxiter=50000)
            o=np.argsort(E); E=E[o]; V=V[:,o]
            deg=int(np.sum(np.abs(E-E[0])<DEGTOL)); deg=max(1,min(deg,V.shape[1]))
            if (deg<V.shape[1]) and (E[deg]-E[deg-1]>5*DEGTOL): break
        v0=V[:,0]; Pm=np.abs(V[:,:deg])**2
        out[s]={e: float(Pmap[e]@Pm.mean(axis=1)) if False else float((Pmap[e]@Pm).mean()) for e in base}
    return G, base, local, bulk, out

def valley(vals_by_s, bonds):
    curve=np.array([np.std([vals_by_s[s][e] for e in bonds]) for s in STR])
    imin=int(np.argmin(curve))
    depth=float(min(curve[0],curve[-1])-curve[imin]) if 0<imin<len(curve)-1 else 0.0
    # clean depth vs right shoulder (skip s=0 degenerate endpoint)
    c2=curve[1:]; im2=int(np.argmin(c2)); sh=float(np.mean(c2[-3:])); cdepth=float(sh-c2[im2])
    return curve, depth, cdepth, float(STR[1+im2])

if __name__=="__main__":
    print("=== self-similarity check: local/bulk bond counts (R=2 around defect (0,2)) ===")
    for lv in (1,2,3):
        G=sierpinski_graph(lv); base,local,bulk=local_bulk_bonds(G)
        print(f"  L{lv}: N={G.number_of_nodes():>2} |base|={len(base):>2} |local|={len(local):>2} |bulk|={len(bulk):>2}")
    print("\n=== ED order-parameter valleys (L1, L2) ===")
    for lv in (1,2):
        G,base,local,bulk,vals=manifold_corrs(lv)
        cg,dg,cdg,sg=valley(vals,base)
        cl,dl,cdl,sl=valley(vals,local)
        results=[("GLOBAL(all)",base,cg,cdg,sg),("LOCAL(defect)",local,cl,cdl,sl)]
        if bulk:
            cb,db,cdb,sb=valley(vals,bulk); results.append(("BULK(far)",bulk,cb,cdb,sb))
        print(f"\n L{lv} (N={G.number_of_nodes()}):")
        for name,bonds,curve,cdepth,smin in results:
            print(f"   {name:14} |bonds|={len(bonds):>2} clean_depth={cdepth:.4f} min_at={smin:.2f}  curve[1:]={np.round(curve[1:],3).tolist()}")

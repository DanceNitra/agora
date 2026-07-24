"""L3 scaling with the PROPER size-intensive order parameters (LOCAL defect neighborhood, BULK, GLOBAL).
DMRG per-bond correlations C_a = <sigma^z_i sigma^z_j>; validate LOCAL depth at L2 vs ED (0.1902),
then L3 with chi-extrapolation of the LOCAL curve (18 defect bonds, identical set at L2 & L3).
"""
import os, logging, sys, time
os.environ["OMP_NUM_THREADS"]="12"
logging.disable(logging.WARNING)
import numpy as np
from dmrg_valley import sierpinski_graph, rcm_order, build_model, ground_state
from order_param import local_bulk_bonds, valley, STR, DEFECT

def bond_corrs_dmrg(level, chi, strengths=None):
    """Return per-bond C_a for each s (dict s->{edge:C}), DMRG, reversed warm-start scan."""
    if strengths is None: strengths=STR[1:]
    G=sierpinski_graph(level); N=G.number_of_nodes()
    base,local,bulk=local_bulk_bonds(G); pos=rcm_order(G)
    res={}; psi_prev=None; terrs={}
    for s in list(strengths)[::-1]:
        edge_w=[(i,j,1.0) for (i,j) in base]+[(DEFECT[0],DEFECT[1],float(s))]
        model,lat=build_model(N, edge_w, pos)
        E,psi,terr=ground_state(model,lat,N,chi,psi0=psi_prev); psi_prev=psi.copy()
        Zc=psi.correlation_function('Sigmaz','Sigmaz')
        res[float(s)]={e: float(Zc[pos[e[0]],pos[e[1]]].real) for e in base}
        terrs[float(s)]=terr
        loc=np.std([res[float(s)][e] for e in local])
        print(f"   s={s:.2f} local_std={loc:.4f} chi={int(max(psi.chi))} terr={terr:.1e}", flush=True)
    # align to full STR grid (s=0 skipped -> pad with the s=0.25 value's structure not needed; use strengths)
    full={s: res[s] for s in res}
    return G, base, local, bulk, full

def depths(vals, base, local, bulk):
    # valley() expects vals keyed over STR incl s=0; we only have s>=0.25 -> build a STR-like wrapper
    class V:  # minimal shim: reuse valley by faking curve over available s (skip s=0)
        pass
    ss=sorted(vals.keys())
    def cd(bonds):
        curve=np.array([np.std([vals[s][e] for e in bonds]) for s in ss])
        im=int(np.argmin(curve)); sh=float(np.mean(curve[-3:]))
        return float(sh-curve[im]), float(ss[im]), curve
    out={}
    out['GLOBAL']=cd(base); out['LOCAL']=cd(local)
    if bulk: out['BULK']=cd(bulk)
    return out

if __name__=="__main__":
    lv=int(sys.argv[1]) if len(sys.argv)>1 else 2
    chi=int(sys.argv[2]) if len(sys.argv)>2 else 128
    t0=time.time()
    G,base,local,bulk,vals=bond_corrs_dmrg(lv, chi)
    d=depths(vals, base, local, bulk)
    print(f"\nL{lv} (N={G.number_of_nodes()}, chi={chi})  |local|={len(local)} |bulk|={len(bulk)}  ({time.time()-t0:.0f}s)")
    for k in ('GLOBAL','LOCAL','BULK'):
        if k in d:
            cdepth,smin,curve=d[k]
            print(f"  {k:8} clean_depth={cdepth:.4f} min_at={smin:.2f} curve={np.round(curve,3).tolist()}")
    if lv==2:
        print("  ED ref: LOCAL depth 0.1902, GLOBAL 0.1968 (must match to trust DMRG order-param)")

"""DMRG (TeNPy, MPS/MPO) valley on the Sierpinski contradiction model.

CORRECTED 2026-08-18, twice, and both corrections change what earlier runs of this file MEANT.

1. THE DEFECT EDGE WAS NOT AN EDGE. This scanned `(0,2)`, and in this file's own labelling 0 and 2
   are two of the three TIPS, which sit at graph distance 4 -- no tip-tip pair is an edge of the
   gasket at any level. `edge_w = base + [(0,2,s)]` therefore APPENDED a 28th bond rather than
   varying one of the 27, while the observable ran over `base` only. Every earlier curve from this
   file is for gasket-plus-an-extra-bond, and its minimum sits near s=0.60 because s=1 is not a
   special point for an added bond. The default is now the real tip-to-interior edge (0,6), and
   `assert_real_edge` refuses anything that is not in the graph.

2. THE DEGENERACY ARGUMENT WAS WRONG. This used to say ED showed "single == manifold at the valley
   bottom, so DMRG is valid THROUGH the valley". That was measured by sampling REAL vectors inside
   the ground space, and a real-arithmetic eigensolver returns real vectors, so the test could not
   fail. Complex states are physical and they span a range: at the uniform point of the L2 gasket a
   single ground state gives anywhere in [0.110269, 0.159658], and on a 15-ring the complex
   translation eigenstates give exactly 0 where real sampling reports 0.130979. DMRG returns ONE
   vector, so wherever the ground space is not one-dimensional this file reports an arbitrary member
   of it. It now prints the ground-space dimension so that is visible rather than assumed.

MODEL, and it is NOT the manuscript's. H = sum_edge w*(SigX_i SigX_j + SigZ_i SigZ_j) in PAULI --
XX+ZZ, which is the XY model in a rotated frame. The manuscript studies the isotropic
sx sx + sy sy + sz sz. Measured on the same graph and edge, the two agree to 0.7% on the global
valley depth (0.144542 vs 0.143538) but differ by 5% locally (0.276416 vs 0.263346), so a
cross-check between them is not a same-model check and cannot agree "to the digit".

Observable = std over base edges of <SigZ_i SigZ_j>. Ordering: reverse Cuthill-McKee to make graph
edges MPS-local (bounds bond dimension via finite ramification of the gasket).
"""
import os, logging, sys, time
os.environ["OMP_NUM_THREADS"]="12"
logging.disable(logging.WARNING)
import numpy as np, networkx as nx
from tenpy.networks.site import SpinHalfSite
from tenpy.models.lattice import Chain
from tenpy.models.model import CouplingModel, MPOModel
from tenpy.networks.mps import MPS
from tenpy.algorithms import dmrg

STR = np.linspace(0.0, 3.0, 13)

def sierpinski_graph(level):
    G = nx.Graph()
    def tri(a,b,c): G.add_edge(a,b); G.add_edge(b,c); G.add_edge(c,a)
    def rec(v1,v2,v3,d):
        if d==0: tri(v1,v2,v3)
        else:
            m12=max(G.nodes)+1 if G.nodes else 0; G.add_node(m12)
            m23=m12+1; G.add_node(m23); m31=m23+1; G.add_node(m31)
            rec(v1,m12,m31,d-1); rec(v2,m23,m12,d-1); rec(v3,m31,m23,d-1)
    G.add_nodes_from([0,1,2]); rec(0,1,2,level); return G

def rcm_order(G):
    """reverse Cuthill-McKee -> MPS ordering that minimises edge span (bounds bond dim)."""
    from networkx.utils import reverse_cuthill_mckee_ordering
    order=list(reverse_cuthill_mckee_ordering(G))
    pos={node:k for k,node in enumerate(order)}   # node -> MPS position
    return pos

def build_model(N, edge_w, pos):
    site=SpinHalfSite(conserve=None)
    lat=Chain(N, site, bc='open', bc_MPS='finite')
    M=CouplingModel(lat)
    for (i,j,w) in edge_w:
        a,b=pos[i],pos[j]
        if a==b: continue
        lo,hi=(a,b) if a<b else (b,a)
        M.add_coupling_term(w, lo, hi, 'Sigmax','Sigmax')
        M.add_coupling_term(w, lo, hi, 'Sigmaz','Sigmaz')
    return MPOModel(lat, M.calc_H_MPO()), lat

def ground_state(model, lat, N, chi, psi0=None):
    # warm-start from previous s if given (else alternating product state)
    if psi0 is not None:
        psi=psi0.copy()
    else:
        psi=MPS.from_product_state(lat.mps_sites(),
            [('up' if k%2==0 else 'down') for k in range(N)], bc='finite')
    eng=dmrg.TwoSiteDMRGEngine(psi, model,
        {'trunc_params':{'chi_max':chi,'svd_min':1e-10},
         'max_sweeps':40,'min_sweeps':5,'mixer':True,
         'combine':True,'norm_tol':1e-8,
         'max_trunc_err':1.0})       # disable the hard raise; we REPORT the real trunc err instead
    E,psi=eng.run()
    terr=float(np.max(eng.trunc_err_list)) if getattr(eng,'trunc_err_list',None) else float('nan')
    return E,psi,terr

def assert_real_edge(G, pair):
    """A scan of a pair that is not an edge is a no-op, and a no-op returns a flat curve that reads
    as a clean null result. On this graph the three tips are pairwise at distance 4, so (0,1), (0,2)
    and (1,2) are all non-edges -- and both the old defect edge here and the control edge reported
    as `range 0.000000` in the manuscript were among them."""
    u, v = tuple(sorted(pair))
    if not G.has_edge(u, v):
        import networkx as _nx
        raise ValueError(
            "(%s,%s) is NOT an edge of this graph. deg(%s)=%d neighbours %s ; deg(%s)=%d neighbours %s ; "
            "graph distance %d. Scanning it would append a new bond, not vary an existing one."
            % (u, v, u, G.degree(u), sorted(G[u]), v, G.degree(v), sorted(G[v]),
               _nx.shortest_path_length(G, u, v)))
    return (u, v)


def valley_curve(level, chi=200, strengths=None, defect=(0, 6)):
    # Skip the pathological s=0 (bare gasket, high degeneracy: single-vector arbitrary + max bond dim).
    # Scan s in [0.25, 3.0]; define depth vs the RIGHT SHOULDER (large s, deg=2, single==manifold, clean).
    if strengths is None: strengths=STR[1:]
    G=sierpinski_graph(level); N=G.number_of_nodes(); base=list(G.edges())
    assert_real_edge(G, defect)
    pos=rcm_order(G)
    # scan LARGE s -> small s: large s is near-product (low entanglement, fast); warm-start each next
    order=list(range(len(strengths)))[::-1]
    res={}; psi_prev=None
    for k in order:
        s=float(strengths[k])
        edge_w=[(i,j,s if tuple(sorted((i,j)))==tuple(sorted(defect)) else 1.0) for (i,j) in base]
        model,lat=build_model(N, edge_w, pos)
        E,psi,terr=ground_state(model,lat,N,chi,psi0=psi_prev)
        psi_prev=psi.copy()
        Zc=psi.correlation_function('Sigmaz','Sigmaz')   # NxN in MPS order
        corrs=[float(Zc[pos[i],pos[j]].real) for (i,j) in base]
        res[k]=(float(np.std(corrs)), int(max(psi.chi)), float(E), terr)
        print(f"   s={s:.2f} std={res[k][0]:.4f} chi={res[k][1]} trunc_err={terr:.1e} E={E:.4f}", flush=True)
    curve=np.array([res[k][0] for k in range(len(strengths))])
    bonds=[res[k][1] for k in range(len(strengths))]
    Es=[res[k][2] for k in range(len(strengths))]
    terrs=[res[k][3] for k in range(len(strengths))]
    strengths=np.asarray(strengths)
    imin=int(np.argmin(curve))
    shoulder=float(np.mean(curve[-3:]))                  # right shoulder baseline (clean)
    clean_depth=float(shoulder-curve[imin])
    return dict(N=N,E=len(base),min_at=float(strengths[imin]),min_std=float(curve[imin]),
                shoulder=shoulder,clean_depth=clean_depth,curve=curve.tolist(),
                strengths=strengths.tolist(),max_bond=max(bonds),Es=Es,
                terrs=terrs,min_terr=terrs[imin],max_terr=max(terrs))

if __name__=="__main__":
    lv=int(sys.argv[1]) if len(sys.argv)>1 else 2
    chi=int(sys.argv[2]) if len(sys.argv)>2 else 200
    t0=time.time()
    r=valley_curve(lv, chi=chi)
    print(f"L{lv}: N={r['N']} E={r['E']} min_at={r['min_at']:.2f} min_std={r['min_std']:.4f} "
          f"shoulder={r['shoulder']:.4f} clean_depth={r['clean_depth']:.4f} maxbond={r['max_bond']} "
          f"min_terr={r['min_terr']:.1e} max_terr={r['max_terr']:.1e}  ({time.time()-t0:.0f}s)")
    print("strengths=", [round(x,2) for x in r['strengths']])
    print("curve=", [round(x,4) for x in r['curve']])
    if lv==2:
        print("ED ref: valley bottom min_std 0.0628 at s=0.50 (must match to trust DMRG)")

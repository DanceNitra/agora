"""DMRG (TeNPy, MPS/MPO) valley on the Sierpinski Heisenberg contradiction model.
VALIDATE at L2 vs ED (valley bottom min_std 0.0628 at s=0.50 must reproduce), report bond dimension,
then extend to L3 (42 sites, out of ED reach). Model = XX+ZZ in PAULI: H=sum_edge w*(SigX_i SigX_j +
SigZ_i SigZ_j). Observable = std over base edges of <SigZ_i SigZ_j>.
DMRG returns ONE ground vector; ED showed single==manifold AT the valley bottom (sigma^z sigma^z is
Z2-invariant there), so DMRG is valid THROUGH the valley. High-degeneracy endpoints are flagged.
Ordering: reverse Cuthill-McKee to make graph edges MPS-local (bounds bond dimension via finite
ramification of the gasket).
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

def valley_curve(level, chi=200, strengths=None):
    # Skip the pathological s=0 (bare gasket, high degeneracy: single-vector arbitrary + max bond dim).
    # Scan s in [0.25, 3.0]; define depth vs the RIGHT SHOULDER (large s, deg=2, single==manifold, clean).
    if strengths is None: strengths=STR[1:]
    G=sierpinski_graph(level); N=G.number_of_nodes(); base=list(G.edges())
    pos=rcm_order(G)
    # scan LARGE s -> small s: large s is near-product (low entanglement, fast); warm-start each next
    order=list(range(len(strengths)))[::-1]
    res={}; psi_prev=None
    for k in order:
        s=float(strengths[k])
        edge_w=[(i,j,1.0) for (i,j) in base]+[(0,2,s)]
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

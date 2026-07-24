"""FEASIBILITY GATE for the impurity-explicit RG, BEFORE building the full recursive machinery.
Core hypothesis: the local defect observable is recovered if the defect NEIGHBORHOOD is kept explicit and
only the FAR bath is truncated. Test at L2: truncate ONLY intB (sub-block B's interior = tip1's sub-gasket,
farthest from the defect tips 0,2), keep {m12,m23,m31,intA,intC} explicit; does the valley depth stay ~0.1902
as chi_B -> small? If YES the impurity approach WORKS (worth the multi-hour build); if it collapses like the
uniform truncation (~0.04), the approach is doomed and we stop.
"""
import numpy as np, scipy.sparse as sp, networkx as nx
from numpy.linalg import eigh
from hotrg import embed, SX, SZ
from hotrg_obs import block0, _ground, defect_bonds

def combine_intB(A,B,C, chiB=None):
    """L2 combine but truncating ONLY the intB factor (factor 7) to chiB; everything else kept explicit."""
    fd=[2,2,2,2,2,2,A['d'],B['d'],C['d']]; posA=[0,3,5,6]; posB=[1,4,3,7]; posC=[2,5,4,8]; D=int(np.prod(fd))
    H=(embed(A['H'],posA,fd)+embed(B['H'],posB,fd)+embed(C['H'],posC,fd)).tocsr()
    E0,low=_ground(H)
    dB=B['d']
    if chiB is None or chiB>=dB:
        W=sp.identity(D,format='csr'); dnew_int=int(np.prod(fd[3:]))
        # no truncation -> W is identity on the interior; but we work with full block. Build P=I.
        Wb=np.eye(dB)
    else:
        # RDM of the intB factor (factor 7): trace out all other factors from the ground manifold
        # reshape ground states to isolate factor 7. factor dims fd; factor 7 has dim dB.
        rhoB=np.zeros((dB,dB))
        for j in range(low.shape[1]):
            psi=np.asarray(low[:,j]).reshape(fd)                 # 9-factor tensor
            psi7=np.moveaxis(psi,7,0).reshape(dB,-1)             # (dB, rest)
            rhoB+=psi7@psi7.T
        wv,U=eigh(rhoB); idx=np.argsort(wv)[::-1][:chiB]; Wb=U[:,idx]
    # build the projector P = identity on factors 0-6,8, Wb on factor 7
    # apply as a factored operator: reshape and contract factor 7 with Wb
    dims=fd
    def project_state(v):
        t=v.reshape(dims); t=np.moveaxis(t,7,0)                  # (dB, rest)
        t=Wb.T@t.reshape(dB,-1)                                  # (chiB, rest)
        return t                                                 # keep as (chiB, rest) flat later
    # Instead of projecting H (expensive), build the reduced block Hamiltonian + observables by projecting
    # the full ground states? No — we need the reduced block to add the defect and re-diagonalize per s.
    # Build reduced-space operators via the isometry Piso (D x Dnew) with Wb on factor 7.
    newfd=list(fd); newfd[7]=Wb.shape[1]; Dnew=int(np.prod(newfd))
    # isometry as sparse: kron structure I(before 7) x Wb x I(after 7). factor 7 is between factors 0-6 and 8.
    dbefore=int(np.prod(fd[:7])); dafter=int(np.prod(fd[8:]))
    Piso=sp.kron(sp.identity(dbefore), sp.kron(sp.csr_matrix(Wb), sp.identity(dafter)))  # D x Dnew
    Hn=(Piso.T@H@Piso).tocsr()
    # corners + defect ops in reduced space
    cx0=(Piso.T@embed(SX,[0],fd)@Piso).tocsr(); cz0=(Piso.T@embed(SZ,[0],fd)@Piso).tocsr()
    cx2=(Piso.T@embed(SX,[2],fd)@Piso).tocsr(); cz2=(Piso.T@embed(SZ,[2],fd)@Piso).tocsr()
    # observables: project each tracked obs edge op
    obs={e:(Piso.T@embed(op,posA if False else _obs_pos(e,A,B,C,posA,posB,posC),fd)@Piso) for e in []}  # placeholder
    return dict(Hn=Hn,cx0=cx0,cz0=cz0,cx2=cx2,cz2=cz2,fd=newfd), A,B,C

# simpler: reuse hotrg_obs to build the FULL L2 block (chi=None) with obs, then truncate intB on THAT.
from hotrg_obs import combine as combine_full, build as build_full

def gate_L2(chiB_list=(1,2,4,8)):
    # full L2 block (exact) with tracked obs
    A,_=build_full(1,chi=None)                                   # L1 block
    fd=[2,2,2,2,2,2,A['d'],A['d'],A['d']]; posA=[0,3,5,6]; posB=[1,4,3,7]; posC=[2,5,4,8]
    H=(embed(A['H'],posA,fd)+embed(A['H'],posB,fd)+embed(A['H'],posC,fd)).tocsr()
    E0,low=_ground(H)
    dB=A['d']
    # build full L2 obs block via combine_full to get obs + edges + cnode + corners (chi=None)
    L2,_=combine_full(A,A,A,chi=None)
    bonds,(d0,d2)=defect_bonds(L2)
    strengths=np.linspace(0.25,3.0,12)
    print(f"gate: |defect bonds|={len(bonds)}  dB(intB)={dB}")
    for chiB in chiB_list:
        # isometry truncating factor 7 (intB) to chiB, identity elsewhere
        if chiB>=dB: Wb=np.eye(dB)
        else:
            rhoB=np.zeros((dB,dB))
            for j in range(low.shape[1]):
                psi=np.asarray(low[:,j]).reshape(fd); p7=np.moveaxis(psi,7,0).reshape(dB,-1); rhoB+=p7@p7.T
            wv,U=eigh(rhoB); Wb=U[:,np.argsort(wv)[::-1][:chiB]]
        dbefore=int(np.prod(fd[:7])); dafter=int(np.prod(fd[8:]))
        Piso=sp.kron(sp.identity(dbefore),sp.kron(sp.csr_matrix(Wb),sp.identity(dafter))).tocsr()
        Hn=(Piso.T@L2['H']@Piso).tocsr()
        cx0=(Piso.T@L2['corners'][0][0]@Piso); cz0=(Piso.T@L2['corners'][0][1]@Piso)
        cx2=(Piso.T@L2['corners'][2][0]@Piso); cz2=(Piso.T@L2['corners'][2][1]@Piso)
        Hdef=(cx0@cx2+cz0@cz2).tocsr()
        obsR={e:(Piso.T@op@Piso).tocsr() for e,op in L2['obs'].items()}
        curve=[]
        for s in strengths:
            Hs=(Hn+float(s)*Hdef).tocsr(); _,lo=_ground(Hs)
            def g(b): return obsR[b] if b in obsR else obsR[(b[1],b[0])]
            vals=[np.mean([float((lo[:,k].conj().T@(g(b)@lo[:,k])).real) for k in range(lo.shape[1])]) for b in bonds]
            curve.append(float(np.std(vals)))
        curve=np.array(curve); im=int(np.argmin(curve)); depth=float(np.mean(curve[-3:])-curve[im])
        print(f"  chiB={chiB}: valley_depth={depth:.4f} min_at={strengths[im]:.2f}  (exact 0.1902)", flush=True)

if __name__=="__main__":
    gate_L2()

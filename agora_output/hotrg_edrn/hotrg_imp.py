"""Impurity-explicit fractal RG (gate-validated approach): the two defect tips (corner0, corner2) keep their
tip-branch explicit; the far bath truncates hard. Tracks per-edge sigma^z sigma^z obs in the tip branches so
the 18 defect-neighborhood correlations survive. GATE: L2 valley depth = 0.1902; then L3 at feasible chi.

Structure per combine(A,B,C): interior factors [m12(3),m23(4),m31(5),intA(6),intB(7),intC(8)].
- tip block (keeps corner0 explicit): A is the tip sub-branch. corner0=A.c0=v1; its adjacent m's are
  m12(=A.c1) and m31(=A.c2). KEEP {m12,m31,intA} explicit; TRUNCATE the far {m23,intB,intC} to chi.
- bath block: uniform truncation of the whole interior (reuse hotrg energy combine).
"""
import numpy as np, scipy.sparse as sp, networkx as nx
from numpy.linalg import eigh
from scipy.sparse.linalg import eigsh
from hotrg import embed, SX, SZ
from hotrg_obs import block0 as block0_obs, _ground, defect_bonds

# ---------- BATH: uniform-truncated block (H + corners only) ----------
def bath0():
    from hotrg import block0 as bH
    return bH()   # dict d,H,corners (sparse)

def bath_combine(A,B,C, chi):
    fd=[2,2,2,2,2,2,A['d'],B['d'],C['d']]; posA=[0,3,5,6]; posB=[1,4,3,7]; posC=[2,5,4,8]; D=int(np.prod(fd))
    H=(embed(A['H'],posA,fd)+embed(B['H'],posB,fd)+embed(C['H'],posC,fd)).tocsr()
    _,low=_ground(H); d_int=int(np.prod(fd[3:]))
    if chi>=d_int: W=np.eye(d_int)
    else:
        rho=np.zeros((d_int,d_int))
        for j in range(low.shape[1]): psi=np.asarray(low[:,j]).reshape(8,d_int); rho+=psi.T@psi
        wv,U=eigh(rho); W=U[:,np.argsort(wv)[::-1][:chi]]
    P=sp.csr_matrix(np.kron(np.eye(8),W))
    newc=[((P.T@embed(SX,[c],fd)@P).tocsr(),(P.T@embed(SZ,[c],fd)@P).tocsr()) for c in range(3)]
    return dict(d=W.shape[1],H=(P.T@H@P).tocsr(),corners=newc)

def bath(level, chi):
    b=bath0()
    for _ in range(level): b=bath_combine(b,b,b,chi)
    return b

# ---------- TIP: keeps corner0 branch explicit, tracks obs ----------
def _factored_iso(fd, near_facs, far_facs, Wfar):
    """Isometry on the 9-factor space: identity on `near_facs`, Wfar on the grouped `far_facs`.
    Returns sparse (D x Dnew) mapping via a permutation to group far factors, kron(I_near, Wfar), back."""
    n=len(fd); D=int(np.prod(fd))
    order=[f for f in range(n) if f not in far_facs]+list(far_facs)   # near... then far...
    dims=[fd[f] for f in order]
    dnear=int(np.prod([fd[f] for f in range(n) if f not in far_facs]))
    dfar=int(np.prod([fd[f] for f in far_facs]))
    Dnew=dnear*Wfar.shape[1]
    # M = I_dnear (x) Wfar  in the `order` layout
    M=sp.kron(sp.identity(dnear), sp.csr_matrix(Wfar), format='csr')  # (dnear*dfar) x (dnear*Wc)
    # permutation P_in: natural linear -> `order` linear (rows), and same on the reduced side for near part
    def permvec(dm):  # natural index (dims by factor 0..n-1) -> order-grouped index
        nat=np.ones(n,dtype=np.int64)
        for i in range(n-2,-1,-1): nat[i]=nat[i+1]*fd[i+1]
        # order strides
        ost=np.ones(n,dtype=np.int64)
        for i in range(n-2,-1,-1): ost[i]=ost[i+1]*fd[order[i+1]]
        idx=np.arange(D,dtype=np.int64); out=np.zeros(D,dtype=np.int64); tmp=idx.copy()
        digit=np.zeros((D,n),dtype=np.int64)
        for k in range(n-1,-1,-1): digit[:,k]=tmp%fd[k]; tmp//=fd[k]      # natural digits
        for k in range(n): out+=digit[:,order[k]]*ost[k]
        return out
    p=permvec(D)                                                       # natural -> order (input side, dim D)
    Pin=sp.csr_matrix((np.ones(D),(np.arange(D),p)),shape=(D,D))       # x_order = Pin @ x_natural
    # output side: order layout is [near..., Wc]; natural-out grouping = near factors in original order then far-reduced
    Iso_order=M                                                        # (D) x (Dnew) in order layout (rows=order input, cols=near+Wc)
    # map input natural -> order, apply Iso, output stays in (near-order, Wc); we keep Dnew basis as-is.
    return (Pin.T@Iso_order).tocsr(), Dnew                             # (D x Dnew): natural-in -> reduced

def tip0():
    return block0_obs()   # dict d,H,corners,obs,edges,cnode ; corner0 is the tip

def tip_combine(A, Bb, Cb, chi):
    """A = tip sub-branch (obs-tracked); Bb,Cb = bath blocks (H+corners). Keep {m12,m31,intA} explicit,
    truncate far {m23,intB,intC} to chi. Track obs from A (embedded via posA)."""
    fd=[2,2,2,2,2,2,A['d'],Bb['d'],Cb['d']]; posA=[0,3,5,6]; posB=[1,4,3,7]; posC=[2,5,4,8]; D=int(np.prod(fd))
    H=(embed(A['H'],posA,fd)+embed(Bb['H'],posB,fd)+embed(Cb['H'],posC,fd)).tocsr()
    E0,low=_ground(H)
    far=[4,7,8]                                                        # m23, intB, intC
    dfar=int(np.prod([fd[f] for f in far]))
    if chi>=dfar: Wfar=np.eye(dfar)
    else:
        rho=np.zeros((dfar,dfar))
        for j in range(low.shape[1]):
            psi=np.asarray(low[:,j]).reshape(fd); pf=np.moveaxis(psi,far,[0,1,2]).reshape(dfar,-1); rho+=pf@pf.T
        wv,U=eigh(rho); Wfar=U[:,np.argsort(wv)[::-1][:chi]]
    Iso,Dnew=_factored_iso(fd,None,far,Wfar)                           # D x Dnew
    Iso=sp.csr_matrix(Iso)
    Hn=(Iso.T@H@Iso).tocsr()
    newc=[((Iso.T@embed(SX,[c],fd)@Iso).tocsr(),(Iso.T@embed(SZ,[c],fd)@Iso).tocsr()) for c in range(3)]
    # obs + edges/nodes: only from A (the tip branch); relabel A's ids as-is (bath has no tracked nodes)
    obs={e:(Iso.T@embed(op,posA,fd)@Iso).tocsr() for e,op in A['obs'].items()}
    edges=list(A['edges']); cnode=[A['cnode'][0], -1, -2]             # only corner0 (tip) node is meaningful
    # the defect partner corner2 is provided by the OTHER tip branch at the top combine; here mark placeholder
    return dict(d=Dnew//8, H=Hn, corners=newc, obs=obs, edges=edges, cnode=cnode, tipnode=A['cnode'][0])

def tip(level, chi):
    b=tip0()
    bth=bath0()
    for L in range(1,level+1):
        b=tip_combine(b, bath(L-1,chi), bath(L-1,chi), chi)
    return b

if __name__=="__main__":
    # sanity: tip block builds + energy reasonable
    import time
    t=time.time(); T=tip(1,chi=8); print(f"tip(1) dim={8*T['d']} obs={len(T['obs'])} edges={len(T['edges'])} ({time.time()-t:.0f}s)")

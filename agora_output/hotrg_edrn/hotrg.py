"""Fractal corner-space real-space RG for the Sierpinski-gasket Heisenberg (XX+ZZ) ground state.
Finite ramification: a sub-gasket couples to the rest ONLY through its 3 corner spins; the 3 corners are
always the original tip spins (stay dim-2); only the interior multiplet grows and is truncated to chi.
Block = (3 corner spins dim2) x (internal dim d): total 8d. Carries H (8d x 8d, sparse) + per-corner
Pauli sx,sz. Combine 3 blocks (shared corners -> interior), diagonalize, truncate the new interior to chi
via the (low-state-averaged) interior reduced density matrix, re-express H + the 3 outer-corner operators.
VALIDATION: exact recursion must give ED ground energy L1 -6.0, L2 -16.921463; truncated must converge to it.
"""
import numpy as np, scipy.sparse as sp
from scipy.sparse.linalg import eigsh, LinearOperator
from numpy.linalg import eigh
SX=sp.csr_matrix(np.array([[0,1],[1,0]],float)); SZ=sp.csr_matrix(np.array([[1,0],[0,-1]],float))

def _perm(order, full_dims):
    """current linear index (factors laid out in `order`) -> natural linear index (factors 0..n-1)."""
    n=len(full_dims); D=int(np.prod(full_dims))
    nat_stride=np.ones(n,dtype=np.int64)
    for i in range(n-2,-1,-1): nat_stride[i]=nat_stride[i+1]*full_dims[i+1]
    cur=[full_dims[i] for i in order]
    tmp=np.arange(D,dtype=np.int64); natlin=np.zeros(D,dtype=np.int64)
    for k in range(n-1,-1,-1):
        dig=tmp % cur[k]; tmp//=cur[k]; natlin+=dig*nat_stride[order[k]]
    return natlin

def embed(op, pos, full_dims):
    """Embed sparse `op` (on ordered factors `pos`) into the full factor space, identity elsewhere."""
    n=len(full_dims); D=int(np.prod(full_dims))
    other=[i for i in range(n) if i not in pos]
    d_ot=int(np.prod([full_dims[o] for o in other])) if other else 1
    M=sp.kron(op, sp.identity(d_ot), format='csr')           # factor order [pos..., other...]
    p=_perm(list(pos)+other, full_dims)
    Pm=sp.csr_matrix((np.ones(D),(p,np.arange(D))),shape=(D,D))
    return (Pm@M@Pm.T).tocsr()

def block0():
    dims=[2,2,2]
    def s(op,site): return embed(op,[site],dims)
    H=sp.csr_matrix((8,8))
    for (i,j) in [(0,1),(1,2),(2,0)]:
        H=H+s(SX,i)@s(SX,j)+s(SZ,i)@s(SZ,j)
    corners=[(s(SX,c),s(SZ,c)) for c in range(3)]
    return dict(d=1,H=H.tocsr(),corners=corners)

DEGTOL=1e-6
def _ground(H, kmax=8):
    """Return E0 and the DEGENERATE GROUND MANIFOLD (all states within DEGTOL of E0). The physically-correct,
    energy-optimal RDM basis — averaging over EXCITED states (the earlier nlow=8 mistake) biases the energy."""
    D=H.shape[0]
    if D<=256:
        w,v=eigh(H.toarray()); o=np.argsort(w); w=w[o]; v=v[:,o]
    else:
        kk=min(max(kmax,6),D-2); w,v=eigsh(H,k=kk,which='SA',tol=0,maxiter=50000); o=np.argsort(w); w=w[o]; v=v[:,o]
    E0=w[0]; deg=int(np.sum(w-E0<DEGTOL)); deg=max(1,min(deg,v.shape[1]))
    return E0, v[:,:deg]

def _apply(psi, op, factors, fd):
    """Apply dense `op` (on ordered `factors`) to state tensor psi (shape=fd). Matrix-free, O(dim) memory."""
    dims=[fd[f] for f in factors]; k=len(factors)
    opt=np.asarray(op).reshape(dims+dims)
    res=np.tensordot(opt, psi, axes=(list(range(k,2*k)), factors))   # op_out axes first, then psi remainder
    remaining=[ax for ax in range(len(fd)) if ax not in factors]
    cur=list(factors)+remaining
    return np.transpose(res, np.argsort(cur))

def combine(A,B,C, chi=None, nlow=8):
    dA,dB,dC=A['d'],B['d'],C['d']
    fd=[2,2,2, 2,2,2, dA,dB,dC]                              # v1 v2 v3 m12 m23 m31 intA intB intC
    posA=[0,3,5,6]; posB=[1,4,3,7]; posC=[2,5,4,8]           # each block's (c0,c1,c2,int)
    D=int(np.prod(fd)); shape=tuple(fd)
    HA=A['H'].toarray(); HB=B['H'].toarray(); HC=C['H'].toarray()
    def matvec(v):
        psi=v.reshape(shape)
        out=_apply(psi,HA,posA,fd)+_apply(psi,HB,posB,fd)+_apply(psi,HC,posC,fd)
        return out.reshape(-1)
    Hop=LinearOperator((D,D), matvec=matvec, rmatvec=matvec, dtype=float)
    v0=np.ones(D)/np.sqrt(D)                                 # FIXED start -> reproducible (gapless RDM cut is otherwise arbitrary)
    kk=min(8,D-2); w,V=eigsh(Hop,k=kk,which='SA',tol=0,maxiter=50000,v0=v0); o=np.argsort(w)
    w=w[o]; V=V[:,o]; E0=w[0]; deg=max(1,min(int(np.sum(w-E0<DEGTOL)),V.shape[1])); low=V[:,:deg]
    d_int=int(np.prod(fd[3:]))                               # interior = m12,m23,m31,intA,intB,intC
    if chi is None or chi>=d_int:
        W=np.eye(d_int); dnew=d_int
    else:
        rho=np.zeros((d_int,d_int))                          # ground-manifold interior RDM (trace out 3 corners)
        for j in range(low.shape[1]):
            psi=low[:,j].reshape(8,d_int); rho+=psi.T@psi
        wv,U=eigh(rho); idx=np.argsort(wv)[::-1][:chi]; W=U[:,idx]; dnew=chi
    # Project into (8 corners x dnew) WITHOUT materializing P: P=kron(I8,W). Loop columns; O(D) memory each.
    Wc=W.shape[1]; ncol=8*Wc
    def proj(vec): return (vec.reshape(8,d_int)@W).reshape(-1)      # (I8 (x) W)^T @ vec  -> length 8*Wc
    def pcol(b,j):
        v=np.zeros((8,d_int)); v[b,:]=W[:,j]; return v.reshape(-1)  # column (b,j) of kron(I8,W)
    Hn=np.empty((ncol,ncol))
    SXa=SX.toarray(); SZa=SZ.toarray()
    cxs=[np.empty((ncol,ncol)) for _ in range(3)]; czs=[np.empty((ncol,ncol)) for _ in range(3)]
    for b in range(8):
        for j in range(Wc):
            c=b*Wc+j; col=pcol(b,j); psi=col.reshape(shape)
            Hn[:,c]=proj(matvec(col))
            for cc in range(3):                              # outer corners = factors 0,1,2
                cxs[cc][:,c]=proj(_apply(psi,SXa,[cc],fd).reshape(-1))
                czs[cc][:,c]=proj(_apply(psi,SZa,[cc],fd).reshape(-1))
    newc=[(sp.csr_matrix(cxs[cc]), sp.csr_matrix(czs[cc])) for cc in range(3)]
    return dict(d=dnew, H=sp.csr_matrix(Hn), corners=newc), float(E0)

def build(level, chi=None, nlow=8):
    blk=block0(); E=None
    for L in range(1,level+1):
        blk,E=combine(blk,blk,blk,chi=chi,nlow=nlow)
    return blk,E

if __name__=="__main__":
    import sys,time
    print("ED ref: L1 E0=-6.000000  L2 E0=-16.921463")
    for chi in [None, 8, 16, 32]:
        t=time.time()
        try:
            _,E1=build(1,chi=chi); _,E2=build(2,chi=chi)
            print(f"chi={str(chi):>4}: L1 E0={E1:.6f}  L2 E0={E2:.6f}  ({time.time()-t:.0f}s)")
        except Exception as e:
            import traceback; traceback.print_exc(); break

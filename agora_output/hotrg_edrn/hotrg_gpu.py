"""GPU (torch) port of the fractal corner-space RG. Matrix-free matvec on GPU via torch.tensordot;
ground state via a full-reorthogonalization Lanczos (fixed v0 -> reproducible). VALIDATE L2 exact
(-16.921463) before trusting L3. fp64 for the validation gate."""
import numpy as np, torch, scipy.sparse as sp
DEV='cuda'; DT=torch.float64
SX=torch.tensor([[0,1],[1,0]],dtype=DT,device=DEV); SZ=torch.tensor([[1,0],[0,-1]],dtype=DT,device=DEV)
DEGTOL=1e-6

def _np_embed(op,pos,full_dims):
    n=len(full_dims); D=int(np.prod(full_dims)); other=[i for i in range(n) if i not in pos]
    d_ot=int(np.prod([full_dims[o] for o in other])) if other else 1
    M=sp.kron(sp.csr_matrix(op),sp.identity(d_ot),format='csr'); order=list(pos)+other
    nat=np.ones(n,dtype=np.int64)
    for i in range(n-2,-1,-1): nat[i]=nat[i+1]*full_dims[i+1]
    cur=[full_dims[i] for i in order]; tmp=np.arange(D,dtype=np.int64); natl=np.zeros(D,dtype=np.int64)
    for k in range(n-1,-1,-1):
        dig=tmp%cur[k]; tmp//=cur[k]; natl+=dig*nat[order[k]]
    Pm=sp.csr_matrix((np.ones(D),(natl,np.arange(D))),shape=(D,D)); return (Pm@M@Pm.T).toarray()

def block0():
    dims=[2,2,2]; sxn=np.array([[0,1],[1,0]],float); szn=np.array([[1,0],[0,-1]],float)
    H=np.zeros((8,8))
    for (i,j) in [(0,1),(1,2),(2,0)]:
        H+=_np_embed(sxn,[i],dims)@_np_embed(sxn,[j],dims)+_np_embed(szn,[i],dims)@_np_embed(szn,[j],dims)
    T=lambda M: torch.tensor(M,dtype=DT,device=DEV)
    return dict(d=1,H=T(H),corners=[(T(_np_embed(sxn,[c],dims)),T(_np_embed(szn,[c],dims))) for c in range(3)])

def _apply(psi, op, factors, fd):
    k=len(factors); dims=[fd[f] for f in factors]
    opt=op.reshape(dims+dims)
    res=torch.tensordot(opt, psi, dims=(list(range(k,2*k)), list(factors)))
    remaining=[ax for ax in range(len(fd)) if ax not in factors]
    return res.permute(*list(np.argsort(list(factors)+remaining)))

def lanczos(matvec, D, nev=8, m=80):
    Q=torch.zeros(m,D,dtype=DT,device=DEV); a=torch.zeros(m,dtype=DT,device=DEV); b=torch.zeros(m,dtype=DT,device=DEV)
    g=torch.Generator(device=DEV).manual_seed(0)            # seeded random start: generic overlap (ones is symmetry-orthogonal), reproducible
    q=torch.randn(D,generator=g,dtype=DT,device=DEV); q/=q.norm(); Q[0]=q; mm=m
    for k in range(m):
        w=matvec(Q[k]); ak=torch.dot(w,Q[k]); a[k]=ak; w=w-ak*Q[k]
        if k>0: w=w-b[k-1]*Q[k-1]
        w=w-Q[:k+1].T@(Q[:k+1]@w)                 # full reorthogonalization
        bk=w.norm(); b[k]=bk
        if bk<1e-10: mm=k+1; break
        if k+1<m: Q[k+1]=w/bk
    Tm=torch.diag(a[:mm])+torch.diag(b[:mm-1],1)+torch.diag(b[:mm-1],-1)
    ev,U=torch.linalg.eigh(Tm); idx=torch.argsort(ev)[:nev]
    R=(Q[:mm].T@U[:,idx]).contiguous(); del Q,Tm,U,a,b; return ev[idx].cpu().numpy(), R

def combine(A,B,C, chi=None, m=80):
    dA,dB,dC=A['d'],B['d'],C['d']
    fd=[2,2,2,2,2,2,dA,dB,dC]; posA=[0,3,5,6]; posB=[1,4,3,7]; posC=[2,5,4,8]
    D=int(np.prod(fd)); shape=tuple(fd); HA,HB,HC=A['H'],B['H'],C['H']
    def matvec(v):
        psi=v.reshape(shape)
        return (_apply(psi,HA,posA,fd)+_apply(psi,HB,posB,fd)+_apply(psi,HC,posC,fd)).reshape(-1)
    w,V=lanczos(matvec,D,nev=8,m=m); E0=float(w[0])
    deg=max(1,min(int(np.sum(w-w[0]<DEGTOL)),V.shape[1])); low=V[:,:deg]
    d_int=int(np.prod(fd[3:]))
    if chi is None or chi>=d_int:
        W=torch.eye(d_int,dtype=DT,device=DEV); dnew=d_int
    else:
        rho=torch.zeros(d_int,d_int,dtype=DT,device=DEV)
        for j in range(low.shape[1]):
            psi=low[:,j].reshape(8,d_int); rho=rho+psi.T@psi
        wv,U=torch.linalg.eigh(rho); idx=torch.argsort(wv,descending=True)[:chi]; W=U[:,idx]; dnew=chi
    Wc=int(W.shape[1]); ncol=8*Wc
    def proj(vec): return (vec.reshape(8,d_int)@W).reshape(-1)
    Hn=torch.empty(ncol,ncol,dtype=DT,device=DEV)
    cxs=[torch.empty(ncol,ncol,dtype=DT,device=DEV) for _ in range(3)]; czs=[torch.empty(ncol,ncol,dtype=DT,device=DEV) for _ in range(3)]
    for bb in range(8):
        for j in range(Wc):
            c=bb*Wc+j; col=torch.zeros(8,d_int,dtype=DT,device=DEV); col[bb,:]=W[:,j]; col=col.reshape(-1); psi=col.reshape(shape)
            Hn[:,c]=proj(matvec(col))
            for cc in range(3):
                cxs[cc][:,c]=proj(_apply(psi,SX,[cc],fd).reshape(-1)); czs[cc][:,c]=proj(_apply(psi,SZ,[cc],fd).reshape(-1))
    return dict(d=dnew,H=Hn,corners=[(cxs[cc],czs[cc]) for cc in range(3)]), E0

def build(level, chi=None, m=80):
    blk=block0(); E=None
    for L in range(1,level+1):
        blk,E=combine(blk,blk,blk,chi=chi,m=m)
    return blk,E

if __name__=="__main__":
    import time
    print("torch cuda:",torch.cuda.is_available(),torch.cuda.get_device_name(0),flush=True)
    _,E1=build(1); print(f"L1 E0={E1:.6f} (ED -6.0) {'OK' if abs(E1+6)<1e-5 else 'BAD'}",flush=True)
    _,E2=build(2,chi=8); print(f"L2 chi=8 E0={E2:.6f} (ED -16.921463) {'OK' if abs(E2+16.921463)<1e-5 else 'BAD'}",flush=True)
    prev=None
    for chi in (8,12,16,20,24,32,40,48):
        torch.cuda.empty_cache()
        t=time.time()
        try:
            _,E=build(3,chi=chi,m=300); d='' if prev is None else f' dE={E-prev:+.4f}'
            print(f"  L3 chi={chi:>3}: E0={E:.5f}{d}  ({time.time()-t:.0f}s)",flush=True); prev=E
        except Exception as e:
            print(f"  chi={chi}: {type(e).__name__}: {e}",flush=True); break

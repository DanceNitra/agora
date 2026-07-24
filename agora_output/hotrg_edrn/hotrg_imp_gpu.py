"""Impurity valley with GPU-accelerated measurement. Build the block on CPU (hotrg_obs factored truncation),
then move H/Hdef/obs to GPU (torch sparse) and do the 12 per-s ground-state solves + obs expectations on GPU
(the dominant cost). Validate L3 chi=3 == CPU 0.0775, then chi-convergence."""
import numpy as np, torch, scipy.sparse as sp, time
from hotrg_obs import build, combine, defect_bonds, block0
DEV='cuda'; DT=torch.float64

def bath(level,chi): return build(level,chi=chi)[0]
def tip(level,chi):
    b=block0()
    for L in range(1,level+1): b,_=combine(b, bath(L-1,chi), bath(L-1,chi), chi=chi, far=[4,7,8])
    return b
def defect(level,chi): return combine(tip(level-1,chi), bath(level-1,chi), tip(level-1,chi), chi=chi, far=[7])[0]

def _to_gpu(csr):
    c=csr.tocsr().astype(np.float64)
    return torch.sparse_csr_tensor(torch.tensor(c.indptr,dtype=torch.int64),
                                   torch.tensor(c.indices,dtype=torch.int64),
                                   torch.tensor(c.data,dtype=DT), size=c.shape, device=DEV)

def lanczos_sparse(Hsp, D, nev=4, m=120):
    Q=torch.zeros(m,D,dtype=DT,device=DEV); a=torch.zeros(m,dtype=DT,device=DEV); b=torch.zeros(m,dtype=DT,device=DEV)
    g=torch.Generator(device=DEV).manual_seed(0); q=torch.randn(D,generator=g,dtype=DT,device=DEV); q/=q.norm(); Q[0]=q; mm=m
    for k in range(m):
        w=(Hsp@Q[k]); ak=torch.dot(w,Q[k]); a[k]=ak; w=w-ak*Q[k]
        if k>0: w=w-b[k-1]*Q[k-1]
        w=w-Q[:k+1].T@(Q[:k+1]@w)
        bk=w.norm(); b[k]=bk
        if bk<1e-9: mm=k+1; break
        if k+1<m: Q[k+1]=w/bk
    Tm=torch.diag(a[:mm])+torch.diag(b[:mm-1],1)+torch.diag(b[:mm-1],-1)
    ev,U=torch.linalg.eigh(Tm); idx=torch.argsort(ev)[:nev]
    R=(Q[:mm].T@U[:,idx]).contiguous(); del Q,Tm,U
    return ev[idx].cpu().numpy(), R

def valley_gpu(blk, ns=12, m=120, strengths=None):
    bonds,_=defect_bonds(blk)
    Hsp=_to_gpu(blk['H']); D=blk['H'].shape[0]
    cx0,cz0=blk['corners'][0]; cx2,cz2=blk['corners'][2]
    Hdef=_to_gpu((cx0@cx2+cz0@cz2).tocsr())
    def getop(b): return blk['obs'][b] if b in blk['obs'] else blk['obs'][(b[1],b[0])]
    obsG={b:_to_gpu(getop(b)) for b in bonds}
    st=strengths if strengths is not None else np.linspace(0.25,3.0,ns); curve=[]
    for s in st:
        Hs=(Hsp + float(s)*Hdef).to_sparse_csr()
        w,low=lanczos_sparse(Hs,D,nev=4,m=m)
        deg=max(1,int(np.sum(w-w[0]<1e-6)))
        vals=[]
        for b in bonds:
            C=obsG[b]
            e=np.mean([float((low[:,k]@(C@low[:,k])).item()) for k in range(deg)])
            vals.append(e)
        curve.append(float(np.std(vals)))
        torch.cuda.empty_cache()
    curve=np.array(curve); im=int(np.argmin(curve)); depth=float(np.mean(curve[-3:])-curve[im])
    return depth, len(bonds), float(st[im]), curve

if __name__=="__main__":
    import sys
    chi=int(sys.argv[1]) if len(sys.argv)>1 else 3
    t=time.time(); blk=defect(3,chi); print(f"L3 chi={chi} dim={8*blk['d']} built ({time.time()-t:.0f}s)",flush=True)
    t=time.time(); d,nb,sm,curve=valley_gpu(blk)
    print(f"L3 chi={chi}: DEPTH={d:.4f} bonds={nb} min_at={sm:.2f}  (GPU measure {time.time()-t:.0f}s)",flush=True)
    print("curve=",[round(x,4) for x in curve],flush=True)

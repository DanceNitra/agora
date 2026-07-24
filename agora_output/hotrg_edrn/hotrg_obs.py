"""Observable path for the fractal RG (CPU/sparse, exact-L2-validatable). Tracks per-node sigma^z operators
+ the node graph through the RG so the 18 defect-neighborhood <sigma^z sigma^z> correlations can be measured
at the top, with the contradiction bond (corner0,corner2) added at strength s. GATE: at chi=None the RG must
reproduce the ED L2 valley depth 0.190.
"""
import numpy as np, scipy.sparse as sp, networkx as nx
from scipy.sparse.linalg import eigsh
from numpy.linalg import eigh
from hotrg import embed, SX, SZ

def block0():
    dims=[2,2,2]
    def s(op,i): return embed(op,[i],dims)
    H=sp.csr_matrix((8,8))
    for (i,j) in [(0,1),(1,2),(2,0)]: H=H+s(SX,i)@s(SX,j)+s(SZ,i)@s(SZ,j)
    E=[(0,1),(1,2),(2,0)]
    return dict(d=1,H=H.tocsr(),corners=[(s(SX,c),s(SZ,c)) for c in range(3)],
               obs={e:(s(SZ,e[0])@s(SZ,e[1])).tocsr() for e in E}, edges=E, cnode=[0,1,2])

def _ground(H):
    D=H.shape[0]
    if D<=256: w,V=eigh(H.toarray()); o=np.argsort(w); w=w[o]; V=V[:,o]
    else:
        kk=min(8,D-2); w,V=eigsh(H,k=kk,which='SA',tol=0,maxiter=50000); o=np.argsort(w); w=w[o]; V=V[:,o]
    deg=max(1,min(int(np.sum(w-w[0]<1e-6)),V.shape[1])); return w[0],V[:,:deg]

def _iso_far(fd, far, Wfar):
    """Isometry (D x Dnew): identity on all factors except `far` (grouped), Wfar on the far group."""
    n=len(fd); D=int(np.prod(fd)); near=[f for f in range(n) if f not in far]
    dnear=int(np.prod([fd[f] for f in near])); dfar=int(np.prod([fd[f] for f in far]))
    order=near+list(far)                                    # grouped layout: near..., far...
    # permutation: natural linear -> grouped linear
    nst=np.ones(n,dtype=np.int64)
    for i in range(n-2,-1,-1): nst[i]=nst[i+1]*fd[i+1]
    ost=np.ones(n,dtype=np.int64)
    for i in range(n-2,-1,-1): ost[i]=ost[i+1]*fd[order[i+1]]
    tmp=np.arange(D,dtype=np.int64); dig=np.zeros((D,n),dtype=np.int64)
    for k in range(n-1,-1,-1): dig[:,k]=tmp%fd[k]; tmp//=fd[k]
    g=np.zeros(D,dtype=np.int64)
    for k in range(n): g+=dig[:,order[k]]*ost[k]           # natural -> grouped
    Pin=sp.csr_matrix((np.ones(D),(g,np.arange(D))),shape=(D,D))   # grouped = Pin @ natural
    M=sp.kron(sp.identity(dnear), sp.csr_matrix(Wfar), format='csr')  # (dnear*dfar) x (dnear*Wc), grouped rows
    return (Pin.T@M).tocsr()                                # natural-in -> reduced (grouped-out basis)

def combine(A,B,C, chi=None, far=None):
    fd=[2,2,2,2,2,2,A['d'],B['d'],C['d']]; posA=[0,3,5,6]; posB=[1,4,3,7]; posC=[2,5,4,8]; D=int(np.prod(fd))
    H=(embed(A['H'],posA,fd)+embed(B['H'],posB,fd)+embed(C['H'],posC,fd)).tocsr()
    E0,low=_ground(H)
    if far is not None:                                    # FACTORED truncation: reduce only `far` factors to chi
        dfar=int(np.prod([fd[f] for f in far]))
        if chi is None or chi>=dfar: P=sp.identity(D,format='csr'); dnew=int(np.prod(fd[3:]))
        else:
            rho=np.zeros((dfar,dfar))
            for j in range(low.shape[1]):
                psi=np.asarray(low[:,j]).reshape(fd); pf=np.moveaxis(psi,far,list(range(len(far)))).reshape(dfar,-1); rho+=pf@pf.T
            wv,U=eigh(rho); Wfar=U[:,np.argsort(wv)[::-1][:chi]]
            P=_iso_far(fd,far,Wfar); dnew=P.shape[1]//8
        obs={}; edges=[]
        c0,c1,c2=A['cnode']; allids=set(A['cnode']); [allids.update(e) for e in A['edges']]; off=max(allids)+1; off2=off+max(allids)+1
        mapA={g:g for g in allids}; mapB={g:g+off for g in allids}; mapB[c2]=c1
        mapC={g:g+off2 for g in allids}; mapC[c2]=c1+off; mapC[c1]=c2
        for sub,pos,mp in ((A,posA,mapA),(B,posB,mapB),(C,posC,mapC)):
            for e,op in sub['obs'].items():
                ee=(mp[e[0]],mp[e[1]])
                if ee not in obs and (ee[1],ee[0]) not in obs: obs[ee]=embed(op,pos,fd)
            for (u,v) in sub['edges']: edges.append((mp[u],mp[v]))
        obsP={e:(P.T@op@P).tocsr() for e,op in obs.items()}
        newc=[((P.T@embed(SX,[c],fd)@P).tocsr(),(P.T@embed(SZ,[c],fd)@P).tocsr()) for c in range(3)]
        return dict(d=dnew,H=(P.T@H@P).tocsr(),corners=newc,obs=obsP,edges=edges,
                    cnode=[mapA[c0],mapB[c0],mapC[c0]]), float(E0)
    d_int=int(np.prod(fd[3:]))
    if chi is None or chi>=d_int: W=np.eye(d_int); dnew=d_int
    else:
        # DEFECT-AWARE truncation: enrich the RDM with corner-operator-applied ground states
        # (sigma^{x,z}_c |g>), the directions the contradiction bond populates on the corners, so the
        # truncated block can represent the defect-perturbed LOCAL correlations (a bath-only RDM cannot).
        states=[np.asarray(low[:,j]) for j in range(low.shape[1])]
        cops=[embed(SX,[c],fd) for c in range(3)]+[embed(SZ,[c],fd) for c in range(3)]
        enr=list(states)
        for j in range(low.shape[1]):
            for op in cops:
                enr.append(np.asarray(op@low[:,j]).ravel())
        rho=np.zeros((d_int,d_int))
        for v in enr:
            psi=v.reshape(8,d_int); rho+=psi.T@psi
        wv,U=eigh(rho); idx=np.argsort(wv)[::-1][:chi]; W=U[:,idx]; dnew=chi
    P=sp.csr_matrix(np.kron(np.eye(8),W))
    # ---- node relabel: A keeps ids; B,C offset; shared corners unified (m12=A.c1=B.c2, m23=B.c1=C.c2, m31=C.c1=A.c2)
    c0,c1,c2=A['cnode']                             # A=B=C identical -> same local cnode
    allids=set(A['cnode']); [allids.update(e) for e in A['edges']]; off=max(allids)+1; off2=off+(max(allids)+1)
    mapA={g:g for g in allids}
    mapB={g:g+off for g in allids}; mapB[c2]=c1                    # B.c2 == A.c1 (m12)
    mapC={g:g+off2 for g in allids}; mapC[c2]=c1+off; mapC[c1]=c2  # C.c2==B.c1(m23), C.c1==A.c2(m31)
    obs={}; edges=[]
    for sub,pos,mp in ((A,posA,mapA),(B,posB,mapB),(C,posC,mapC)):
        for e,op in sub['obs'].items():
            ee=(mp[e[0]],mp[e[1]])
            if ee not in obs and (ee[1],ee[0]) not in obs: obs[ee]=embed(op,pos,fd)
        for (u,v) in sub['edges']: edges.append((mp[u],mp[v]))
    obsP={e:(P.T@op@P).tocsr() for e,op in obs.items()}
    cnode=[mapA[c0],mapB[c0],mapC[c0]]
    newc=[((P.T@embed(SX,[c],fd)@P).tocsr(),(P.T@embed(SZ,[c],fd)@P).tocsr()) for c in range(3)]
    return dict(d=dnew,H=(P.T@H@P).tocsr(),corners=newc,obs=obsP,edges=edges,cnode=cnode), float(E0)

def build(level, chi=None):
    b=block0(); E=None
    for _ in range(level): b,E=combine(b,b,b,chi=chi)
    return b,E

def defect_bonds(blk, R=2):
    """The radius-R defect neighborhood bonds of {corner0,corner2}, in the block's node graph."""
    d0,_,d2=blk['cnode']
    G=nx.Graph(); G.add_edges_from(blk['edges'])
    dd0=nx.single_source_shortest_path_length(G,d0); dd2=nx.single_source_shortest_path_length(G,d2)
    near=lambda n: min(dd0.get(n,99),dd2.get(n,99))<=R
    return [(u,v) for (u,v) in blk['edges'] if near(u) and near(v)], (d0,d2)

def valley(level, chi=None, strengths=None):
    if strengths is None: strengths=np.linspace(0.25,3.0,12)
    blk,_=build(level,chi=chi)
    bonds,(d0,d2)=defect_bonds(blk)
    Hbase=blk['H']; cx0,cz0=blk['corners'][0]; cx2,cz2=blk['corners'][2]
    Hdef=(cx0@cx2+cz0@cz2).tocsr()                  # defect bond (corner0,corner2): sigma^x sigma^x + sigma^z sigma^z
    curve=[]
    for s in strengths:
        H=(Hbase+float(s)*Hdef).tocsr()
        _,low=_ground(H)
        # manifold-averaged <sz_i sz_j> per bond
        def getop(b):
            return blk['obs'][b] if b in blk['obs'] else blk['obs'][(b[1],b[0])]
        vals=[]
        for b in bonds:
            Cij=getop(b)
            e=np.mean([float((low[:,k].conj().T@(Cij@low[:,k])).real) for k in range(low.shape[1])])
            vals.append(e)
        curve.append(float(np.std(vals)))
    curve=np.array(curve); im=int(np.argmin(curve)); sh=float(np.mean(curve[-3:]))
    return float(sh-curve[im]), float(strengths[im]), len(bonds), curve

if __name__=="__main__":
    for lv in (1,2):
        depth,smin,nb,curve=valley(lv,chi=None)
        print(f"L{lv}: |defect bonds|={nb}  valley_depth={depth:.4f}  min_at={smin:.2f}")
        print(f"     curve={np.round(curve,3).tolist()}")
    print("ED ref: L2 LOCAL valley depth = 0.1902 (18 bonds)")

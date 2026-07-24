"""Reconstruct the L1->L2 finite-size scaling reference in ED, so DMRG can be validated against it.
Setup (Li's contradiction protocol): base Sierpinski(level), all edges w=1; ADD corner edge (0,2)
tuned s in [0,3]; manifold-averaged std of <sz_i sz_j> over the BASE edges is the valley observable.
Must reproduce L2: min_std 0.0843 at s=0.50, depth 0.0401 (and L1: min_std 0.1225, depth 0.0735).
"""
import os
os.environ["OMP_NUM_THREADS"] = "12"
import numpy as np, networkx as nx
from scipy.sparse import coo_matrix, diags
from scipy.sparse.linalg import eigsh

STR = np.linspace(0.0, 3.0, 13)
DEGTOL = 1e-2

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

def make_ops(N):
    DIM=1<<N; IDX=np.arange(DIM,dtype=np.int64)
    def H_build(edge_w):
        diag=np.zeros(DIM); rows=[]; cols=[]; vals=[]
        for (i,j,w) in edge_w:
            bi=(IDX>>i)&1; bj=(IDX>>j)&1
            diag += w*(1-2*bi)*(1-2*bj)
            fl = IDX ^ (1<<i) ^ (1<<j)
            rows.append(IDX); cols.append(fl); vals.append(np.full(DIM,w))
        r=np.concatenate(rows); c=np.concatenate(cols); v=np.concatenate(vals)
        return (coo_matrix((v,(r,c)),shape=(DIM,DIM)).tocsr()+diags(diag)).tocsr()
    def szsz(i,j): return (1-2*((IDX>>i)&1))*(1-2*((IDX>>j)&1))
    return DIM,H_build,szsz

def manifold_std(H, P_edges, v0):
    for k in (16,32,48):
        kk=min(k,H.shape[0]-2)
        E,V=eigsh(H,k=kk,which='SA',tol=0,v0=v0,maxiter=50000)
        o=np.argsort(E); E=E[o]; V=V[:,o]
        deg=int(np.sum(np.abs(E-E[0])<DEGTOL)); deg=max(1,min(deg,V.shape[1]))
        gap_ok=(deg<V.shape[1]) and (E[deg]-E[deg-1]>5*DEGTOL)
        if gap_ok: break
    Pm=np.abs(V[:,:deg])**2
    man=float(np.std([(d@Pm).mean() for d in P_edges]))
    return man, deg, V[:,0]

def scaling_point(level):
    G=sierpinski_graph(level); N=G.number_of_nodes()
    base=list(G.edges())
    DIM,H_build,szsz=make_ops(N)
    Hbase=H_build([(i,j,1.0) for (i,j) in base])
    Hedge=H_build([(0,2,1.0)])                 # the ADDED corner contradiction edge
    P_edges=[szsz(i,j) for (i,j) in base]      # observable = dispersion over base correlations
    v0=None; curve=[]; degs=[]
    for s in STR:
        H=Hbase+s*Hedge
        m,deg,gs=manifold_std(H,P_edges,v0); v0=gs
        curve.append(m); degs.append(deg)
    curve=np.array(curve); imin=int(np.argmin(curve))
    depth=float(min(curve[0],curve[-1])-curve[imin]) if 0<imin<len(curve)-1 else 0.0
    return N,len(base),float(STR[imin]),float(curve[imin]),depth,curve,degs

if __name__=="__main__":
    print(f"{'level':5} {'N':>3} {'E':>4} {'min_at':>7} {'min_std':>8} {'depth':>8}  degs")
    for lv in (1,2):
        N,E,mn,mstd,depth,curve,degs=scaling_point(lv)
        print(f"  L{lv}  {N:>3} {E:>4} {mn:>7.2f} {mstd:>8.4f} {depth:>8.4f}  {degs}")
        print(f"       curve={np.round(curve,4).tolist()}")

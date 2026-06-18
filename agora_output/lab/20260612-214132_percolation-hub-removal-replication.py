# Smallest mechanism model: targeted hub removal vs bond-percolation threshold.
# BA(N=2000,m=2). Molloy-Reed pc = <k>/(<k^2>-<k>) before & after removing top-10% hubs;
# Monte-Carlo bond percolation cross-check (giant-component onset). Claim: pc 0.174 -> 0.776.
import numpy as np, networkx as nx, statistics as st
rng = np.random.default_rng(7)
def mr(degs):
    d=np.array([x for x in degs if x>0],float); k1=d.mean(); k2=(d**2).mean()
    return k1/(k2-k1) if k2-k1>0 else float('inf')
def mc(G,ps,trials=12):
    nodes=list(G.nodes()); N=len(nodes); E=list(G.edges()); out=[]
    for p in ps:
        f=0.0
        for _ in range(trials):
            H=nx.Graph(); H.add_nodes_from(nodes)
            H.add_edges_from([e for e in E if rng.random()<p])
            f += (max((len(c) for c in nx.connected_components(H)),default=1))/N
        out.append(f/trials)
    return np.array(out)
def pc_curve(ps,S,thr=0.05):
    for p,s in zip(ps,S):
        if s>=thr: return p
    return float('nan')
ps=np.linspace(0.02,0.95,32); b_mr=[];a_mr=[];b_mc=[];a_mc=[]
for r in range(6):
    G=nx.barabasi_albert_graph(2000,2,seed=int(rng.integers(1e9)))
    b_mr.append(mr([d for _,d in G.degree()]))
    order=sorted(G.nodes(),key=lambda n:G.degree(n),reverse=True)
    Gp=G.copy(); Gp.remove_nodes_from(order[:int(0.1*G.number_of_nodes())])
    a_mr.append(mr([d for _,d in Gp.degree()]))
    if r<3:
        b_mc.append(pc_curve(ps,mc(G,ps))); a_mc.append(pc_curve(ps,mc(Gp,ps)))
print("MR pc before=%.3f after=%.3f (claim .174 -> .776)"%(st.mean(b_mr),st.mean(a_mr)))
print("MC pc before=%.3f after=%.3f"%(st.mean(b_mc),st.mean(a_mc)))
print("MC ratio after/before=%.2fx  claim ratio=%.2fx"%(st.mean(a_mc)/st.mean(b_mc),0.776/0.174))

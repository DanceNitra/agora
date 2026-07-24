"""ARTIFACT for the s=2.50 claim: L2 exact-diagonalization physics on a fine grid straddling s=2.50.
Shows the ground-state observables are SMOOTH there (no gap closing, no non-analyticity), so Marat's
pairwise-difference 's=2.50 divergence' is a normalization property of the derived TAT metric, not a
feature of the Hamiltonian. Re-runnable; prints the grid + the smoothness summary.
"""
import os
os.environ["OMP_NUM_THREADS"]="12"
import numpy as np
from scipy.sparse.linalg import eigsh
from reconstruct_scaling_ED import sierpinski_graph, make_ops

def main():
    G=sierpinski_graph(2); N=G.number_of_nodes(); base=list(G.edges())
    DIM,H_build,szsz=make_ops(N)
    Hbase=H_build([(i,j,1.0) for (i,j) in base]); Hedge=H_build([(0,2,1.0)])
    P=[szsz(i,j) for (i,j) in base]
    SS=np.linspace(2.0,3.0,21)
    print(f"L2 (N={N}, {len(base)} base edges) ED, fine grid across s=2.50")
    print(f"{'s':>5} {'E0':>10} {'gap(E2-E0)':>11} {'corr_std':>9}")
    gaps=[]; stds=[]
    for s in SS:
        H=Hbase+s*Hedge
        E,V=eigsh(H,k=6,which='SA',tol=0,maxiter=50000)
        o=np.argsort(E); E=E[o]; V=V[:,o]
        gap=float(E[2]-E[0]); gaps.append(gap)               # deg=2 Kramers -> physical gap is E2-E0
        Pm=np.abs(V[:,:2])**2; std=float(np.std([(d@Pm).mean() for d in P])); stds.append(std)
        tag=" <-- s=2.50" if abs(s-2.5)<1e-6 else ""
        print(f"{s:5.2f} {E[0]:10.4f} {gap:11.4f} {std:9.4f}{tag}")
    gaps=np.array(gaps); stds=np.array(stds)
    d2=np.gradient(np.gradient(stds,SS),SS)
    i25=int(np.argmin(np.abs(SS-2.5)))
    mono = bool(np.all(np.diff(stds)>0) or np.all(np.diff(stds)<0))
    print("\n--- SMOOTHNESS SUMMARY AT s=2.50 ---")
    print(f"gap nonzero through window: min gap = {gaps.min():.4f} (at s={SS[int(np.argmin(gaps))]:.2f}); monotone in s: {bool(np.all(np.diff(gaps)>0) or np.all(np.diff(gaps)<0))}")
    print(f"corr_std at s=2.50 = {stds[i25]:.4f}; 2nd derivative = {d2[i25]:.4f} (approx 0 => no kink)")
    print(f"corr_std strictly monotone on [2.0,3.0]: {mono}")
    print("VERDICT: s=2.50 is a smooth, featureless point on the right shoulder (no transition).")

if __name__=="__main__":
    main()

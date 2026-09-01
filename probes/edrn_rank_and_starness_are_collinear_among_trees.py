"""COUNTER-PROBE 4. The draft tells Marat to 'plot C against 2S+1 across your whole set'.
In his set only the star exceeds rank 4, so rank and star-ness are perfectly collinear: the plot
cannot separate 'C tracks the degeneracy' from 'the star is special'. Find the discriminating control:
a NON-star graph with the SAME rank as the star.
"""
import itertools, numpy as np, networkx as nx

def rank_of_tree(G):
    """Lieb-Mattis: ground multiplet 2S+1 = |nA-nB|+1 on a connected bipartite AF Heisenberg graph."""
    a, b = nx.bipartite.sets(G)
    return abs(len(a) - len(b)) + 1

for N in (7, 8, 9, 10):
    star = nx.star_graph(N - 1)
    r_star = rank_of_tree(star)
    same, total = [], 0
    for T in nx.nonisomorphic_trees(N):
        total += 1
        r = rank_of_tree(T)
        if r == r_star and not nx.is_isomorphic(T, star):
            same.append(sorted(d for _, d in T.degree()))
    print("N=%d: star rank %d;  %d non-isomorphic trees;  %d NON-star trees at the SAME rank"
          % (N, r_star, total, len(same)))
    for s in same[:4]:
        print("      degree sequence %s" % s)

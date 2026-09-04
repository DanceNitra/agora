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

# ---- recorded run -------------------------------------------------------------------
# Cited by name in a letter to a collaborator while it recorded nothing, so `main` carried
# the script and no result. The letter discussing it says in as many words that no run of
# ours stood behind it. This is that run. It changes no measurement.
import json as _json, os as _os
_rep = {"lieb_mattis_rank": "2S+1 = |nA - nB| + 1 on a connected bipartite AF Heisenberg graph",
        "by_N": {}}
for _N in (7, 8, 9, 10):
    _star = nx.star_graph(_N - 1)
    _rs = rank_of_tree(_star)
    _same, _total, _ranks = [], 0, {}
    for _T in nx.nonisomorphic_trees(_N):
        _total += 1
        _r = rank_of_tree(_T)
        _ranks[_r] = _ranks.get(_r, 0) + 1
        if _r == _rs and not nx.is_isomorphic(_T, _star):
            _same.append(sorted(d for _, d in _T.degree()))
    _rep["by_N"][str(_N)] = {
        "star_rank": _rs,
        "n_nonisomorphic_trees": _total,
        "n_non_star_trees_at_star_rank": len(_same),
        "degree_sequences_of_those": _same[:8],
        "rank_histogram": {str(k): v for k, v in sorted(_ranks.items())},
        "max_rank_among_non_star_trees": max((k for k in _ranks if k < _rs), default=None),
    }
# The question this probe was written to answer: is there a discriminating control, that is a
# non-star tree carrying the star's rank? If none exists at any N, rank and star-ness cannot be
# separated within trees, and a regression fitted on non-star trees predicts the star's rank by
# extrapolation with no data at that point.
_rep["a_discriminating_control_exists_among_trees"] = any(
    v["n_non_star_trees_at_star_rank"] > 0 for v in _rep["by_N"].values())
print("MEASURED: discriminating control among trees exists = %s"
      % _rep["a_discriminating_control_exists_among_trees"])
for _k, _v in sorted(_rep["by_N"].items(), key=lambda x: int(x[0])):
    print("  N=%s: star rank %d, highest non-star rank %s"
          % (_k, _v["star_rank"], _v["max_rank_among_non_star_trees"]))
_out = _os.path.splitext(_os.path.abspath(__file__))[0] + ".result.json"
with open(_out, "w", encoding="utf-8") as _fh:
    _json.dump(_rep, _fh, indent=1)
print("wrote", _os.path.basename(_out))

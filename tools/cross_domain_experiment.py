#!/usr/bin/env python3
"""
cross_domain_experiment.py — severe test + implementation of the owner's hypothesis:

  "If the vault's concepts are organized by domain INTERCONNECTIVITY (a link network) rather than
   static categories, then a dynamic NETWORK-BASED filter will improve CROSS-DOMAIN idea generation
   by >= 40% vs traditional keyword search."

Real data: the vault's Domains/ tree (real domain labels) + the real [[wiki-link]] graph (~43k edges).
Two retrievers, same top-k, same seeds:
  - keyword(seed)  = TF-IDF cosine over the note text (the standard "search") — a strong, fair baseline.
  - network(seed)  = spreading activation over the [[link]] graph (1-hop + decayed 2-hop), text-blind.
Metric: CROSS-DOMAIN YIELD = of the top-k returned, the fraction in a DIFFERENT domain than the seed
(that IS cross-domain idea generation). We compare the two and test the >= 40% improvement claim.

Usage:  python tools/cross_domain_experiment.py
The two retrievers are the implementation; main() is the measured test.
"""
from __future__ import annotations

import glob
import math
import os
import re
from collections import defaultdict

VAULT = "C:/Users/Danculus/my-second-brain/04 Resources/Concepts/Domains"
_STOP = set("the a an of to in and or is are was on for with as by it its this that these those be "
            "from at into than then so such not no can may will would could we our you your they their "
            "which when where what how why also more most less between within across via using used use "
            "one two three new each per about over under both either neither only just very".split())
_WORD = re.compile(r"[a-z][a-z0-9\-]{2,}")
_LINK = re.compile(r"\[\[([^\]|#]+)")


def _tokens(text: str):
    return [w for w in _WORD.findall(text.lower()) if w not in _STOP]


def load_vault():
    """Return nodes: list of dicts {title, domain, tf (term->count), links (raw targets)} + title index."""
    nodes, by_title = [], {}
    for f in glob.glob(VAULT + "/**/*.md", recursive=True):
        rel = os.path.relpath(f, VAULT).split(os.sep)
        if len(rel) < 2:
            continue
        domain = rel[0]
        title = os.path.splitext(os.path.basename(f))[0]
        try:
            txt = open(f, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        toks = _tokens(txt)
        if len(toks) < 8:
            continue
        tf = defaultdict(int)
        for t in toks:
            tf[t] += 1
        links = [m.strip() for m in _LINK.findall(txt)]
        key = title.strip().lower()
        if key in by_title:
            continue
        by_title[key] = len(nodes)
        nodes.append({"title": title, "domain": domain, "tf": tf, "links": links})
    return nodes, by_title


def build(nodes, by_title):
    """TF-IDF vectors + the undirected link-graph adjacency (resolved to known notes)."""
    N = len(nodes)
    df = defaultdict(int)
    for nd in nodes:
        for term in nd["tf"]:
            df[term] += 1
    idf = {t: math.log(1 + N / (1 + c)) for t, c in df.items()}
    vecs, norms = [], []
    for nd in nodes:
        v = {t: (1 + math.log(c)) * idf[t] for t, c in nd["tf"].items()}
        vecs.append(v)
        norms.append(math.sqrt(sum(w * w for w in v.values())) or 1.0)
    adj = defaultdict(set)
    for i, nd in enumerate(nodes):
        for tgt in nd["links"]:
            j = by_title.get(tgt.strip().lower())
            if j is not None and j != i:
                adj[i].add(j)
                adj[j].add(i)                       # undirected interconnectivity
    return idf, vecs, norms, adj


def keyword_topk(seed, vecs, norms, k):
    """Standard search: top-k by TF-IDF cosine to the seed's text."""
    sv, sn = vecs[seed], norms[seed]
    scores = []
    for j in range(len(vecs)):
        if j == seed:
            continue
        v = vecs[j]
        # dot over the smaller vector
        a, b = (sv, v) if len(sv) <= len(v) else (v, sv)
        dot = sum(w * v.get(t, 0.0) for t, w in a.items()) if a is sv else sum(w * sv.get(t, 0.0) for t, w in a.items())
        if dot:
            scores.append((dot / (sn * norms[j]), j))
    scores.sort(reverse=True)
    return [j for _, j in scores[:k]]


def network_topk(seed, adj, k, hop2=0.4):
    """Network filter: spreading activation over the [[link]] graph (1-hop=1.0, 2-hop=hop2). Text-blind."""
    act = defaultdict(float)
    for n1 in adj.get(seed, ()):
        act[n1] += 1.0
        for n2 in adj.get(n1, ()):
            if n2 != seed:
                act[n2] += hop2
    act.pop(seed, None)
    return [j for j, _ in sorted(act.items(), key=lambda kv: -kv[1])[:k]]


def cross_domain_fraction(seed, hits, nodes):
    if not hits:
        return None
    sd = nodes[seed]["domain"]
    return sum(1 for j in hits if nodes[j]["domain"] != sd) / len(hits)


def main(k=10, max_seeds=300, seed_min_links=3):
    nodes, by_title = load_vault()
    idf, vecs, norms, adj = build(nodes, by_title)
    edges = sum(len(v) for v in adj.values()) // 2
    domains = len({nd["domain"] for nd in nodes})
    print(f"vault: {len(nodes)} concept notes · {domains} domains · {edges} resolved link-edges\n")
    # deterministic seed sample: notes with enough links for the network to be meaningful
    seeds = [i for i in range(len(nodes)) if len(adj.get(i, ())) >= seed_min_links]
    seeds = seeds[:: max(1, len(seeds) // max_seeds)][:max_seeds]
    kw_cd, nw_cd, both = [], [], 0
    for s in seeds:
        kh, nh = keyword_topk(s, vecs, norms, k), network_topk(s, adj, k)
        kf, nf = cross_domain_fraction(s, kh, nodes), cross_domain_fraction(s, nh, nodes)
        if kf is None or nf is None or not nh:
            continue
        kw_cd.append(kf)
        nw_cd.append(nf)
        both += 1
    kw = sum(kw_cd) / len(kw_cd)
    nw = sum(nw_cd) / len(nw_cd)
    impr = (nw - kw) / kw if kw else float("inf")
    print(f"seeds tested: {both} (>= {seed_min_links} links each), top-{k} each\n")
    print(f"  keyword search   cross-domain yield: {kw:.1%}")
    print(f"  network filter   cross-domain yield: {nw:.1%}")
    print(f"  improvement: {impr:+.1%}   (claim: >= +40%)")
    verdict = "SUPPORTED" if impr >= 0.40 else ("DIRECTIONALLY SUPPORTED" if impr > 0 else "REFUTED")
    print(f"\n  HYPOTHESIS {verdict} — network filtering "
          f"{'beats' if impr>0 else 'does not beat'} keyword search at surfacing cross-domain concepts.")
    return {"keyword": kw, "network": nw, "improvement": impr, "seeds": both, "k": k,
            "domains": domains, "edges": edges, "verdict": verdict}


def suggest(query, k=8):
    """THE IMPLEMENTATION, usable: given a free-text concept/query, find the closest seed note by
    keyword, then NETWORK-FILTER its graph neighbourhood and return the CROSS-DOMAIN concepts it
    surfaces (the ones a keyword search would miss). Returns a list of {title, domain}."""
    nodes, by_title = load_vault()
    idf, vecs, norms, adj = build(nodes, by_title)
    # map the query into the space: pick the highest TF-IDF-cosine note as the seed
    qtf = defaultdict(int)
    for t in _tokens(query):
        qtf[t] += 1
    qv = {t: (1 + math.log(c)) * idf.get(t, 0.0) for t, c in qtf.items()}
    qn = math.sqrt(sum(w * w for w in qv.values())) or 1.0
    best, seed = -1.0, None
    for j in range(len(nodes)):
        dot = sum(w * vecs[j].get(t, 0.0) for t, w in qv.items())
        if dot:
            sc = dot / (qn * norms[j])
            if sc > best:
                best, seed = sc, j
    if seed is None:
        return {"query": query, "seed": None, "ideas": []}
    hits = network_topk(seed, adj, k * 2)
    sd = nodes[seed]["domain"]
    ideas = [{"title": nodes[j]["title"], "domain": nodes[j]["domain"]}
             for j in hits if nodes[j]["domain"] != sd][:k]
    return {"query": query, "seed": {"title": nodes[seed]["title"], "domain": sd}, "ideas": ideas}


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        r = suggest(" ".join(sys.argv[1:]))
        s = r["seed"]
        print(f"seed: {s['title']!r} [{s['domain']}]" if s else "no seed match")
        print("cross-domain ideas the network surfaces (keyword search would miss):")
        for it in r["ideas"]:
            print(f"  - [{it['domain']}] {it['title']}")
    else:
        main()

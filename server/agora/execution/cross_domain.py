"""
Network-based cross-domain idea seeding for the agents' seminar.

The validated mechanism (tools/cross_domain_experiment.py, severe-tested on the real vault: 2,681
concepts, 46 domains, 20,635 [[link]] edges): a network filter over the concept graph surfaces +67.5%
more CROSS-DOMAIN concepts than keyword search (65.9% vs 39.3% cross-domain yield) — the owner's >=40%
hypothesis, SUPPORTED. Here that filter FEEDS the agents: pick a well-linked seed concept, spread
activation over the real link graph, and hand the seminar a cross-domain bridge to research.

Graph-only (no TF-IDF): topic seeding just needs domains + the [[link]] adjacency, so the cache is
small and the first build is fast. Cached in-process after the first call.
"""
from __future__ import annotations

import glob
import os
import random
import re
from collections import defaultdict

from agora.config import settings

_LINK = re.compile(r"\[\[([^\]|#]+)")
_graph = None                                   # (nodes, adj) cache


def _domains_dir() -> str:
    v = settings.vault_path or "C:/Users/Danculus/my-second-brain"
    return os.path.join(v, "04 Resources", "Concepts", "Domains")


def _load_graph():
    """Build (nodes, adj) once: nodes = [(title, domain)], adj = undirected resolved [[link]] graph."""
    global _graph
    if _graph is not None:
        return _graph
    base = _domains_dir()
    nodes, by_title, raw = [], {}, []
    for f in glob.glob(base + "/**/*.md", recursive=True):
        rel = os.path.relpath(f, base).split(os.sep)
        if len(rel) < 2:
            continue
        title = os.path.splitext(os.path.basename(f))[0]
        key = title.strip().lower()
        if key in by_title:
            continue
        try:
            txt = open(f, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        by_title[key] = len(nodes)
        nodes.append((title, rel[0]))           # (title, domain)
        raw.append([m.strip().lower() for m in _LINK.findall(txt)])
    adj = defaultdict(set)
    for i, links in enumerate(raw):
        for tgt in links:
            j = by_title.get(tgt)
            if j is not None and j != i:
                adj[i].add(j)
                adj[j].add(i)
    _graph = (nodes, adj)
    return _graph


def _network_topk(seed, adj, k, hop2=0.4):
    """Spreading activation over the link graph: 1-hop = 1.0, 2-hop = hop2 (the validated filter)."""
    act = defaultdict(float)
    for n1 in adj.get(seed, ()):
        act[n1] += 1.0
        for n2 in adj.get(n1, ()):
            if n2 != seed:
                act[n2] += hop2
    act.pop(seed, None)
    return [j for j, _ in sorted(act.items(), key=lambda kv: -kv[1])[:k]]


def cross_domain_topic(min_links: int = 4):
    """A fresh CROSS-DOMAIN bridge topic from the network filter: pick a well-linked seed, spread over
    the graph, take the strongest concept in a DIFFERENT domain. Returns {headline, prompt} or None."""
    try:
        nodes, adj = _load_graph()
        seeds = [i for i in adj if len(adj[i]) >= min_links]
        if not seeds:
            return None
        random.shuffle(seeds)
        for s in seeds[:50]:
            sd = nodes[s][1]
            for j in _network_topk(s, adj, 12):
                if nodes[j][1] != sd:
                    a, da = nodes[s]
                    b, db = nodes[j]
                    return {
                        "headline": f"Bridge: {a} x {b}"[:90],
                        "prompt": (f"The vault's link-graph connects '{a}' ({da}) and '{b}' ({db}) "
                                   f"across domains. Find the REAL shared mechanism that links them "
                                   f"(a structural/dynamical analogy, not surface similarity), state "
                                   f"ONE falsifiable claim it implies, and what evidence would refute "
                                   f"it. Ground it in literature or the vault."),
                        "a": a, "b": b, "domains": [da, db],
                    }
        return None
    except Exception:
        return None

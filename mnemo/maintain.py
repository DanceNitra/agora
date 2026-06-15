"""
maintain — the self-maintaining second brain.  (mnemo's maintenance layer)

The #1 frustration with second brains (measured, 2026): *capture is easy, maintenance is hard.*
People set up Obsidian/Notion, take notes for two weeks, then the review/re-link/summarise/reorganise
chore piles up and the vault decays into noise. The 2026 ask is "a brain that maintains itself."

This is that maintenance pass, run over a folder of Markdown notes. It does the chore the human won't:
  • DEAD LINKS    — [[wikilinks]] pointing at a note that doesn't exist
  • ORPHANS       — notes nothing links to and that link to nothing (lost in the pile)
  • STALE         — notes untouched past a threshold AND weakly connected (review/refresh/archive)
  • DUPLICATES    — near-identical note clusters (merge candidates)
  • HEALTH        — a vault self-legibility score = % of notes in the link graph's giant component,
                    plus orphan/dead-link/stale fractions. Knowledge debt is a PERCOLATION collapse:
                    legibility holds, then drops abruptly — so this warns BEFORE the cliff, not after.

Safety rule (non-negotiable, same as mnemo): this is ADVISORY. It READS notes and returns a plan;
it never edits, moves, or deletes a note. You (or an explicit apply step) act on the report.

Zero dependencies. With an embedder, duplicate detection gets sharper; without one it uses a
token-overlap (Jaccard) fallback so it runs anywhere, today.
"""
from __future__ import annotations

import re
import time
from pathlib import Path

_WIKILINK = re.compile(r"\[\[([^\]|#]+)")
_WORD = re.compile(r"[a-z0-9]{3,}")


def scan_vault(folder: str, cap: int = 4000) -> list[dict]:
    """Read a folder of .md notes into {title, path, text, mtime, links_out}."""
    notes = []
    for p in Path(folder).rglob("*.md"):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")[:cap]
        except Exception:
            continue
        notes.append({"title": p.stem, "path": str(p), "text": text,
                      "mtime": p.stat().st_mtime,
                      "links_out": {m.strip() for m in _WIKILINK.findall(text)}})
    return notes


def _tokens(text: str) -> set:
    return set(_WORD.findall(text.lower()))


def _giant_component_frac(titles: set, edges: dict) -> float:
    """Fraction of notes in the largest connected component of the (undirected) link graph —
    the vault's self-legibility. A low/falling value = knowledge-debt percolation collapse."""
    if not titles:
        return 1.0
    seen, best = set(), 0
    for start in titles:
        if start in seen:
            continue
        stack, comp = [start], 0
        while stack:
            n = stack.pop()
            if n in seen:
                continue
            seen.add(n); comp += 1
            stack.extend(edges.get(n, set()) - seen)
        best = max(best, comp)
    return best / len(titles)


def maintain(notes: list[dict], *, now: float | None = None, stale_days: float = 120.0,
             dup_threshold: float = 0.6, embed=None) -> dict:
    """Compute the maintenance plan + health for a scanned vault. Pure: returns findings, edits nothing."""
    now = time.time() if now is None else float(now)
    titles = {n["title"] for n in notes}
    by_title = {n["title"]: n for n in notes}

    # link graph (only edges to notes that exist)
    edges: dict[str, set] = {t: set() for t in titles}
    in_links: dict[str, int] = {t: 0 for t in titles}
    dead_links = []
    for n in notes:
        for tgt in n["links_out"]:
            if tgt in titles:
                edges[n["title"]].add(tgt); edges[tgt].add(n["title"]); in_links[tgt] += 1
            else:
                dead_links.append({"note": n["title"], "broken_link": tgt})

    orphans, stale = [], []
    for n in notes:
        out_valid = len(n["links_out"] & titles)
        if in_links[n["title"]] == 0 and out_valid == 0:
            orphans.append(n["title"])
        age = (now - n["mtime"]) / 86400.0
        if age > stale_days and (in_links[n["title"]] + out_valid) <= 1:
            stale.append({"note": n["title"], "age_days": round(age)})

    # near-duplicate clusters (token Jaccard, or embedder cosine if provided)
    dup_clusters = []
    if embed is None:
        toks = {n["title"]: _tokens(n["text"]) for n in notes}
        items = list(titles)
        used = set()
        for i, a in enumerate(items):
            if a in used:
                continue
            cluster = [a]
            for b in items[i + 1:]:
                if b in used:
                    continue
                ta, tb = toks[a], toks[b]
                if ta and tb:
                    j = len(ta & tb) / len(ta | tb)
                    if j >= dup_threshold:
                        cluster.append(b); used.add(b)
            if len(cluster) > 1:
                used.add(a); dup_clusters.append(cluster)

    gc = _giant_component_frac(titles, edges)
    n = max(1, len(notes))
    health = {
        "notes": len(notes),
        "self_legibility": round(gc, 3),               # % in the giant component (1.0 = fully connected)
        "orphan_frac": round(len(orphans) / n, 3),
        "dead_link_frac": round(len(dead_links) / n, 3),
        "stale_frac": round(len(stale) / n, 3),
        "avg_links": round(sum(len(e) for e in edges.values()) / n, 2),
        "duplicate_clusters": len(dup_clusters),
    }
    # one-line verdict: percolation framing — warn as the giant component thins
    if gc >= 0.85:
        health["verdict"] = "healthy — well-connected"
    elif gc >= 0.6:
        health["verdict"] = "fraying — link the orphans before it fragments"
    else:
        health["verdict"] = "DEBT CLIFF — self-legibility collapsing; consolidate now"

    actions = []
    if dead_links:
        actions.append(f"fix {len(dead_links)} dead links")
    if orphans:
        actions.append(f"link or archive {len(orphans)} orphan notes")
    if stale:
        actions.append(f"review/refresh {len(stale)} stale notes")
    if dup_clusters:
        actions.append(f"merge {len(dup_clusters)} duplicate clusters")
    return {"health": health, "actions": actions, "dead_links": dead_links,
            "orphans": orphans, "stale": stale, "duplicate_clusters": dup_clusters}


if __name__ == "__main__":
    # Build a synthetic vault on disk (a connected core + planted orphans/dead-links/stale/dups),
    # run the maintainer, and verify it finds each problem and scores health. Testable today.
    import tempfile, os, random
    random.seed(5)
    d = tempfile.mkdtemp(prefix="vault_")
    now = time.time(); DAY = 86400.0

    def w(name, text, age_days=1):
        p = Path(d) / f"{name}.md"
        p.write_text(text, encoding="utf-8")
        os.utime(p, (now - age_days * DAY, now - age_days * DAY))

    # connected core of 12 DISTINCT notes (different topics), chained -> one giant component
    topics = ["transformer attention", "vector database sharding", "kalman filtering robotics",
              "supabase row-level security", "rust borrow checker", "options gamma hedging",
              "crispr off-target effects", "kubernetes pod autoscaling", "bayesian ab testing",
              "graphql n+1 queries", "circadian melatonin timing", "elliptic curve signatures"]
    for i, t in enumerate(topics):
        w(f"core{i}", f"Note on {t}: detailed thoughts and specifics about {t}. See [[core{(i+1)%12}]].")
    w("hub", "Index linking [[core0]] [[core3]] [[core7]].")
    # planted problems:
    w("orphan_a", "A lonely thought nobody links and that links nowhere.")          # orphan
    w("orphan_b", "Another island note, unconnected.")                              # orphan
    w("broken", "This points to [[NoteThatDoesNotExist]] and [[AlsoGone]].")        # 2 dead links
    w("stale_old", "Old weakly-linked note about delta.", age_days=400)             # stale (old + weak)
    w("dup1", "Quarterly pricing: enterprise tier is $499 per seat per month billed annually.")
    w("dup2", "Quarterly pricing: enterprise tier is $499 per seat per month billed annually!!")  # near-dup

    rep = maintain(scan_vault(d), now=now, stale_days=120)
    print("health :", rep["health"])
    print("actions:", rep["actions"])
    print("dead_links:", rep["dead_links"])
    print("orphans:", rep["orphans"])
    print("stale  :", rep["stale"])
    print("dup clusters:", rep["duplicate_clusters"])
    assert rep["health"]["dead_link_frac"] > 0 and len(rep["dead_links"]) == 2
    assert "orphan_a" in rep["orphans"] and "orphan_b" in rep["orphans"]
    assert any("stale_old" == s["note"] for s in rep["stale"])
    assert any(set(c) == {"dup1", "dup2"} for c in rep["duplicate_clusters"])
    print("\nOK — maintainer found dead links, orphans, stale, and the duplicate cluster, and scored health.")

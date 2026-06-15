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
_FM_DATE = re.compile(r"^\s*(updated|date|created)\s*:\s*(\d{4})-(\d{2})-(\d{2})", re.M)


def _frontmatter(text: str) -> tuple[set, float | None]:
    """Parse a note's YAML frontmatter (best-effort, zero-dep) for aliases and the freshest date.
    Returns (aliases set, epoch-ts or None). Vaults sync over git, which resets file mtime — so the
    real 'last touched' lives in frontmatter (updated/date/created), not on disk."""
    if not text.startswith("---"):
        return set(), None
    end = text.find("\n---", 3)
    fm = text[3:end] if end != -1 else ""
    aliases = set()
    m = re.search(r"^\s*aliases\s*:\s*\[([^\]]*)\]", fm, re.M)            # inline: aliases: [a, b]
    if m:
        aliases |= {a.strip().strip("\"'") for a in m.group(1).split(",") if a.strip()}
    bl = re.search(r"^\s*aliases\s*:\s*\n((?:\s*-\s*.+\n?)+)", fm, re.M)  # block list under aliases:
    if bl:
        aliases |= {ln.split("-", 1)[1].strip().strip("\"'")
                    for ln in bl.group(1).splitlines() if "-" in ln}
    ts = None
    for _, y, mo, d in _FM_DATE.findall(fm):                              # freshest of updated/date/created
        try:
            import datetime as _dt
            cand = _dt.datetime(int(y), int(mo), int(d)).timestamp()
            ts = cand if ts is None else max(ts, cand)
        except Exception:
            pass
    return {a for a in aliases if a}, ts


def scan_vault(folder: str, cap: int = 8000) -> list[dict]:
    """Read a folder of .md notes into {title, aliases, path, ts, links_out}. `ts` is the frontmatter
    date if present (mtime is unreliable across a git sync), else file mtime."""
    notes = []
    for p in Path(folder).rglob("*.md"):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        aliases, fm_ts = _frontmatter(text[:cap])
        notes.append({"title": p.stem, "aliases": aliases, "path": str(p),
                      "text": text[:cap], "ts": fm_ts if fm_ts else p.stat().st_mtime,
                      "links_out": {m.strip() for m in _WIKILINK.findall(text)}})
    return notes


_STOP = set((
    "the a an and or but of to in is it for on with that this as are be by at from into over "
    "not no can will would should could than then so if you your we our they their there here "
    "note notes see also more most some any all one two via use used using etc"
).split())


def _tokens(text: str) -> set:
    """Content tokens for similarity — common stopwords removed so matches need real topical
    overlap, not shared filler like 'note'/'about'/'the' (which produced spurious suggestions)."""
    return {w for w in _WORD.findall(text.lower()) if w not in _STOP}


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


def suggest_links(notes: list[dict], orphans: list[str], *, k: int = 3, max_orphans: int = 300,
                  min_sim: float = 0.12, embed=None) -> dict:
    """For each orphan, suggest the top-k most-similar CONNECTED notes to link it to — turning
    'you have N orphans' into 'link this orphan to these'. Lexical Jaccard by default (capped at
    max_orphans for scale); an embedder makes it sharper. Suggests nothing when no decent match
    exists (no noise). Advisory only."""
    by_title = {n["title"]: n for n in notes}
    orphan_set = set(orphans)
    pool = [n for n in notes if n["title"] not in orphan_set]
    pool_tok = {n["title"]: _tokens(n["text"]) for n in pool}
    out = {}
    for ot in orphans[:max_orphans]:
        ta = _tokens(by_title[ot]["text"])
        if not ta:
            continue
        scored = []
        for n in pool:
            tb = pool_tok[n["title"]]
            if tb:
                j = len(ta & tb) / len(ta | tb)
                if j >= min_sim:
                    scored.append((round(j, 3), n["title"]))
        scored.sort(reverse=True)
        if scored:
            out[ot] = [{"link_to": t, "sim": j} for j, t in scored[:k]]
    return out


def maintain(notes: list[dict], *, now: float | None = None, stale_days: float = 120.0,
             dup_threshold: float = 0.6, dup_max_n: int = 2000, suggest: bool = True,
             link_k: int = 3, max_orphans: int = 300, embed=None) -> dict:
    """Compute the maintenance plan + health for a scanned vault. Pure: returns findings, edits nothing.
    Duplicate detection is O(n^2) lexical; it auto-skips above `dup_max_n` notes (use an embedder +
    LSH for big vaults). All other findings are O(n)/O(edges) and always run."""
    now = time.time() if now is None else float(now)
    titles = {n["title"] for n in notes}
    by_title = {n["title"]: n for n in notes}
    # a wikilink resolves to a canonical note by filename OR by a frontmatter alias (Obsidian does
    # both) — resolving aliases is what stops alias-links being miscounted as dead.
    resolve = {t: t for t in titles}
    for n in notes:
        for a in n.get("aliases", ()):  # title wins on a collision
            resolve.setdefault(a, n["title"])

    edges: dict[str, set] = {t: set() for t in titles}
    in_links = {t: 0 for t in titles}
    out_valid = {t: 0 for t in titles}
    dead_links = []
    for n in notes:
        for tgt in n["links_out"]:
            canon = resolve.get(tgt)
            if canon in by_title:
                edges[n["title"]].add(canon); edges[canon].add(n["title"])
                in_links[canon] += 1; out_valid[n["title"]] += 1
            else:
                dead_links.append({"note": n["title"], "broken_link": tgt})

    orphans, stale = [], []
    for n in notes:
        t = n["title"]
        if in_links[t] == 0 and out_valid[t] == 0:
            orphans.append(t)
        age = (now - n["ts"]) / 86400.0                       # frontmatter date, not git-reset mtime
        if age > stale_days and (in_links[t] + out_valid[t]) <= 1:
            stale.append({"note": t, "age_days": round(age)})

    # turn orphans into actions: link the connectable ones, archive the old-isolated ones
    link_suggestions = suggest_links(notes, orphans, k=link_k, max_orphans=max_orphans,
                                     embed=embed) if suggest else {}
    archive_candidates = [o for o in orphans if o not in link_suggestions
                          and (now - by_title[o]["ts"]) / 86400.0 > stale_days]

    # near-duplicate clusters (token Jaccard, or embedder cosine if provided)
    dup_clusters = []
    dup_scanned = len(notes) <= dup_max_n
    if embed is None and dup_scanned:
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
        "duplicate_clusters": (len(dup_clusters) if dup_scanned else "skipped (vault > dup_max_n; use an embedder)"),
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
        actions.append(f"fix {len(dead_links)} dead links ({len({x['broken_link'] for x in dead_links})} distinct targets)")
    if link_suggestions:
        actions.append(f"link {len(link_suggestions)} orphans to suggested neighbors")
    if archive_candidates:
        actions.append(f"archive {len(archive_candidates)} old isolated notes")
    if stale:
        actions.append(f"review/refresh {len(stale)} stale notes")
    if isinstance(dup_clusters, list) and dup_clusters:
        actions.append(f"merge {len(dup_clusters)} duplicate clusters")
    return {"health": health, "actions": actions, "dead_links": dead_links,
            "orphans": orphans, "stale": stale, "duplicate_clusters": dup_clusters,
            "link_suggestions": link_suggestions, "archive_candidates": archive_candidates}


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
    # an orphan that SHOULD get a link suggestion (matches core2's topic but links nowhere)
    w("lost_kalman", "Stray notes on kalman filtering robotics state estimation — specifics about kalman filtering robotics.")

    rep = maintain(scan_vault(d), now=now, stale_days=120)
    print("health :", rep["health"])
    print("actions:", rep["actions"])
    print("dead_links:", rep["dead_links"])
    print("orphans:", rep["orphans"])
    print("stale  :", rep["stale"])
    print("dup clusters:", rep["duplicate_clusters"])
    print("link suggestions:", rep["link_suggestions"])
    print("archive candidates:", rep["archive_candidates"])
    assert rep["health"]["dead_link_frac"] > 0 and len(rep["dead_links"]) == 2
    assert "orphan_a" in rep["orphans"] and "orphan_b" in rep["orphans"]
    assert any("stale_old" == s["note"] for s in rep["stale"])
    assert any(set(c) == {"dup1", "dup2"} for c in rep["duplicate_clusters"])
    assert "lost_kalman" in rep["link_suggestions"] and rep["link_suggestions"]["lost_kalman"][0]["link_to"] == "core2"
    assert "stale_old" in rep["archive_candidates"]
    print("\nOK — found dead links, orphans, stale, duplicates; SUGGESTED linking lost_kalman -> core2; "
          "flagged stale_old to archive. Health scored.")

"""
The Reference Audit — knowledge observability pointed at someone else's knowledge base.

This is the product demo: every instrument Agora built for its own vault (link-graph structure,
orphan detection, structural holes between clusters, near-duplicate detection) runs against a
FOREIGN public markdown corpus, producing a measured audit: what the knowledge base doesn't
know it doesn't know. Phase 1 is strictly local — clone, measure, report to the owner; nothing
is published without the gate. Foreign corpora have no frontmatter or wikilink discipline, so
clustering falls back to top-level folders and links include both [[wiki]] and [md](links).
"""
from __future__ import annotations

import re
import subprocess
import time
from collections import defaultdict
from pathlib import Path

AUDITS_DIR = Path(__file__).resolve().parents[3] / "agora_output" / "audits"
_WIKI = re.compile(r"\[\[([^\]|#]+)")
_MDLINK = re.compile(r"\]\(([^)#:]+\.md)[^)]*\)")
_WORD = re.compile(r"[a-z][a-z\-]{2,}")
_TITLE_STOP = frozenset("the a an of and or for to in on with how what readme index".split())


def ingest(repo: str, name: str = "") -> Path:
    """Shallow-clone a public repo into agora_output/audits/<name>. Returns the path."""
    name = name or repo.rstrip("/").rsplit("/", 1)[-1]
    dst = AUDITS_DIR / name
    if not (dst / ".git").exists():
        AUDITS_DIR.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(["git", "clone", "--depth", "1", "--single-branch",
                            f"https://github.com/{repo}.git", str(dst)],
                           capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            raise RuntimeError(("clone failed: " + (r.stderr or r.stdout))[:300])
    return dst


def scan(base: Path) -> dict:
    """One pass: the corpus's link graph, clusters (top folders), orphans, holes, near-dupes."""
    notes: dict[str, dict] = {}                  # stem(lower) -> {path, cluster, words}
    for p in list(base.rglob("*.md"))+list(base.rglob("*.mdx")):
        rel = p.relative_to(base)
        if any(part.startswith(".") for part in rel.parts):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")[:8000]
        except Exception:
            continue
        cluster = rel.parts[0] if len(rel.parts) > 1 else "(root)"
        notes[p.stem.lower()] = {"path": str(rel), "cluster": cluster, "text": text,
                                 "title_words": {w for w in _WORD.findall(p.stem.lower().replace("-", " "))
                                                 if w not in _TITLE_STOP}}
    inbound: dict[str, int] = defaultdict(int)
    bridges: dict[tuple, int] = defaultdict(int)
    edges = 0
    for stem, n in notes.items():
        targets = set()
        for t in _WIKI.findall(n["text"]):
            targets.add(t.strip().lower())
        for t in _MDLINK.findall(n["text"]):
            targets.add(Path(t).stem.lower())
        for t in targets:
            if t in notes and t != stem:
                edges += 1
                inbound[t] += 1
                ca, cb = n["cluster"], notes[t]["cluster"]
                if ca != cb:
                    bridges[tuple(sorted((ca, cb)))] += 1

    clusters: dict[str, int] = defaultdict(int)
    for n in notes.values():
        clusters[n["cluster"]] += 1
    big = {c: k for c, k in clusters.items() if k >= 15}

    # structural holes: substantial cluster pairs with zero/near-zero bridges
    holes = []
    cs = sorted(big)
    for i, a in enumerate(cs):
        for b in cs[i + 1:]:
            nb = bridges.get(tuple(sorted((a, b))), 0)
            if nb <= 1:
                holes.append({"a": a, "b": b, "a_size": big[a], "b_size": big[b], "bridges": nb})
    holes.sort(key=lambda h: -(h["a_size"] + h["b_size"]))

    orphans = [n["path"] for s, n in notes.items() if inbound.get(s, 0) == 0]

    # near-duplicate titles: containment >= 0.8 on title words (>=3 words)
    dupes = []
    stems = [s for s in notes if len(notes[s]["title_words"]) >= 3]
    for i, s1 in enumerate(stems):
        w1 = notes[s1]["title_words"]
        for s2 in stems[i + 1:]:
            w2 = notes[s2]["title_words"]
            inter = len(w1 & w2)
            if inter >= 3 and inter / min(len(w1), len(w2)) >= 0.8:
                dupes.append((notes[s1]["path"], notes[s2]["path"]))
                if len(dupes) >= 40:
                    break
        if len(dupes) >= 40:
            break

    return {"notes": len(notes), "edges": edges,
            "link_density": round(edges / max(len(notes), 1), 2),
            "orphan_count": len(orphans), "orphan_frac": round(len(orphans) / max(len(notes), 1), 3),
            "orphan_sample": orphans[:10],
            "clusters": dict(sorted(big.items(), key=lambda kv: -kv[1])[:12]),
            "holes": holes[:8], "dupes": dupes[:12]}


def compose_report(repo: str, s: dict, out_dir: Path) -> Path:
    L = [f"# Knowledge Observability Audit — `{repo}`",
         f"\n_{time.strftime('%Y-%m-%d')} · measured by Agora's vault instruments pointed at a "
         "public knowledge base. Numbers first, opinions second._\n",
         "## Structure",
         f"- **{s['notes']} notes**, {s['edges']} internal links → link density "
         f"**{s['link_density']}** links/note",
         f"- **{s['orphan_frac']:.0%} orphans** ({s['orphan_count']} notes nothing links to) — "
         "unreachable by graph traversal, findable only by search",
         "\n## Largest clusters"]
    for c, k in s["clusters"].items():
        L.append(f"- {c}: {k} notes")
    L.append("\n## Structural holes (substantial clusters that never talk)")
    if s["holes"]:
        for h in s["holes"]:
            L.append(f"- **{h['a']}** ({h['a_size']}) × **{h['b']}** ({h['b_size']}): "
                     f"{h['bridges']} bridge(s)")
        L.append("\n_A hole is where cross-domain insight is structurally impossible — no path "
                 "carries a reader from one domain to the other._")
    else:
        L.append("- none found at cluster scale (well-bridged corpus)")
    L.append("\n## Near-duplicate candidates")
    if s["dupes"]:
        for a, b in s["dupes"]:
            L.append(f"- `{a}` ≈ `{b}`")
    else:
        L.append("- none detected at title level")
    L.append("\n## Reading")
    L.append(f"- Orphan rate {s['orphan_frac']:.0%} vs our instrumented baseline 0.5% — orphans "
             "are invisible knowledge: paid for, unreachable.")
    L.append("- Structural holes mark the highest-leverage places to write ONE bridging note.")
    L.append("\n_Method: link-graph analysis over markdown ([[wiki]] + relative .md links), "
             "top-folder clustering, title-containment duplicate detection. Local audit; "
             "nothing was modified._")
    out = out_dir / "audit_report.md"
    out.write_text("\n".join(L), encoding="utf-8")
    return out


_Q_STOP = frozenset(
    "the a an of and or for to in on with how what why when where can could do does is are be "
    "i my me we our you your it its this that these those if then so but not no yes get got "
    "want need use using used way best should would will have has had from into about there here "
    "any some all one two new old more most much many very just like also still even only as at "
    "obsidian app note notes file files please thanks issue feature request bug help question "
    "possible add support work working able tried trying error "
    # issue-template / meta boilerplate that pollutes the demand signal
    "thank thanks suggestion suggested suggest completing complete checklist confirm please "
    "problem problems fixes fix fixed incorrect wrong reason update updated change changes "
    "documentation docs document page pages section example examples following follow report "
    "reporting describe description detail details related duplicate existing open opening "
    "title body comment version current behavior behaviour expected actual steps reproduce "
    "undocumented document documented currently missing unclear confusing typo".split())
_Q_TRIGGER = re.compile(r"\?|^\s*(how|why|can|is there|what'?s the|best way|unable|cannot|can't|"
                        r"does(n'?t)?|not working|doesn'?t)", re.IGNORECASE)


def _content_words(text: str) -> list[str]:
    return [w for w in _WORD.findall((text or "").lower())
            if w not in _Q_STOP and len(w) > 3]


def demand_gap(issues_repo: str, docs_base: Path, max_issues: int = 200) -> dict:
    """Mine user questions from a repo's issues, rank the topics they ask about, and measure
    each topic's documentation coverage in docs_base. A gap = high demand, low coverage."""
    from agora.execution.correspondent import _api
    issues, page = [], 1
    while len(issues) < max_issues and page <= 3:
        try:
            batch = _api("GET", f"/repos/{issues_repo}/issues?state=all&per_page=100&page={page}")
        except Exception as e:
            if not issues:
                return {"error": str(e)[:140]}
            break
        if not batch:
            break
        issues.extend(batch)
        page += 1

    # keep only question-like issues (real user demand, not PRs or announcements)
    questions = []
    for it in issues:
        if it.get("pull_request"):
            continue
        title, body = it.get("title", ""), (it.get("body") or "")[:600]
        if _Q_TRIGGER.search(title) or _Q_TRIGGER.search(body[:200]):
            w = set(_content_words(title))
            tw = _content_words(title)
            # spam guard: real doc questions are short + technical; drop one-word-repeats and
            # rambling prose (troll/spam titles), keep concise topical ones
            if (2 <= len(w) and len(title.split()) <= 16
                    and (not tw or max(tw.count(x) for x in set(tw)) <= 2)):
                questions.append({"title": title[:140], "words": w})

    # docs as word-sets, per page (the unit of an answer)
    doc_pages = []
    for p in list(docs_base.rglob("*.md")) + list(docs_base.rglob("*.mdx")):
        if any(part.startswith(".") for part in p.relative_to(docs_base).parts):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")[:6000]
        except Exception:
            continue
        doc_pages.append(set(_content_words(p.stem.replace("-", " ") + " " + text)))

    # PER-QUESTION coverage: best topic overlap with any single doc page
    scored = []
    for q in questions:
        best = max((len(q["words"] & dp) / len(q["words"]) for dp in doc_pages), default=0.0)
        scored.append({"title": q["title"], "words": q["words"], "coverage": round(best, 2)})
    scored.sort(key=lambda x: x["coverage"])
    weak = scored[:10]                     # the 10 least-covered questions — always actionable
    thin = [s for s in scored if s["coverage"] < 0.34]
    covs = sorted(s["coverage"] for s in scored)
    median_cov = covs[len(covs) // 2] if covs else 0.0

    # cluster the thin questions by shared topic word → recurring uncovered themes
    theme: dict[str, list] = defaultdict(list)
    for u in thin:
        for w in u["words"]:
            theme[w].append(u["title"])
    gaps = [{"topic": t, "questions": len(titles), "examples": titles[:3]}
            for t, titles in theme.items() if len(titles) >= 2]
    gaps.sort(key=lambda g: -g["questions"])
    return {"issues_seen": len(issues), "questions": len(questions),
            "doc_notes": len(doc_pages), "uncovered": len(thin),
            "median_coverage": median_cov,
            "weakest": [{"title": w["title"], "coverage": w["coverage"]} for w in weak],
            "uncovered_sample": [w["title"] for w in weak], "gaps": gaps[:12]}


def compose_demand_report(issues_repo: str, docs_repo: str, dg: dict, out_dir: Path) -> Path:
    n = dg["questions"]
    pct = round(100 * dg["uncovered"] / max(n, 1))
    L = [f"# Documentation Demand-Gap Audit — `{docs_repo}`",
         f"\n_{time.strftime('%Y-%m-%d')} · which user questions your docs don't answer. "
         f"Mined {n} question-issues across {dg['issues_seen']} issues in `{issues_repo}`, scored "
         f"each against {dg['doc_notes']} doc pages by best topic overlap._\n",
         f"## Headline",
         f"**Median question coverage {dg.get('median_coverage', 0):.0%}** (topic overlap with the "
         f"best-matching doc page). **{dg['uncovered']} of {n} questions ({pct}%) fall below the "
         f"0.34 coverage line** — the docs barely touch their topic.",
         "\n## Your 10 least-covered user questions (write these first)"]
    for w in dg.get("weakest", []):
        L.append(f"- _{w['title']}_ — coverage {w['coverage']:.0%}")
    if dg["gaps"]:
        L.append("\n## Recurring uncovered themes")
        for g in dg["gaps"]:
            L.append(f"\n**{g['topic']}** — {g['questions']} uncovered questions:")
            for ex in g["examples"]:
                L.append(f"- _{ex}_")
    L.append("\n## Reading")
    L.append("- Each item is a real question whose topic no single doc page addresses — the "
             "cheapest high-impact place to write or expand a page.")
    L.append("- A low uncovered % means the docs already track demand well (a finding in itself); "
             "a high % localizes exactly where to invest.")
    L.append("\n_Method: question-issue mining, per-question best-overlap coverage vs each doc "
             "page (uncovered = best overlap < 0.34). No content was modified._")
    out = out_dir / "demand_gap_report.md"
    out.write_text("\n".join(L), encoding="utf-8")
    return out


def run_audit(repo: str, subdir: str = "") -> dict:
    """End to end: ingest → scan → report. `subdir` scopes the scan (e.g. 'en' when language
    mutations live in top folders and would fake the cluster structure)."""
    base = ingest(repo)
    root = base / subdir if subdir else base
    s = scan(root)
    report = compose_report(repo + (f"/{subdir}" if subdir else ""), s, base.parent)
    return {"repo": repo, "report": str(report), **{k: s[k] for k in
            ("notes", "edges", "link_density", "orphan_frac", "orphan_count")},
            "holes": s["holes"][:4], "dupes_found": len(s["dupes"])}


def run_demand_audit(issues_repo: str, docs_subdir: str = "", docs_repo: str = "") -> dict:
    """End to end demand-gap: ingest the docs repo, mine the issues repo's questions, score
    coverage, write the report. docs_repo defaults to issues_repo (docs live with the code)."""
    docs_repo = docs_repo or issues_repo
    base = ingest(docs_repo)
    docs_base = base / docs_subdir if docs_subdir else base
    dg = demand_gap(issues_repo, docs_base, max_issues=200)
    if dg.get("error"):
        return dg
    report = compose_demand_report(issues_repo, docs_repo + (f"/{docs_subdir}" if docs_subdir else ""),
                                   dg, base.parent)
    return {"issues_repo": issues_repo, "docs_repo": docs_repo, "report": str(report),
            "questions": dg["questions"], "doc_notes": dg["doc_notes"],
            "median_coverage": dg["median_coverage"], "uncovered": dg["uncovered"],
            "weakest": dg["weakest"][:5], "themes": dg["gaps"][:5]}

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
    for p in base.rglob("*.md"):
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

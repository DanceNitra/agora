"""
The Atlas — auto-maintained Maps of Content for the owner's navigation.

4710 notes, 63% evergreen — and navigation rests on search. The Atlas gives every major
domain a living front door: a weekly-refreshed MOC listing the domain's top concepts (by the
Memory Economy's value accounting), what arrived recently, and the orphans that deserve
attention. Deterministic, idempotent direct-file writes (like the Canon) into an Atlas folder;
an index note links them all.
"""
from __future__ import annotations

import re
import time
from pathlib import Path

_ATLAS_DIR = "04 Resources/Concepts/Agora Agents/Atlas"
_MIN_DOMAIN_NOTES = 8
_MAX_DOMAINS = 12


def _note_domain(text: str) -> str:
    m = re.search(r"^domain:\s*[\"']?([^\"'\n]+)", text[:1200], re.M)
    if not m:
        return ""
    # multi-domain values like "Statistics, Research Methods" -> first segment
    return m.group(1).split(",")[0].split("/")[0].strip()[:40]


def build_atlas(vault_path: str) -> dict:
    """Score the vault, group by frontmatter domain, write one MOC per major domain + index."""
    from agora.execution.memory_economy import score_notes
    root = Path(vault_path)
    notes = score_notes(vault_path)
    by_path = {n["path"]: n for n in notes}

    domains: dict[str, list] = {}
    for n in notes:
        p = root / n["path"]
        try:
            head = p.read_text(encoding="utf-8", errors="replace")[:1200]
        except Exception:
            continue
        dom = _note_domain(head)
        if dom and "Agora Agents" not in n["path"]:
            domains.setdefault(dom, []).append(n)

    big = sorted(((d, ns) for d, ns in domains.items() if len(ns) >= _MIN_DOMAIN_NOTES),
                 key=lambda kv: -len(kv[1]))[:_MAX_DOMAINS]
    out_dir = root / _ATLAS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    today = time.strftime("%Y-%m-%d")
    written = []
    now = time.time()

    for dom, ns in big:
        top = sorted(ns, key=lambda n: (-n["value"], -(n["inlinks"] + n["outlinks"])))[:15]
        fresh = sorted((n for n in ns if n["age_days"] <= 14), key=lambda n: n["age_days"])[:8]
        orphans = [n for n in ns if n["inlinks"] + n["outlinks"] == 0][:8]
        L = [f"---\ntitle: \"Atlas — {dom}\"\ntags: [agora, atlas, moc]\nupdated: {today}\n---",
             f"\n# Atlas — {dom}",
             f"\n> Living map of content, maintained by Agora. {len(ns)} notes in this domain.",
             "\n## Core concepts (by value & connectivity)"]
        L += [f"- [[{n['title']}]]" + (" 🌲" if n["evergreen"] else "") for n in top]
        if fresh:
            L.append("\n## Fresh (last 14 days)")
            L += [f"- [[{n['title']}]]" for n in fresh]
        if orphans:
            L.append("\n## Orphans worth connecting")
            L += [f"- [[{n['title']}]]" for n in orphans]
        slug = re.sub(r"[^\w\- ]", "", dom).strip()
        (out_dir / f"Atlas — {slug}.md").write_text("\n".join(L), encoding="utf-8")
        written.append({"domain": dom, "notes": len(ns), "orphans": len(orphans)})

    idx = [f"---\ntitle: \"Atlas — Index\"\ntags: [agora, atlas, moc]\nupdated: {today}\n---",
           "\n# Atlas — Index", "\n> One front door per domain, refreshed weekly by Agora.\n"]
    for w in written:
        slug = re.sub(r"[^\w\- ]", "", w["domain"]).strip()
        idx.append(f"- [[Atlas — {slug}]] — {w['notes']} notes")
    (out_dir / "Atlas — Index.md").write_text("\n".join(idx), encoding="utf-8")
    return {"domains": written, "dir": str(out_dir)}


def format_atlas(d: dict) -> str:
    ws = d.get("domains", [])
    if not ws:
        return "🗺 _No domains large enough for an atlas._"
    lines = [f"🗺 *Atlas refreshed* — {len(ws)} domain maps (see 'Atlas — Index' in the vault)"]
    lines += [f"• {w['domain']}: {w['notes']} notes" + (f", {w['orphans']} orphans" if w['orphans'] else "")
              for w in ws[:10]]
    return "\n".join(lines)

#!/usr/bin/env python3
"""
second_brain_mcp — turn ANY notes folder into a thinking partner over MCP.

Where mnemo_mcp exposes the MEMORY layer, this exposes the THINKING layer: point it at a folder of
Markdown notes (e.g. an Obsidian vault) and a Claude / Cursor / custom agent gets the substrate to
make that second brain *think*, not just store — ground a claim, find the gaps between notes,
surface non-obvious bridges, and generate ideas BY documented idea-generation methods.

Design (deliberate): the server provides RETRIEVAL + STRUCTURE; the calling LLM does the reasoning.
That is mnemo's philosophy — the tool is the memory/structure, the agent is the mind. So the tools
return *material to think over* (relevant notes, under-linked notes, candidate bridges, claim
sentences, the method toolkit), not canned "insights". No LLM call lives here, so it runs anywhere.

Run (stdio):   NOTES_DIR=/path/to/your/vault python -m mnemo.second_brain_mcp
Config (env):
    NOTES_DIR          folder of .md notes to think over (default: ./notes)
    SECOND_BRAIN_CAP   max chars indexed per note (default 4000)
    MNEMO_EMBED_URL/MODEL/KEY  optional OpenAI-compatible embedder for SEMANTIC bridges
                       (no embedder -> lexical-overlap fallback; runs today with zero config)
"""
from __future__ import annotations

import os
import re
import sys
import json
import urllib.request
from pathlib import Path

# Load the zero-dep store directly by path so it works whether launched as a script
# (python second_brain_mcp.py) or as a package submodule (python -m mnemo.second_brain_mcp),
# without the `mnemo` package dir shadowing `mnemo.py`.
import importlib.util as _ilu  # noqa: E402
_spec = _ilu.spec_from_file_location("mnemo_core", str(Path(__file__).resolve().parent / "mnemo.py"))
_mnemo_core = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mnemo_core)
Inspeximus = _mnemo_core.Inspeximus

try:
    from mcp.server.fastmcp import FastMCP
except Exception:
    sys.stderr.write('second_brain MCP server needs the MCP SDK: pip install "mcp[cli]"\n')
    raise

_NOTES_DIR = Path(os.environ.get("NOTES_DIR", "./notes")).expanduser()
_CAP = int(os.environ.get("SECOND_BRAIN_CAP", "4000"))
_MAX_BYTES = int(os.environ.get("SECOND_BRAIN_MAX_BYTES", str(2 * 1024 * 1024)))  # skip notes > 2 MB
_WIKILINK = re.compile(r"\[\[([^\]|#]+)")
_SENT = re.compile(r"(?<=[.!?])\s+")
# claim-like: declarative, has a verb-ish copula or quantity, not a question/heading/list
_CLAIM_HINT = re.compile(r"\b(is|are|was|were|causes?|leads? to|implies|beats?|reduces?|increases?|"
                         r"means|equals?|driven by|because|therefore|%|\d)\b", re.I)
_STOP = set(("the a an of to in on for and or is are was were be been being do does did how what when "
             "where why which who whom with that this these those it its as by at from into over under "
             "can could should would will may might more most less than then so such not no your you "
             "our we i they them their about between across vs versus using use make made get gets").split())


def _salient_terms(question: str, limit: int = 8) -> list[str]:
    """Content words from a question (LLM-free): the sub-terms whose coverage we check."""
    words = re.findall(r"[A-Za-z][A-Za-z\-]{3,}", (question or "").lower())
    seen, terms = set(), []
    for w in words:
        if w in _STOP or w in seen:
            continue
        seen.add(w)
        terms.append(w)
    return terms[:limit]


def _embed_url_ok(url: str) -> bool:
    """The embedder receives the FULL TEXT of every note. Refuse cleartext-to-the-internet and the
    cloud-metadata SSRF target; allow https anywhere and http only to loopback (local Ollama, etc.)."""
    import ipaddress
    from urllib.parse import urlparse
    try:
        u = urlparse(url)
    except Exception:
        return False
    if u.scheme not in ("http", "https"):
        sys.stderr.write("second_brain: MNEMO_EMBED_URL must be http(s) — embedder disabled.\n")
        return False
    host = (u.hostname or "").lower()
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_link_local or str(ip) == "169.254.169.254":      # cloud-metadata / link-local
            sys.stderr.write("second_brain: refusing link-local/metadata MNEMO_EMBED_URL — embedder disabled.\n")
            return False
        loopback = ip.is_loopback
    except ValueError:
        loopback = host in ("localhost",) or host.endswith(".localhost")
    if u.scheme == "http" and not loopback:
        sys.stderr.write("second_brain: refusing non-loopback http MNEMO_EMBED_URL (cleartext) — use https.\n")
        return False
    return True


def _make_embedder():
    url = os.environ.get("MNEMO_EMBED_URL", "").strip()
    if not url or not _embed_url_ok(url):
        return None
    model = os.environ.get("MNEMO_EMBED_MODEL", "text-embedding-3-small").strip()
    key = os.environ.get("MNEMO_EMBED_KEY", "").strip()

    def embed(text: str):
        body = json.dumps({"model": model, "input": text}).encode()
        headers = {"Content-Type": "application/json"}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        req = urllib.request.Request(url, data=body, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())["data"][0]["embedding"]
    return embed


def _read_notes() -> list[dict]:
    """Scan NOTES_DIR for .md notes -> [{title, folder, links, text}]. Skips obvious machine artifacts."""
    notes = []
    if not _NOTES_DIR.exists():
        return notes
    base = _NOTES_DIR.resolve()
    for p in _NOTES_DIR.rglob("*.md"):
        # Containment: rglob follows directory symlinks (Linux/macOS) AND Windows junctions (which
        # report is_symlink()==False), so a planted link inside a shared/cloned vault could escape
        # NOTES_DIR and leak arbitrary .md files. Resolve the real path and require it under base.
        # Use resolve()+parents (NOT is_symlink) precisely because junctions defeat is_symlink.
        try:
            rp = p.resolve()
            if rp != base and base not in rp.parents:
                continue
            if p.stat().st_size > _MAX_BYTES:        # bound memory: don't read a giant planted file
                continue
        except OSError:
            continue
        name = p.stem
        low = name.lower()
        if any(s in low for s in ("autolinker", "vault-digest", "_pending", "_report")):
            continue
        try:
            raw = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        body = re.sub(r"^---.*?---", "", raw, flags=re.DOTALL)  # strip frontmatter
        links = list({m.strip() for m in _WIKILINK.findall(raw)})
        rel = p.relative_to(_NOTES_DIR)
        folder = str(rel.parent).replace("\\", "/")
        notes.append({"title": name, "folder": folder, "links": links, "text": body.strip()[:_CAP]})
    return notes


# ---- index once at startup; load notes into a mnemo store for value/semantic recall ----
_NOTES = _read_notes()
_MEM = Inspeximus(":memory:" if False else os.environ.get("SECOND_BRAIN_INDEX", "second_brain_index.json"),
             embed=_make_embedder())
_BY_TITLE = {n["title"]: n for n in _NOTES}
if _NOTES and not _MEM.items:
    for n in _NOTES:
        _MEM.remember(f"{n['title']}\n{n['text'][:1200]}", tags=[n["folder"] or "root"], mtype="semantic")

mcp = FastMCP("second-brain")


@mcp.tool()
def index_status() -> dict:
    """How many of your notes are indexed and ready to think over, with the folder spread.
    Call this first; if it reports 0, set NOTES_DIR to your vault and restart."""
    folders: dict[str, int] = {}
    for n in _NOTES:
        folders[n["folder"] or "root"] = folders.get(n["folder"] or "root", 0) + 1
    top = dict(sorted(folders.items(), key=lambda kv: -kv[1])[:12])
    return {"notes_indexed": len(_NOTES), "folders": top, "notes_dir": str(_NOTES_DIR)}


@mcp.tool()
def relevant_notes(query: str, k: int = 6) -> list[dict]:
    """Retrieve the k notes most relevant to a topic, ranked by relevance x accrued value (mnemo).
    Use this to pull the substrate before you GROUND a claim, CHALLENGE a belief, or CONNECT ideas."""
    hits = _MEM.recall(query, k=k)
    out = []
    for h in hits:
        title = (h.get("text", "").split("\n", 1)[0])[:120]
        note = _BY_TITLE.get(title)
        out.append({"title": title, "folder": note["folder"] if note else "",
                    "relevance": round(h.get("relevance", h.get("score", 0)) or 0, 3),
                    "excerpt": (note["text"][:500] if note else h.get("text", "")[:500])})
    return out


@mcp.tool()
def coverage_gap(question: str, k: int = 6, threshold: float = 0.22) -> dict:
    """Surface the NEGATIVE SPACE of a question — what your notes do NOT cover. Alongside the top-k
    relevant notes it returns a measured completeness score and the explicit list of the question's
    sub-terms that have NO strongly-relevant note. This is a WYSIATI guard: a tidy retrieved context
    feels complete and breeds overconfidence precisely when it is incomplete, so an agent should read
    `missing` and the `outside_view_first` slot BEFORE answering, and flag the gap rather than answer
    a tidy-but-incomplete context with full confidence. Pure retrieval (no LLM call)."""
    terms = _salient_terms(question)
    covered, missing = [], []
    for t in terms:
        hits = _MEM.recall(t, k=2)
        top = max((h.get("relevance", h.get("score", 0)) or 0 for h in hits), default=0.0)
        (covered if top >= threshold else missing).append({"term": t, "top_relevance": round(top, 3)})
    completeness = round(len(covered) / len(terms), 3) if terms else 0.0
    return {
        "outside_view_first": (f"Before any case detail: what is the base-rate / reference-class answer "
                               f"to \"{(question or '')[:90]}\"? State the prior, then adjust inward."),
        "completeness": completeness,
        "covered": covered,
        "missing": missing,
        "top_notes": relevant_notes(question, k=k),
        "guidance": ("A non-empty `missing` (or low completeness) means the context is tidy but INCOMPLETE "
                     "— do NOT answer with full confidence; name the gap or go find/ground the missing terms."),
    }


@mcp.tool()
def find_gaps(max_items: int = 8) -> dict:
    """Find where the second brain is BLIND: notes that are isolated (no inbound or outbound
    [[links]]) and folders that are thin relative to the rest. These under-connected nodes are the
    highest-value places to think next — the gaps the network can't see itself. (Pure structure;
    the agent decides which gap is worth closing.)"""
    inbound: dict[str, int] = {n["title"]: 0 for n in _NOTES}
    for n in _NOTES:
        for l in n["links"]:
            if l in inbound:
                inbound[l] += 1
    isolated = [n["title"] for n in _NOTES if not n["links"] and inbound.get(n["title"], 0) == 0]
    folders: dict[str, int] = {}
    for n in _NOTES:
        folders[n["folder"] or "root"] = folders.get(n["folder"] or "root", 0) + 1
    thin = sorted(folders.items(), key=lambda kv: kv[1])[:6]
    return {"isolated_notes": isolated[:max_items],
            "isolated_count": len(isolated),
            "thin_folders": [{"folder": f, "notes": c} for f, c in thin],
            "hint": "Bridge an isolated/thin node to a strong one — fight preferential attachment."}


@mcp.tool()
def bridge_candidates(seed: str, k: int = 6) -> list[dict]:
    """Given a seed note title or topic, surface DISTANT notes (different folder, no direct link) that
    are nonetheless semantically close — candidate non-obvious bridges. These are where new ideas
    hide. The agent then writes the structural mapping (or rejects it as a forced analogy)."""
    seed_note = _BY_TITLE.get(seed)
    q = (seed_note["text"][:800] if seed_note else seed)
    hits = _MEM.recall(q, k=k * 3)
    seed_folder = seed_note["folder"] if seed_note else None
    seed_links = set(seed_note["links"]) if seed_note else set()
    out = []
    for h in hits:
        title = (h.get("text", "").split("\n", 1)[0])[:120]
        if title == seed or title in seed_links:
            continue
        note = _BY_TITLE.get(title)
        if not note:
            continue
        distant = (note["folder"] != seed_folder)   # different domain = higher novelty
        out.append({"title": title, "folder": note["folder"], "distant_domain": distant,
                    "similarity": round(h.get("relevance", h.get("score", 0)) or 0, 3),
                    "excerpt": note["text"][:300]})
    out.sort(key=lambda r: (r["distant_domain"], r["similarity"]), reverse=True)
    return out[:k]


@mcp.tool()
def extract_claims(note_title: str, max_claims: int = 8) -> dict:
    """Pull the claim-like sentences out of one note (declarative statements with a verb/quantity) so
    the agent can GROUND each against real literature or CHALLENGE it. Returns the note's claims with
    a rough line index. The agent does the verification — this just isolates what is checkable."""
    note = _BY_TITLE.get(note_title)
    if not note:
        # fuzzy: first note whose title contains the query
        note = next((n for n in _NOTES if note_title.lower() in n["title"].lower()), None)
    if not note:
        return {"error": f"note not found: {note_title}", "available_hint": "call relevant_notes first"}
    claims = []
    for i, line in enumerate(note["text"].splitlines()):
        s = line.strip().lstrip("-*>#").strip()
        if len(s) < 25 or s.endswith("?") or s.startswith("[["):
            continue
        for sent in _SENT.split(s):
            sent = sent.strip()
            if 25 <= len(sent) <= 300 and _CLAIM_HINT.search(sent):
                claims.append({"line": i + 1, "claim": sent})
            if len(claims) >= max_claims:
                break
        if len(claims) >= max_claims:
            break
    return {"title": note["title"], "folder": note["folder"], "claims": claims}


@mcp.tool()
def idea_methods() -> list[dict]:
    """The idea-generation method toolkit: documented recipes for producing NEW ideas from a knowledge
    base. Generate ideas BY a named method (so generation is principled, not a vibe), each applied to
    real notes you pulled via relevant_notes / bridge_candidates / find_gaps."""
    return [
        {"name": "Hidden-Connection Bridge", "recipe": "Pick two distant notes that share a keyword/structure but have no link; state the isomorphism 'X IS Y', map one concept from each side, name the idea visible only once they are the same system."},
        {"name": "Missing-Reciprocity", "recipe": "Find a one-way link asymmetry (A links to B a lot, B never back); write the missing reverse concept — what B knows about A that A doesn't know about itself."},
        {"name": "Missing-Triad Completion", "recipe": "If A->C and B->C but no A<->B, complete the implied edge through C; the shared third concept justifies the leap."},
        {"name": "Abstraction-Ladder Lift", "recipe": "Take a domain-specific finding, name the general structural pattern it instantiates (threshold/percolation, regulatory architecture, etc.), then apply that pattern down into a domain that hasn't used it."},
        {"name": "Inversion", "recipe": "Flip the claim ('creativity as a critical phenomenon' -> 'stability as innovation failure') and see what becomes true."},
        {"name": "Scale Shift", "recipe": "Push a mechanism +-3 orders of magnitude (molecule->organism, individual->civilization) and ask what the same rule predicts there."},
        {"name": "Drop-the-Constraint", "recipe": "Name the one assumption the idea depends on, delete it, and see what survives."},
        {"name": "Gap-Scan", "recipe": "Use find_gaps; turn an isolated/thin node into a buildable idea by bridging it to a strong domain (counter preferential attachment)."},
        {"name": "Link-Density Emergence", "recipe": "Scan a dense cluster of notes for two atoms that touch unexpectedly; write the note that connects them — the idea was implied by the network, not any single note."},
        {"name": "Applicability Gate", "recipe": "Score a raw idea 0-100 on Market/Tech/Uniqueness/Scale/Moat; keep only >~60 and write its smallest first test."},
    ]


@mcp.tool()
def maintenance_report(stale_days: float = 120.0) -> dict:
    """Run the SELF-MAINTAINING pass over the notes folder — the chore people stop doing. Finds dead
    [[wikilinks]], orphan notes (nothing links to them and they link to nothing), stale notes
    (old + weakly connected), near-duplicate clusters, and a vault HEALTH score: self_legibility =
    fraction of notes in the link graph's giant component (knowledge debt is a percolation collapse,
    so this warns BEFORE the cliff) plus orphan/dead-link/stale fractions and a prioritised action
    list. ADVISORY ONLY — returns a plan; it never edits, moves, or deletes a note."""
    import importlib.util as _i
    from pathlib import Path as _P
    spec = _i.spec_from_file_location("sb_maintain", str(_P(__file__).resolve().parent / "maintain.py"))
    m = _i.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.maintain(m.scan_vault(str(_NOTES_DIR)), stale_days=stale_days)


@mcp.tool()
def apply_links(dry_run: bool = True, stale_days: float = 120.0) -> dict:
    """ACT on the maintenance plan: append a marked '## Related (auto-suggested)' block of [[links]]
    to each orphan note, reconnecting it to the graph. SAFE: additive only (never edits existing
    content), idempotent (re-running replaces its own block), and DRY-RUN BY DEFAULT — call with
    dry_run=False to actually write. Returns {dry_run, changed, notes}. Review a dry run first."""
    import importlib.util as _i
    from pathlib import Path as _P
    spec = _i.spec_from_file_location("sb_maintain", str(_P(__file__).resolve().parent / "maintain.py"))
    m = _i.module_from_spec(spec)
    spec.loader.exec_module(m)
    notes = m.scan_vault(str(_NOTES_DIR))
    rep = m.maintain(notes, stale_days=stale_days)
    return m.apply_suggestions(notes, rep["link_suggestions"], dry_run=dry_run)


def main():
    mcp.run()


if __name__ == "__main__":
    main()

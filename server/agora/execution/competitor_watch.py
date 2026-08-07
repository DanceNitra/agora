"""Watch what the competition SHIPS — the one external signal that can invalidate our moat overnight.

Everything else this system reads is either its own vault or arXiv. Both are the same pot: the vault is
what we already thought, and arXiv is what academics publish. Neither tells us that mem0 shipped a
revert command last Tuesday, and that is exactly the news that would make three of our claims false
while we kept repeating them.

Two sources per competitor, because they disagree in useful ways: GitHub releases (what they say they
shipped) and PyPI (what you can actually install, and when). We store a snapshot and report only the
DELTA — a watcher that re-reports the same state every cycle trains you to ignore it.

The keyword scan is the point: a release whose notes mention correction, revert, erasure, provenance or
determinism is a release that touches OUR axis, and those are flagged loudly rather than listed.
"""
from __future__ import annotations

import json
import re
import time
import urllib.request
from pathlib import Path

_STORE = Path(__file__).resolve().parents[2] / ".competitor_watch.json"

# (display name, github repo or "", pypi package or "")
COMPETITORS = [
    ("mem0", "mem0ai/mem0", "mem0ai"),
    ("Zep / Graphiti", "getzep/graphiti", "graphiti-core"),
    ("Letta", "letta-ai/letta", "letta"),
    ("Cognee", "topoteretes/cognee", "cognee"),
    ("Memobase", "memodb-io/memobase", "memobase"),
    ("LangMem", "langchain-ai/langmem", "langmem"),
    ("claude-mem", "thedotmack/claude-mem", ""),
    ("Supermemory", "supermemoryai/supermemory", ""),
    ("MemOS / MemTensor", "MemTensor/MemOS", "memoryos"),
    ("txtai", "neuml/txtai", "txtai"),
    ("Memanto", "moorcheh-ai/memanto", ""),
]

# Orgs that ship a competing memory product AND things we partner with. Their competitor repo is
# excluded by exact name; the rest of the org is NOT. langchain-ai is the live case: langmem competes
# with us, while langgraph is a partner that merged our integration docs (langchain-ai/docs#5019) and
# whose InMemoryStore we pass an operation-by-operation parity audit against. An org-wide rule here
# would have blacklisted the single best distribution channel we have.
_MIXED_ORGS = {"langchain-ai"}


def is_competitor_repo(repo: str) -> bool:
    """True when a GitHub repo belongs to a competing memory product.

    Used to keep competitors OUT of anywhere we offer help — the contribution shortlist and the
    scout's outreach candidates. Reading them is fine and this does not gate that: competitor_watch
    itself exists to learn from them, and scout.find_learning() is deliberately left unfiltered.
    What the owner rules out is HELPING them.

    Matches on the exact `owner/repo`, plus the whole org for single-product owners (so mem0ai/mem0-ts
    is caught, not just mem0ai/mem0). Orgs in _MIXED_ORGS match on the exact repo only.
    """
    r = (repo or "").strip().lower().strip("/")
    if not r or "/" not in r:
        return False
    known = {c[1].lower() for c in COMPETITORS if c[1]}
    if r in known:
        return True
    owner = r.split("/", 1)[0]
    return owner in {k.split("/", 1)[0] for k in known} - _MIXED_ORGS

# Words that mean "this release is on our axis" — the moat, not the feature list.
ON_OUR_AXIS = ("revert", "rollback", "undo", "supersede", "superseded", "correction", "correct a",
               "erasure", "erase", "hard delete", "hard-delete", "right to be forgotten", "gdpr",
               "tombstone", "receipt", "provenance", "attestation", "deterministic", "determinism",
               "no llm", "without an llm", "poison", "tamper", "audit log")


def _get(url: str, token: str = "", timeout: int = 20):
    req = urllib.request.Request(url, headers={"Accept": "application/json",
                                               "User-Agent": "agora-competitor-watch"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _github_latest(repo: str, token: str = "") -> dict:
    try:
        d = _get(f"https://api.github.com/repos/{repo}/releases/latest", token)
        return {"tag": d.get("tag_name", ""), "published": (d.get("published_at") or "")[:10],
                "name": (d.get("name") or "")[:120], "notes": (d.get("body") or "")[:4000]}
    except Exception:
        return {}


def _github_stars(repo: str, token: str = "") -> int:
    try:
        return int(_get(f"https://api.github.com/repos/{repo}", token).get("stargazers_count") or 0)
    except Exception:
        return 0


def _pypi_latest(pkg: str) -> dict:
    try:
        d = _get(f"https://pypi.org/pypi/{pkg}/json")
        v = d["info"]["version"]
        files = d["releases"].get(v) or []
        return {"version": v, "uploaded": (files[0].get("upload_time") or "")[:10] if files else ""}
    except Exception:
        return {}


def _hits(text: str) -> list:
    t = (text or "").lower()
    return sorted({w for w in ON_OUR_AXIS if w in t})


def _load() -> dict:
    try:
        return json.loads(_STORE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(d: dict) -> None:
    try:
        _STORE.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


def scan(token: str = "") -> dict:
    """Poll every competitor and return ONLY what changed since the last scan.

    First run records the baseline and reports nothing new — otherwise the first report is a wall of
    fifty 'changes' that are just the current state, and nobody reads the second one.
    """
    prev = _load()
    now = {}
    changes, on_axis = [], []

    for name, repo, pkg in COMPETITORS:
        cur = {"name": name}
        if repo:
            rel = _github_latest(repo, token)
            if rel:
                cur["gh_tag"] = rel.get("tag", "")
                cur["gh_published"] = rel.get("published", "")
                cur["gh_name"] = rel.get("name", "")
            cur["stars"] = _github_stars(repo, token)
        if pkg:
            pp = _pypi_latest(pkg)
            if pp:
                cur["pypi_version"] = pp.get("version", "")
                cur["pypi_uploaded"] = pp.get("uploaded", "")
        now[name] = cur

        old = prev.get(name) or {}
        if not old:
            continue                                   # baseline run: record, do not shout

        if cur.get("gh_tag") and cur.get("gh_tag") != old.get("gh_tag"):
            rel = _github_latest(repo, token)
            hits = _hits((rel.get("name", "") + " " + rel.get("notes", "")))
            item = {"who": name, "what": "github release", "from": old.get("gh_tag", "?"),
                    "to": cur["gh_tag"], "date": cur.get("gh_published", ""),
                    "title": cur.get("gh_name", ""), "on_our_axis": hits,
                    "url": f"https://github.com/{repo}/releases/tag/{cur['gh_tag']}"}
            changes.append(item)
            if hits:
                on_axis.append(item)
        if cur.get("pypi_version") and cur.get("pypi_version") != old.get("pypi_version"):
            changes.append({"who": name, "what": "pypi release", "from": old.get("pypi_version", "?"),
                            "to": cur["pypi_version"], "date": cur.get("pypi_uploaded", ""),
                            "url": f"https://pypi.org/project/{pkg}/{cur['pypi_version']}/"})
        # star velocity: only worth a line when it is a real move, not daily noise
        if old.get("stars") and cur.get("stars"):
            d = cur["stars"] - old["stars"]
            if d >= max(50, int(old["stars"] * 0.02)):
                changes.append({"who": name, "what": "stars", "from": old["stars"], "to": cur["stars"],
                                "delta": d})

    now["_scanned"] = time.time()
    _save(now)
    return {"changes": changes, "on_our_axis": on_axis, "watched": len(COMPETITORS),
            "baseline": not prev}


def format_report(res: dict) -> str:
    if res.get("baseline"):
        return f"👁 Competitor watch: baseline recorded for {res['watched']} projects."
    ch = res.get("changes") or []
    if not ch:
        return ""
    lines = [f"👁 *Competitor watch* — {len(ch)} change(s)"]
    for c in res.get("on_our_axis") or []:
        lines.append(f"⚠️ *{c['who']}* {c['to']} touches OUR axis: {', '.join(c['on_our_axis'])}\n{c['url']}")
    for c in ch:
        if c in (res.get("on_our_axis") or []):
            continue
        if c["what"] == "stars":
            lines.append(f"• {c['who']}: +{c['delta']} stars ({c['to']})")
        else:
            lines.append(f"• {c['who']} {c['what']}: {c['from']} → {c['to']} ({c.get('date','')})")
    return "\n".join(lines)

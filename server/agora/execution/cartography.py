"""
Cartography — the map of what the vault knows, and the holes in it.

Linking (Dame Elara) connects notes that are NEAR each other; nobody watched the shape of the
whole graph. The Cartographer does Burt's structural-hole analysis on the vault: cluster notes
by domain, count the bridges BETWEEN clusters, and surface the pair of substantial clusters
with the fewest honest connections — that's where a genuinely new idea is most likely to live
(brokerage across holes, not density within clusters). Each charted hole is ledgered; the
Cartographer's yield is measured later, by whether bridges actually appeared where he pointed.
"""
from __future__ import annotations

import json
import re
import time
import uuid
from collections import defaultdict
from pathlib import Path

_STORE = Path(__file__).resolve().parents[2] / ".cartography.json"
_LINK = re.compile(r"\[\[([^\]|#]+)")
_DOMAIN = re.compile(r"^domain:\s*[\"']?(.+?)[\"']?\s*$", re.MULTILINE)


def _load() -> list:
    try:
        return json.loads(_STORE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(items: list) -> None:
    try:
        _STORE.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


def _scan(vault: str) -> tuple[dict, dict, dict]:
    """One pass over the vault: note -> domain, domain -> notes, (domA,domB) -> bridge count."""
    base = Path(vault)
    note_domain: dict[str, str] = {}
    domain_notes: dict[str, list] = defaultdict(list)
    texts: dict[str, str] = {}
    for p in base.rglob("*.md"):
        if any(part.startswith(".") for part in p.parts):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")[:6000]
        except Exception:
            continue
        title = p.stem
        m = _DOMAIN.search(text[:600])
        # KNOWLEDGE domains come from frontmatter only — folder names (Daily, Archives,
        # Templates…) are organization, not domains, and made garbage "holes"
        dom = (m.group(1).strip() if m else "(unfiled)")[:40]
        note_domain[title.lower()] = dom
        domain_notes[dom].append(title)
        texts[title.lower()] = text
    bridges: dict[tuple, int] = defaultdict(int)
    for title, text in texts.items():
        da = note_domain.get(title)
        for target in _LINK.findall(text):
            db = note_domain.get(target.strip().lower())
            if da and db and da != db:
                bridges[tuple(sorted((da, db)))] += 1
    return note_domain, domain_notes, bridges


def find_hole(vault: str, min_cluster: int = 8) -> dict | None:
    """The pair of substantial domains with the FEWEST bridges (>=0) — the widest hole.
    Skips pairs already charted and still open."""
    _, domain_notes, bridges = _scan(vault)
    big = {d: ns for d, ns in domain_notes.items()
           if len(ns) >= min_cluster and d != "(unfiled)"}
    charted = {(x.get("a"), x.get("b")) for x in _load() if x.get("status") == "charted"}
    best = None
    doms = sorted(big)
    for i, a in enumerate(doms):
        for b in doms[i + 1:]:
            if (a, b) in charted or (b, a) in charted:
                continue
            n = bridges.get(tuple(sorted((a, b))), 0)
            score = n / min(len(big[a]), len(big[b]))     # bridges per unit of cluster mass
            if best is None or score < best["score"]:
                best = {"a": a, "b": b, "bridges": n, "score": score,
                        "a_size": len(big[a]), "b_size": len(big[b]),
                        "a_notes": big[a][:4], "b_notes": big[b][:4]}
    return best


#: Outcomes that only say the work STARTED. 68 of 80 entries sat here — a hypothesis nobody was
#: obliged to test, which is why the Cartographer scored as pure volume.
_UNTESTED = ("hypothesized", "", "charted")


def record_charted(a: str, b: str, bridges_then: int, note: str = "", outcome: str = "") -> dict:
    rec = {"id": uuid.uuid4().hex[:6],
           "a": (a or "")[:40], "b": (b or "")[:40], "bridges_then": int(bridges_then),
           "note": (note or "")[:200], "outcome": (outcome or "")[:200],
           "status": "charted", "ts": time.time()}
    items = _load()
    items.append(rec)
    _save(items[-300:])          # was [-80:] — the cap silently discarded charts before anyone
    return rec                   # could test them, so the backlog could never be worked down


def pick_untested_bridge() -> dict | None:
    """The oldest charted bridge that was hypothesized and never tested.

    Wren's organ produced 80 charts of which 68 ended at 'hypothesized' — a proposal with no consumer
    obliged to act on it. The chart was the artifact, and a chart changes nothing. This is the selector
    that gives those hypotheses a consumer: a bridge is now a claim awaiting a verdict, and the
    Cartographer's real output becomes 'this bridge holds' or 'there is no honest bridge' — the second
    of which he already produced 9 times and is a finding, not a failure.

    Skips entries with no id: those predate this change and cannot be resolved, so offering them would
    queue work that can never be closed.
    """
    return (pick_untested_bridges(1) or [None])[0]


def pick_untested_bridges(n: int = 8) -> list[dict]:
    """The n oldest unresolved bridges, oldest first — so a caller whose own gate refuses the head
    can WALK to the next instead of stopping.

    Returning a single target made this a dead end, and I shipped that dead end HOURS after fixing
    the identical one in the belief-challenge sweep. The dungeon's bridge bench applies a board gate
    the brain knows nothing about; when the gate refused the oldest bridge, the caller returned and
    that bridge — still the oldest unresolved — was re-offered and re-refused on every cycle
    thereafter. Same shape as _task_already_pending with no expiry, and as verify_contributions
    spending its budget on a wall of permanent failures at the front of the list. A selector must
    never hand out one item to a caller that is allowed to say no.
    """
    live = [r for r in _load()
            if r.get("id") and str(r.get("outcome", "")).strip().lower() in _UNTESTED]
    live.sort(key=lambda r: float(r.get("ts", 0) or 0))
    return live[:max(1, n)]


def resolve_bridge(bridge_id: str, outcome: str, note: str = "") -> dict | None:
    """Close a charted bridge with a verdict. Returns None on an unknown id rather than silently
    appending a new record — a resolve that quietly creates instead of updating is how a ledger fills
    with work nobody did."""
    if not (bridge_id or "").strip() or not (outcome or "").strip():
        return None
    items = _load()
    for r in items:
        if r.get("id") == bridge_id:
            r["outcome"] = outcome[:200]
            r["status"] = "resolved"
            r["resolved_ts"] = time.time()
            if note:
                r["note"] = f"{r.get('note', '')} || {note}"[:400]
            _save(items)
            return r
    return None


def measure_yield(vault: str) -> list[dict]:
    """The Cartographer's income: did bridges actually appear where he pointed?"""
    _, _, bridges = _scan(vault)
    items, changed = _load(), False
    for x in items:
        if x.get("status") != "charted":
            continue
        now = bridges.get(tuple(sorted((x["a"], x["b"]))), 0)
        if now > x.get("bridges_then", 0):
            x["status"] = "bridged"
            x["bridges_now"] = now
            x["bridged_ts"] = time.time()
            changed = True
    if changed:
        _save(items)
    return items


def format_cartography() -> str:
    items = _load()
    if not items:
        return "🗺 _No hole has been charted yet — the map is blank._"
    bridged = sum(1 for x in items if x.get("status") == "bridged")
    lines = [f"🗺 *The Cartographer* — {len(items)} holes charted · {bridged} since bridged"]
    for x in items[-6:][::-1]:
        icon = "🌉" if x.get("status") == "bridged" else "🕳"
        lines.append(f"{icon} {x['a']} × {x['b']} (bridges then: {x.get('bridges_then', 0)})")
        if x.get("outcome"):
            lines.append(f"    {x['outcome'][:70]}")
    return "\n".join(lines)

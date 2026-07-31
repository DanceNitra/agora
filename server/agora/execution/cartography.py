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
    # DO NOT CHART WHAT THE CONSUMER MUST REFUSE. The dungeon's bridge bench applies a board gate on
    # "<A> x <B>", so a pair whose two labels share no term with the board can never be worked --
    # charting it only grows a wall the selector then re-offers forever. Measured 2026-07-31: 68 such
    # charts accumulated and Wren refused the same eight every cycle. Starving here is the honest
    # outcome and is visible (find_hole returns None); a growing backlog of dead work is not.
    try:
        from agora.execution.board import priorities_text
        from agora.execution.methods import board_priority_terms, _theme_tokens
        _prio = board_priority_terms(priorities_text())
    except Exception:
        _prio = set()

    def _passes_board(a: str, b: str) -> bool:
        return (not _prio) or bool(_theme_tokens("%s x %s" % (a, b)) & _prio)

    # `charted` is matched on OUTCOME, not status: an entry recorded as "hypothesized" carries a
    # different status, so a status-only skip re-charted pairs that were already on the books.
    charted = {(x.get("a"), x.get("b")) for x in _load()
               if str(x.get("outcome", "")).strip().lower() in _UNTESTED
               or x.get("status") == "charted"}
    best = None
    doms = sorted(big)
    for i, a in enumerate(doms):
        for b in doms[i + 1:]:
            if (a, b) in charted or (b, a) in charted:
                continue
            if not _passes_board(a, b):
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


# ── THE RESEARCH MAP — holes in OUR OWN measured work ────────────────────────────────────────────
#
# `find_hole` maps the OWNER'S vault: domains from his `domain:` frontmatter, holes between them.
# That map is real, but it is not our research frontier, and the consumer's board gate refuses every
# pair it produces (measured 2026-07-31: 0 of 47 domain labels match the board, and all 68 charts it
# had accumulated were off-mission). So the Map-maker had a working algorithm pointed at the wrong
# corpus.
#
# FIVE candidate corpora were measured before this one, and each was rejected on evidence:
#   1. vault domain LABELS vs the board ............ 0/47 match
#   2. vault domain note CONTENT vs the board ...... 44/47 match -- noise; the board's terms are
#                                                    common words and classify nothing
#   3. note TITLES behind the eight oldest holes ... 0/8 match
#   4. our own 3,913 agent notes ................... 0 domains (they carry no `domain:` frontmatter)
#   5. shared TERMS over findings / lab records .... an ARTIFACT. "agent" labs and "recall" labs
#      showed zero overlap over 999 records, which looked like a spectacular research hole and was
#      verified by raw substring twice before the cause turned up: they are simply different method
#      templates (`method:info-cascade` vs `method:bandit-regret`). Word co-occurrence measures which
#      template was used, not what was studied.
#
# What survives is meaning, not vocabulary: EMBED the measured questions and cluster them. A domain
# is then a cluster of work that is actually about the same thing, whatever words it happened to use.
#
# Both thresholds are CALIBRATED, not chosen. Cluster: 0.42 collapses 188 of 225 into one blob, 0.58
# fragments to 36% coverage; 0.50 gives 12 domains covering 84%. Bridge: at 0.45 every pair bridges
# every pair (0 holes of 66 -- the word "hole" would mean nothing), at 0.70 almost nothing bridges
# (61 of 66); 0.60 leaves 24 of 66 genuinely unbridged.
_CLUSTER_THR = 0.50      # cosine floor for two measured questions to be the same domain
_BRIDGE_THR = 0.60       # cosine to a second domain's centroid that counts as spanning it
_MIN_DOMAIN = 5          # a cluster smaller than this is one study, not a domain
_EMBED_CHUNK = 48        # the embedder 400s on a batch of 225; 48 is under the limit


def _measured_questions(lab_path=None) -> list[dict]:
    """The distinct questions we have actually MEASURED, from the Lab ledger.

    The `method:<slug> ` prefix is stripped: it is the template artifact that defeated approach 5
    above, and leaving it in would cluster by template rather than by subject.
    """
    p = Path(lab_path) if lab_path else (Path(__file__).resolve().parents[2] / ".lab.json")
    try:
        recs = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []
    seen, out = set(), []
    for x in recs:
        if not (isinstance(x, dict) and x.get("ok")):
            continue
        name = str(x.get("name") or "")
        q = (name.split(" ", 1)[1] if " " in name else name).strip()
        key = q.lower()[:80]
        if len(q) < 25 or key in seen:
            continue
        seen.add(key)
        out.append({"q": q[:300], "lab_id": x.get("id")})
    return out


def research_map(lab_path=None) -> dict:
    """Cluster our measured questions into domains and count what bridges them.

    Returns {"domains": [{label, size, lab_ids}], "bridges": {"a|b": n}, "n_questions": int}.
    Returns an empty map (never raises) if the embedder is unavailable -- an unreachable embedder
    must starve this organ visibly, not fabricate a map from nothing.
    """
    import numpy as np
    from agora.execution.semantic_index import _embed_batch

    qs = _measured_questions(lab_path)
    if len(qs) < _MIN_DOMAIN * 2:
        return {"domains": [], "bridges": {}, "n_questions": len(qs),
                "note": "too few measured questions to map"}
    emb = []
    for i in range(0, len(qs), _EMBED_CHUNK):
        part = _embed_batch([x["q"] for x in qs[i:i + _EMBED_CHUNK]])
        if not part or len(part) != len(qs[i:i + _EMBED_CHUNK]):
            return {"domains": [], "bridges": {}, "n_questions": len(qs),
                    "note": "embedder unavailable -- no map rather than a guessed one"}
        emb.extend(part)
    v = np.array(emb, dtype=np.float32)
    v /= (np.linalg.norm(v, axis=1, keepdims=True) + 1e-9)
    sim = v @ v.T

    # Greedy clustering seeded by the most central question, so a domain's label is its most
    # representative measurement rather than whichever one happened to be first.
    assigned, clusters = {}, []
    for i in np.argsort(-sim.sum(1)):
        i = int(i)
        if i in assigned:
            continue
        members = [int(j) for j in np.argsort(-sim[i])
                   if int(j) not in assigned and sim[i][int(j)] >= _CLUSTER_THR]
        for j in members:
            assigned[j] = len(clusters)
        clusters.append(members)

    big = [(k, c) for k, c in enumerate(clusters) if len(c) >= _MIN_DOMAIN]
    cent = {}
    for k, c in big:
        m = v[c].mean(0)
        cent[k] = m / (np.linalg.norm(m) + 1e-9)
    domains = [{"key": k, "label": qs[c[0]]["q"][:90], "size": len(c),
                "lab_ids": [qs[j]["lab_id"] for j in c[:6]]} for k, c in big]
    bridges = {}
    for ai in range(len(big)):
        for bi in range(ai + 1, len(big)):
            ka, ca = big[ai]
            kb, cb = big[bi]
            n = (sum(1 for j in ca if float(v[j] @ cent[kb]) >= _BRIDGE_THR)
                 + sum(1 for j in cb if float(v[j] @ cent[ka]) >= _BRIDGE_THR))
            bridges["%d|%d" % (ka, kb)] = n
    return {"domains": domains, "bridges": bridges, "n_questions": len(qs)}


def find_research_hole(lab_path=None) -> dict | None:
    """The widest unbridged pair of domains in our own measured work, skipping charted ones.

    Ranked by bridges per unit of the SMALLER domain, so a pair of small clusters that genuinely
    never meet outranks a giant one that merely has proportionally few links.
    """
    m = research_map(lab_path)
    doms = {d["key"]: d for d in m.get("domains") or []}
    if len(doms) < 2:
        return None
    charted = {tuple(sorted((str(x.get("a")), str(x.get("b"))))) for x in _load()}
    # SAME RULE AS find_hole: never hand over a pair the consumer's board gate must refuse. Measured
    # on the live map -- 4 of 11 domain labels pass the board, so requiring ONE on-frontier side
    # still leaves a real supply, while charting an off-board pair would just rebuild the wall this
    # source exists to replace. Labels are truncated to 40 chars by `record_charted`, so the gate is
    # applied to the SAME string the consumer will see, not to the untruncated one.
    try:
        from agora.execution.board import priorities_text
        from agora.execution.methods import board_priority_terms, _theme_tokens
        _prio = board_priority_terms(priorities_text())
    except Exception:
        _prio = set()

    def _workable(la: str, lb: str) -> bool:
        return (not _prio) or bool(_theme_tokens("%s x %s" % (la[:40], lb[:40])) & _prio)

    best = None
    for pair, n in (m.get("bridges") or {}).items():
        ka, kb = (int(x) for x in pair.split("|"))
        a, b = doms[ka], doms[kb]
        if tuple(sorted((a["label"], b["label"]))) in charted:
            continue
        if not _workable(a["label"], b["label"]):
            continue
        score = n / max(1, min(a["size"], b["size"]))
        if best is None or score < best["score"]:
            best = {"a": a["label"], "b": b["label"], "bridges": n, "score": score,
                    "a_size": a["size"], "b_size": b["size"],
                    "a_labs": a["lab_ids"], "b_labs": b["lab_ids"],
                    "source": "research-map"}
    return best


def retire_off_board(reason: str = "", apply: bool = False) -> dict:
    """Close charts that the consumer's board gate can never pass, so the backlog can advance.

    A selector that hands out the OLDEST unresolved charts, to a caller allowed to refuse them, needs
    refusals to be recorded somewhere -- otherwise the same wall is re-offered forever. Measured
    2026-07-31: all 68 untested charts were off-frontier, the oldest eight were `Business x <domain>`
    aged 36-41 days, and Cartographer Wren walked and refused the identical eight every cycle.

    They are not badly chosen; they are honestly off-mission. `find_hole` enumerates pairs of the
    OWNER'S personal vault domains (Business, Physics, Linguistics), and that taxonomy is not the
    inspeximus frontier. Four ways of asking were measured before concluding it: the domain LABEL
    matched the board 0/47, the domains' note CONTENT matched 44/47 (noise, not signal -- the board's
    terms are common words), the note TITLES behind the eight oldest matched 0/8, and our own 3,913
    agent notes carry no `domain:` frontmatter to substitute (0 domains with >=8 notes).

    Reversible: sets outcome `off-board` and keeps the record. Dry-run by default.
    """
    items = _load()
    hit = [r for r in items
           if r.get("id") and str(r.get("outcome", "")).strip().lower() in _UNTESTED]
    if apply:
        now = time.time()
        for r in hit:
            r["outcome"] = "off-board"
            r["status"] = "off-board"
            r["resolved_ts"] = now
            r["note"] = ((r.get("note") or "") + " || RETIRED: " + (reason or "off the board"))[:400]
        _save(items)
    return {"retired": len(hit), "applied": bool(apply), "remaining_untested": 0 if apply else len(hit)}


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
    # AN EMPTY BACKLOG IS A CUE TO MAP, NOT TO IDLE. The vault-taxonomy source is exhausted by
    # construction (see the research-map header), so when nothing is left to test we chart the
    # widest hole in our OWN measured work and hand that over instead. Failing softly to [] is
    # deliberate: an unreachable embedder must show as starvation, never as an invented hole.
    if not live:
        try:
            h = find_research_hole()
            if h:
                rec = record_charted(h["a"], h["b"], h["bridges"],
                                     note=("no measured question spans these two domains "
                                           "(%d vs %d labs; receipts %s / %s)"
                                           % (h["a_size"], h["b_size"],
                                              ",".join((h.get("a_labs") or [])[:3]),
                                              ",".join((h.get("b_labs") or [])[:3]))))
                if rec:
                    live = [rec]
        except Exception:
            pass
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

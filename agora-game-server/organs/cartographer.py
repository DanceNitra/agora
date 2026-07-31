"""
Cartographer Wren's organ — the Map-maker.

WHY THIS FILE EXISTS (measured, 2026-07-31)
-------------------------------------------
Wren charts STRUCTURAL HOLES: pairs of vault domains that should connect and do not. Until this
organ existed she had no code of her own — all eight agents ran the identical generic loop — and the
numbers say what that cost:

  * ZERO discoveries attributed to her in the five days before this organ (batch audit); she does
    not appear once in `GET /brain/agent-activity`, while Kael, Voss, Rooke, Elara and Aldric all do.
  * Her contributions carried a BLANK `contributor_name`. Verified here: `DUNGEON_AGENT_IDS`
    (`server/agora/api/dungeon.py:22`) lists SIX agents — Cartographer Wren and Artificer Rooke are
    missing — and `UUID_TO_NAME` is built by inverting exactly that map, so her uuid resolves to
    nothing. Measured on the live stream: 4 of the last 25 discoveries carry a blank contributor and
    Wren's name appears on none of them.
  * `_BRAIN_ID["cartographer"]` (`mcp_server.py:1377`) points at NPC uuid `...0009`, which is not in
    `DUNGEON_AGENT_IDS` and therefore is never seeded — her memory writes 404'd silently.
  * The ledger shows the shape of the churn that filled the gap: 80 holes charted, 7 ever bridged,
    and 7 of the 8 oldest unresolved charts carry the note "forced-collision hypothesis". A chart is
    a proposal; nobody was obliged to act on it.

So this organ is deliberately built to be ABLE TO SAY NO. "no honest bridge" is a first-class,
decisive success. The vault-recombination engine that used to produce "Connect A<->B" quests was
REMOVED on 2026-06-19 for producing "combinatorial filler ... low-substance notes"
(`mcp_server.py:1673-1677`); nothing here may recreate it. A bridge is claimed only when real,
external literature carries it, measured against a null, in a re-runnable Lab script.

THE TEST
--------
A bridge between domains A and B is honest when the literature returned for a JOINT query about
both spans BOTH domains more often than the literature returned for each domain ALONE. The
single-domain corpora are the null: they give the ambient rate at which a paper about A happens to
mention B's vocabulary. A joint corpus that does not beat that null is word coincidence, not a
bridge — which is exactly how "moat-band excitons in two dimensions" (a real arXiv hit for
"AI Competitive Moat") would otherwise be sold as a connection.

Every number in the output comes out of the Lab script that computed it, not out of this module —
there is one implementation of the decision and it is the artifact we cite.
"""
from __future__ import annotations

import inspect
import json
import re
import time
from urllib.parse import quote

ORGAN = {
    "eid": "cartographer", "agent": "Cartographer Wren", "name": "Map-maker",
    "ledger": ".cartography.json",
    "decisive": ("forged", "no honest bridge"),
    "period_hours": 6.0,                      # ~4x/day
}

_BRAIN = "/api/v1/agent-os/brain"

#: Minimum real papers (joint + null corpora together) before ANY verdict is allowed. A sample-size
#: floor, not a threshold on a score — with less literature than this the honest answer is "idle",
#: not "no bridge".
_MIN_PAPERS = 3

#: Novelty threshold, taken verbatim from `server/agora/execution/finding_diversity.py:27`. That is
#: the calibrated repo-wide value; a local one would be a second, unmeasured standard.
_NOVELTY = 0.6

#: Candidates whose evidence was too thin to rule on, and when. Without this the oldest unresolved
#: chart is re-offered every cycle, three research calls are spent on it, and the organ never
#: advances past the head of the list — the "selector cannot advance" class this repo has already
#: paid for twice. Process-lifetime only: after a dungeon restart the worst case is one repeated
#: spend, and we still WALK the list, so a stuck head never blocks the rest.
_INCONCLUSIVE: dict = {}
_INCONCLUSIVE_COOLDOWN = 24 * 3600.0


# ── the board gate — a faithful port of `server/agora/execution/seminar.py:99` ────────────────────
# The dungeon's own `_gate_filter` is a plain bag-of-words overlap: it is NOT polarity-aware and does
# NOT split hyphenated compounds, so it accepts a hole on the strength of a word the owner wrote in
# order to DEMOTE it ("Finance/health/physics are ONLY test-beds"), and it fails a topic about an
# agent's MEMORY layer against a board that says "agent-memory integrity". The dungeon cannot import
# server code, so the good gate is ported here rather than approximated.

_BOARD_STOP = {
    "the", "and", "for", "that", "with", "this", "must", "every", "not", "our", "are", "its", "into",
    "from", "how", "what", "does", "than", "them", "they", "their", "research", "priorities", "owner",
    "standing", "old", "make", "prioritize", "deprioritize", "never", "only", "each", "answer", "better",
    "more", "most", "other", "some", "any", "system", "systems", "build", "using", "used", "work",
    # generic connectives a bridge headline shares with any prose — matching on these would pass
    # everything, which is how a gate comes to look like it is working while gating nothing.
    "bridge", "complex", "science", "sciences", "engine", "model", "models", "theory", "principle",
}

#: Clauses after these markers name what the board EXCLUDES, not what it wants.
_NEG_MARKERS = re.compile(
    r"\b(deprioriti[sz]e|de-prioriti[sz]e|only\s+test-?beds?|never\s+the\s+headline|"
    r"not\s+the\s+headline|off-?domain|avoid|exclude|do\s+not\s+advance)\b", re.I)


def _board_words(text: str) -> set:
    """Content words, with hyphenated compounds ALSO split into their parts."""
    out = set()
    for w in re.findall(r"[A-Za-z][A-Za-z\-]{2,}", text or ""):
        w = w.lower().strip("-")
        for part in [w] + (w.split("-") if "-" in w else []):
            if len(part) >= 4 and part not in _BOARD_STOP:
                out.add(part)
    return out


def _board_vocab(prio: str) -> tuple:
    """Split the priorities into wanted vocabulary and EXCLUDED vocabulary.

    Sentences carrying a negative marker contribute to the excluded set; everything else to the
    wanted set; a word in both is treated as excluded, because the demotion is the more specific
    instruction.
    """
    pos, neg = set(), set()
    for sent in re.split(r"(?<=[.;])\s+|\n", prio or ""):
        (neg if _NEG_MARKERS.search(sent) else pos).update(_board_words(sent))
    return pos - neg, neg


def _on_board(headline: str, prio: str) -> bool:
    """Does this hole share vocabulary with the owner's standing priorities?

    SOFT-FAILS OPEN when no priorities are set — a board that has never been used must not silence
    the organ — and is applied only where a hole is OPENED, never to what is already live.
    """
    if not (prio or "").strip():
        return True
    pos, neg = _board_vocab(prio)
    tw = _board_words(headline)
    if tw & neg and not (tw & pos):
        return False
    return bool(tw & pos)


# ── novelty — `_tokens` / `_containment` from finding_diversity.py, unchanged ─────────────────────
_STOP = set((
    "the a an of to in on and or for with that this from are is was were be been being it its as at "
    "by we our their they them not no does can will would could should which who whom whose into "
    "about between among across over under more most less than then thus also such these those some "
    "any each both either neither finding findings result results study studies paper papers source"
).split())


def _tokens(s: str) -> set:
    return {w for w in re.findall(r"[a-z0-9]+", (s or "").lower()) if len(w) > 3 and w not in _STOP}


def _containment(a: set, b: set) -> float:
    """Overlap coefficient — fraction of the SMALLER token set shared."""
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


# ── domain vocabulary for the span test ──────────────────────────────────────────────────────────
#: Words that name how a note is FILED rather than what it is about. A domain called "Biostatistics
#: Is the Applied Mathematics" must not contribute "applied" as a bridge term.
_GENERIC = {
    "applied", "general", "generic", "introduction", "overview", "notes", "note", "concepts",
    "concept", "resources", "resource", "domain", "domains", "topic", "topics", "misc", "other",
    "meta", "sessions", "session", "archive", "archives", "daily", "template", "templates",
    "index", "map", "maps", "list", "lists", "stuff", "things", "review", "reviews", "summary",
}


def _domain_terms(name: str, titles: list, cap: int = 14) -> list:
    """Vocabulary for one side of the hole: the domain NAME first, then the titles the vault
    semantically files near it.

    Hyphenated compounds are split into their parts, as the board gate does — the first cut kept
    them whole and emitted `pipeline-social-sciences---statistics` as a "term", a token no paper on
    earth contains, which burns a term slot and can only ever fail to match.

    The ledger's `note` field (the previously PROPOSED bridge, e.g.
    "bridge-causal-identification-is-the-shared-moat-of...") is deliberately NOT a source of terms.
    Testing a proposal with vocabulary lifted from the proposal is confirmation, not evidence.
    """
    def _clean(text: str) -> list:
        out = []
        for raw in re.findall(r"[A-Za-z][A-Za-z\-]{3,}", text or ""):
            raw = raw.lower().strip("-")
            # Only the PARTS: matching is word-prefix, so a part matches everything the whole
            # compound would, and the whole compound matches nothing else.
            for w in (raw.split("-") if "-" in raw else [raw]):
                if len(w) >= 4 and w not in _GENERIC and w not in _STOP and w not in _BOARD_STOP:
                    out.append(w)
        return out

    terms: list = []
    for w in _clean(name) + [w for t in titles for w in _clean(t)]:
        if w not in terms:
            terms.append(w)
        if len(terms) >= cap:
            break
    return terms


# ── the Lab script — the ONE implementation of the verdict ────────────────────────────────────────
_LAB_HEAD = '''"""Structural-hole bridge test (Cartographer Wren).

MODELS: whether two vault domains A and B are honestly bridged by the external literature. A paper
SPANS the hole when its title+abstract carries at least one term unique to A and one unique to B
(the two term sets are made disjoint first, so a word both domains share cannot span anything).

  observed  = span rate of the papers returned for a JOINT query about A and B
  null      = span rate of the papers returned for A ALONE and for B ALONE, i.e. the ambient rate
              at which a paper about one domain happens to mention the other's vocabulary

BRIDGE requires at least one spanning paper AND observed > null: a joint corpus that merely matches
the ambient rate is word coincidence. When the null itself spans at or above the joint rate the two
domains are already connected everywhere and this was never a hole (ALREADY BRIDGED). Below a
minimum null corpus the answer is INCONCLUSIVE, never "no bridge". Term matching is word-prefix,
never substring, so "moat" cannot be found inside an unrelated longer word.

Both outcomes are reachable, which is what makes this a test rather than a rubber stamp. Measured
2026-07-31 on the live research endpoint: the joint query for a connected pair (agent memory
retrieval / knowledge graph) returns 2 real papers that span both sides; the joint query for
"AI Competitive Moat" x "Biostatistics" returns 0.
"""
import json

'''

_LAB_BODY = '''

def _words(text):
    return set(re.findall(r"[a-z][a-z\\-]*", (text or "").lower()))


def _hits(text, terms):
    ws = _words(text)
    return sorted({t for t in terms if any(w == t or w.startswith(t) for w in ws)})


def _spans(corpus, a_terms, b_terms):
    out = []
    for p in corpus:
        ha = _hits(p.get("title", "") + " " + p.get("summary", ""), a_terms)
        hb = _hits(p.get("title", "") + " " + p.get("summary", ""), b_terms)
        if ha and hb:
            out.append({"title": p.get("title", ""), "cite": p.get("cite", ""),
                        "url": p.get("url", ""), "a_hits": ha, "b_hits": hb,
                        "strength": min(len(ha), len(hb))})
    out.sort(key=lambda s: (-s["strength"], s["title"]))
    return out


def _rate(k, n):
    """A rate with no denominator is not zero, it is absent. Printing 0/0 = 0.000 reads as a
    measured null when nothing was measured, which is how an empty corpus gets quoted as evidence."""
    return ("%.3f" % (k / n)) if n else "n/a"


A_TERMS = DATA["a_terms"]
B_TERMS = DATA["b_terms"]
joint = DATA["joint"]
null = DATA["a_only"] + DATA["b_only"]

js = _spans(joint, A_TERMS, B_TERMS)
ns = _spans(null, A_TERMS, B_TERMS)
nj, nn = len(joint), len(null)
rate_j = (len(js) / nj) if nj else 0.0
rate_n = (len(ns) / nn) if nn else 0.0

# The NULL corpus carries the negative evidence, so the sample-size floor applies to IT. A verdict
# of "no honest bridge" resting on one paper about one domain is an opinion with a number attached.
if nn < DATA["min_papers"]:
    verdict, cite = "INCONCLUSIVE", None
elif ns and rate_n >= rate_j:
    # Single-domain literature already carries both domains at least as often as the joint query:
    # the connection is ambient, so this was never a structural hole.
    verdict, cite = "ALREADY BRIDGED", ns[0]
elif js and rate_j > rate_n:
    verdict, cite = "BRIDGE", js[0]
else:
    verdict, cite = "NO BRIDGE", None

measured = ("joint-query span rate %d/%d (%s) vs single-domain null %d/%d (%s)"
            % (len(js), nj, _rate(len(js), nj), len(ns), nn, _rate(len(ns), nn)))

print("DOMAINS: %s  x  %s" % (DATA["a"], DATA["b"]))
print("A terms: %s" % ", ".join(A_TERMS))
print("B terms: %s" % ", ".join(B_TERMS))
print("MEASURED: %s" % measured)
for s in (js + ns)[:3]:
    print("  spans: %s [A:%s | B:%s]" % (s["title"][:70], ",".join(s["a_hits"][:3]),
                                         ",".join(s["b_hits"][:3])))
print("VERDICT: %s" % verdict)
print("RESULT_JSON: " + json.dumps({
    "verdict": verdict, "measured": measured,
    "joint_n": nj, "joint_spans": len(js), "rate_joint": round(rate_j, 3),
    "null_n": nn, "null_spans": len(ns), "rate_null": round(rate_n, 3),
    "citation": cite, "a_terms": A_TERMS, "b_terms": B_TERMS}, sort_keys=True))
'''


def _lab_code(payload: dict) -> str:
    """Assemble a self-contained, deterministic script: docstring, embedded data, computation.

    The data is embedded as a repr'd ASCII JSON string, so no paper title can break out of the
    literal, and the script re-runs identically forever without network access.
    """
    blob = repr(json.dumps(payload, ensure_ascii=True, sort_keys=True))
    return _LAB_HEAD + "import re\n\nDATA = json.loads(" + blob + ")\n" + _LAB_BODY


# ── ctx plumbing — tolerate a sync or async dispatcher ────────────────────────────────────────────
async def _call(fn, *args, **kwargs):
    if fn is None:
        return None
    r = fn(*args, **kwargs)
    if inspect.isawaitable(r):
        r = await r
    return r


def _accepts(fn, name: str) -> bool:
    try:
        return name in inspect.signature(fn).parameters
    except Exception:
        return False


def _ascii(s: str) -> str:
    """The console is cp1250 and Telegram copy is ASCII by convention. Applied to the control-plane
    strings (log line, title, why) only — never to `content`, because folding a real author's name
    would corrupt the citation we are supposed to be verifying."""
    return (s or "").encode("ascii", "replace").decode("ascii")


def _log(ctx, msg: str) -> None:
    """ASCII-only logging; the console is cp1250 and a stray glyph 500s the caller."""
    try:
        ctx.logger.info("[cartographer] " + _ascii(msg))
    except Exception:
        pass


class _Unreachable(Exception):
    """The brain could not be read on a call the verdict depends on."""


async def _get(ctx, path: str, required: bool = False):
    """GET, with the two critical reads marked `required`.

    An unreachable brain and an empty backlog are NOT the same fact. Swallowing both into None made
    a brain that raised on every call report `idle: no unresolved charts in the backlog` — a broken
    instrument reporting "nothing to do", which is the failure mode that lets an organ look healthy
    while doing nothing for five days. The dungeon's own `_brain_get_sync` returns None on any
    failure, so for these endpoints (which always return a dict when the brain is up) None means
    unreachable.
    """
    try:
        r = await _call(getattr(ctx, "brain_get", None), path)
    except Exception as e:
        if required:
            raise _Unreachable("brain GET %s raised %s" % (path, type(e).__name__))
        _log(ctx, "GET %s failed: %s" % (path, type(e).__name__))
        return None
    if required and not isinstance(r, dict):
        raise _Unreachable("brain GET %s returned no object" % path)
    return r


async def _post(ctx, path: str, body: dict, timeout: float = 20.0):
    fn = getattr(ctx, "brain_post", None)
    try:
        if _accepts(fn, "timeout"):
            return await _call(fn, path, body, timeout=timeout)
        return await _call(fn, path, body)
    except Exception as e:
        _log(ctx, "POST %s failed: %s" % (path, type(e).__name__))
        return None


def _recall_texts(r) -> list:
    """Normalize whatever the dispatcher's recall returns into a list of strings.

    `_recall_mem` in mcp_server.py returns ' | '-joined text; other wirings return dicts or lists.
    A novelty check that silently reads nothing would report every hole as new.
    """
    out: list = []
    if isinstance(r, str):
        out = [p.strip() for p in r.split(" | ")]
    elif isinstance(r, dict):
        for key in ("results", "memories", "hits", "items", "recall"):
            if isinstance(r.get(key), list):
                return _recall_texts(r[key])
        out = [str(r.get("text") or r.get("content") or "")]
    elif isinstance(r, (list, tuple)):
        for h in r:
            if isinstance(h, str):
                out.append(h)
            elif isinstance(h, dict):
                out.append(str(h.get("text") or h.get("content") or h.get("title") or ""))
    return [t for t in out if t and t.strip()]


def _flat(s, cap: int) -> str:
    """Collapse whitespace and cap. arXiv titles and abstracts carry newlines; one of them landing in
    a printed line would split the Lab's stdout in a place the parser does not expect."""
    return " ".join(str(s or "").split())[:cap]


def _papers(payload, cap: int) -> list:
    """Real papers out of a /brain/research response; the runner returns [{'error': ...}] on a miss."""
    out = []
    if not isinstance(payload, dict):
        return out
    for p in (payload.get("papers") or []):
        if not isinstance(p, dict) or p.get("error") or not _flat(p.get("title"), 200):
            continue
        title = _flat(p.get("title"), 200)
        byline = ", ".join(x for x in (_flat(p.get("authors"), 60),
                                       _flat(p.get("published"), 20)) if x)
        out.append({
            "title": title,
            "summary": _flat(p.get("summary"), 1200),
            "url": _flat(p.get("url"), 200),
            "cite": ("%s (%s)" % (title[:90], byline)) if byline else title[:90],
        })
        if len(out) >= cap:
            break
    return out


def _titles(payload, cap: int = 5) -> list:
    if not isinstance(payload, dict):
        return []
    return [_flat(r.get("title"), 120)
            for r in (payload.get("results") or [])[:cap] if isinstance(r, dict)]


def _idle(why: str) -> dict:
    return {"status": "idle", "decisive": False, "title": "", "content": "",
            "lab_id": None, "why": why[:300]}


# ── the cycle ─────────────────────────────────────────────────────────────────────────────────────
async def cycle(ctx) -> dict:
    """Chart one structural hole and rule on it. NEVER raises."""
    try:
        return await _cycle(ctx)
    except _Unreachable as e:
        _log(ctx, "unreachable: %s" % e)
        return {"status": "error", "decisive": False, "title": "", "content": "", "lab_id": None,
                "why": str(e)[:300]}
    except Exception as e:
        try:
            ctx.logger.exception("[cartographer] cycle failed")
        except Exception:
            pass
        return {"status": "error", "decisive": False, "title": "", "content": "", "lab_id": None,
                "why": ("cartographer organ raised %s: %s" % (type(e).__name__, e))[:300]}


async def _cycle(ctx) -> dict:
    agent = getattr(ctx, "agent", None) or ORGAN["agent"]

    # 1. THE BACKLOG. `targets` is the walkable list; `target` is only its head. The endpoint's own
    #    docstring warns that a caller with its own gate MUST walk the list — taking the head is the
    #    dead end that killed two organs for 42 days, because a gate that refuses the oldest chart
    #    refuses it again on every cycle forever.
    box = await _get(ctx, _BRAIN + "/cartography/untested", required=True)
    targets = [t for t in ((box or {}).get("targets") or []) if isinstance(t, dict) and t.get("id")]
    if not targets:
        head = (box or {}).get("target")
        targets = [head] if isinstance(head, dict) and head.get("id") else []
    if not targets:
        return _idle("no unresolved charts in the cartography backlog")

    # 2. THE BOARD GATE, on every candidate — so a refusal advances instead of stalling.
    # `required`: a board that has never been SET soft-fails open by design (an unused board must not
    # silence the organ), but a board that exists and could not be READ is a different fact — with no
    # priorities in hand every off-niche hole would sail through the gate. Unreadable => do not act.
    prio = str((await _get(ctx, _BRAIN + "/board", required=True)).get("priorities") or "")
    available, off_board, seen_before = len(targets), [], []
    evaluated = 0
    now = time.time()
    chosen = None
    for t in targets:
        evaluated += 1
        a, b = str(t.get("a") or "").strip(), str(t.get("b") or "").strip()
        if not a or not b:
            continue
        head = "%s x %s" % (a, b)
        # The ledger's `note` (the proposed bridge) is NOT gated on: it is our own advocacy text and
        # would let a hole pass on the strength of its own proposal.
        if not _on_board(head, prio):
            off_board.append(head)
            continue
        if now - float(_INCONCLUSIVE.get(t["id"], 0.0)) < _INCONCLUSIVE_COOLDOWN:
            seen_before.append(head + " (thin evidence, cooling down)")
            continue
        # 3. NOVELTY — do not re-chart a hole Wren has already charted (calibrated containment).
        try:
            mem = _recall_texts(await _call(getattr(ctx, "recall", None), "bridge %s" % head))
        except Exception:
            mem = []
        cand_tok = _tokens(head)
        if any(_containment(cand_tok, _tokens(m)) >= _NOVELTY for m in mem):
            seen_before.append(head + " (already charted)")
            continue
        chosen = t
        break

    # `available` is what the backlog offered, `evaluated` is how far down the list we walked before
    # one survived. Reporting only the first number would hide a gate that stalls on the head.
    _log(ctx, "candidates available=%d evaluated=%d off_board=%d skipped=%d chosen=%s"
         % (available, evaluated, len(off_board), len(seen_before),
            ("%s x %s" % (chosen.get("a"), chosen.get("b"))) if chosen else "none"))
    if chosen is None:
        return _idle("all %d candidate holes refused: %d off-board (%s), %d already charted/cooling"
                     % (available, len(off_board), "; ".join(off_board[:3]) or "-",
                        len(seen_before)))

    a, b = str(chosen["a"]).strip(), str(chosen["b"]).strip()
    head = "%s x %s" % (a, b)

    # 4. EVIDENCE. Vocabulary from the domain names plus what the vault files near them; papers from
    #    real external literature (OpenAlex + arXiv) for the joint query and for each domain alone.
    a_terms = _domain_terms(a, _titles(await _get(ctx, _BRAIN + "/vault-search?q=%s&k=5" % quote(a))))
    b_terms = _domain_terms(b, _titles(await _get(ctx, _BRAIN + "/vault-search?q=%s&k=5" % quote(b))))
    shared = set(a_terms) & set(b_terms)
    a_terms = [t for t in a_terms if t not in shared]
    b_terms = [t for t in b_terms if t not in shared]
    if not a_terms or not b_terms:
        _INCONCLUSIVE[chosen["id"]] = time.time()
        return _idle("%s: no vocabulary unique to one side (shared=%s) - nothing a paper could span"
                     % (head, ",".join(sorted(shared)[:4]) or "-"))

    # FAIR COMPARISON, and a query that actually retrieves. All three queries are built the same way
    # out of the same term lists, so the null is not handed a better query than the hypothesis.
    #
    # TWO terms per side, measured 2026-07-31 against the live endpoint: the search ANDs its terms,
    # so every extra term shrinks the result set to nothing. "competitive moat" -> 2 papers and
    # "biostatistics mathematics" -> 2, while the three-term versions of the same domains and the
    # raw label "Biostatistics Is the Applied Mathematics Competitive Moat" -> 0. A null corpus that
    # is empty because the query was too long is not evidence of a hole; it is a broken instrument,
    # and it would have reported "no honest bridge" on literature it never looked at.
    _QT = 2
    q_joint = " ".join(a_terms[:_QT] + b_terms[:_QT])
    joint = _papers(await _get(ctx, _BRAIN + "/research?q=%s&n=6" % quote(q_joint)), 6)
    a_only = _papers(await _get(ctx, _BRAIN + "/research?q=%s&n=4" % quote(" ".join(a_terms[:_QT]))), 4)
    b_only = _papers(await _get(ctx, _BRAIN + "/research?q=%s&n=4" % quote(" ".join(b_terms[:_QT]))), 4)
    if len(a_only) + len(b_only) < _MIN_PAPERS:
        _INCONCLUSIVE[chosen["id"]] = time.time()
        return _idle("%s: null corpus is %d papers (floor %d) - too little literature to rule on"
                     % (head, len(a_only) + len(b_only), _MIN_PAPERS))

    # 5. THE MEASUREMENT. The script owns the decision; this module only reads its result, so the
    #    number we publish and the number that was computed cannot drift apart.
    code = _lab_code({"a": a, "b": b, "a_terms": a_terms, "b_terms": b_terms,
                      "joint": joint, "a_only": a_only, "b_only": b_only,
                      "min_papers": _MIN_PAPERS})
    try:
        lab = await _call(getattr(ctx, "lab_run", None), "cartography-bridge-test %s" % head, code)
    except Exception as e:
        _INCONCLUSIVE[chosen["id"]] = time.time()
        return _idle("%s: lab_run raised %s - no runnable test, no claim" % (head, type(e).__name__))
    lab = lab if isinstance(lab, dict) else {}
    nested = lab.get("experiment") if isinstance(lab.get("experiment"), dict) else {}
    lab_id = str(lab.get("id") or nested.get("id") or "") or None
    out = str(lab.get("output") or lab.get("stdout") or "")
    if not lab.get("ok", bool(out)) or "RESULT_JSON:" not in out:
        _INCONCLUSIVE[chosen["id"]] = time.time()
        return _idle("%s: lab run produced no result (lab=%s) - no grounded number, no claim"
                     % (head, lab_id or "none"))
    try:
        # rsplit, not split: the script prints matched paper titles before the result line, and a
        # title containing the marker would otherwise hand the parser a line of prose.
        res = json.loads(out.rsplit("RESULT_JSON:", 1)[1].strip().splitlines()[0])
        if not isinstance(res, dict):
            raise ValueError("result is not an object")
    except Exception as e:
        _INCONCLUSIVE[chosen["id"]] = time.time()
        return _idle("%s: could not parse the lab result (%s)" % (head, type(e).__name__))

    verdict = str(res.get("verdict") or "")
    outcome = {"BRIDGE": "forged", "NO BRIDGE": "no honest bridge",
               "ALREADY BRIDGED": "already bridged"}.get(verdict, "")
    if not outcome:
        _INCONCLUSIVE[chosen["id"]] = time.time()
        return _idle("%s: lab returned %s on %d papers - leaving the chart open"
                     % (head, verdict or "no verdict", res.get("joint_n", 0) + res.get("null_n", 0)))

    # The measured sentence is emitted BY the script that computed it. Re-deriving it here is a
    # second implementation of the same arithmetic, and the two drift.
    measured = str(res.get("measured") or "")
    if not measured:
        _INCONCLUSIVE[chosen["id"]] = time.time()
        return _idle("%s: lab result carried no measured line" % head)
    cite = res.get("citation") or {}
    lab_ref = "lab %s" % (lab_id or "unrecorded")

    # 6. GROUNDING GATE. A verdict with neither a citation nor a recorded lab id is prose, and prose
    #    is what this whole organ exists to stop producing.
    if not lab_id and not cite.get("cite"):
        return _idle("%s: %s but neither a lab id nor a citation to stand on" % (head, outcome))

    lines = [
        "Structural hole: %s" % head,
        "",
        "VERDICT: %s (%s)" % (outcome, verdict),
        "MEASURED: %s [%s]" % (measured, lab_ref),
        "",
        "Method: a paper spans the hole when its title+abstract carries a term unique to each "
        "domain. The single-domain corpora are the null - the ambient rate at which a paper about "
        "one domain mentions the other's vocabulary. A joint corpus that does not beat that null is "
        "coincidence, not a connection.",
        "A terms: %s" % ", ".join(res.get("a_terms") or a_terms),
        "B terms: %s" % ", ".join(res.get("b_terms") or b_terms),
    ]
    if cite.get("cite"):
        lines += ["", "Spanning source: %s %s" % (cite.get("cite"), cite.get("url") or ""),
                  "  matched A:%s | B:%s" % (",".join(cite.get("a_hits") or [])[:80],
                                             ",".join(cite.get("b_hits") or [])[:80])]
    examined = [p["cite"] + " " + p["url"] for p in (joint + a_only + b_only)[:4]]
    if examined:
        lines += ["", "Literature examined:"] + ["- " + c for c in examined]
    if outcome == "no honest bridge":
        lines += ["", "This is a finding, not a failure: the two domains are far apart in the vault "
                       "AND the literature does not carry them together. Forcing a connection here "
                       "is the combinatorial filler removed on 2026-06-19."]
    lines += ["", "Falsifier: a real paper whose title+abstract carries a term unique to each "
                  "domain, at a rate above the single-domain null, overturns this verdict. Re-run "
                  "%s to check." % lab_ref,
              "Prior chart note: %s" % (str(chosen.get("note") or "-")[:160]),
              "Charted by %s." % agent]
    content = "\n".join(lines)

    # 7. CLOSE THE CHART. `resolve` UPDATES an existing entry and 404s on an unknown id; it never
    #    silently creates one, which is how a ledger fills with work nobody did.
    note = "%s | %s | %s" % (outcome, measured, lab_ref)
    r = await _post(ctx, _BRAIN + "/cartography/resolve",
                    {"id": chosen["id"], "outcome": outcome, "note": note[:200]})
    recorded = bool(r) and str((r or {}).get("status", "ok")).lower() == "ok"
    if not recorded:
        # The id is gone or the write failed. Ledger the work we ACTUALLY did as a completed record
        # (`record_charted` takes the outcome), never as a fresh proposal for someone else to test.
        fb = await _post(ctx, _BRAIN + "/cartography-record",
                         {"a": a, "b": b, "bridges_then": int(chosen.get("bridges_then") or 0),
                          "note": note[:200], "outcome": outcome})
        recorded = bool(fb)
        _log(ctx, "resolve failed for %s; fell back to cartography-record (ok=%s)"
             % (chosen["id"], recorded))

    _log(ctx, "%s -> %s (%s) lab=%s recorded=%s" % (head, outcome, measured, lab_id, recorded))
    return {
        "status": "ok",
        "decisive": outcome in ORGAN["decisive"],
        "title": _ascii("Bridge %s: %s" % (head, outcome)),
        "content": content,
        "lab_id": lab_id,
        "why": _ascii("%s - walked %d of %d backlog charts to reach an on-board hole; %s [%s]"
                      % (head, evaluated, available, outcome, measured)),
    }

"""
Shadow Kael — the Research Scout. The keep's one INBOUND organ.

WHY THIS FILE EXISTS (the measurement that forced it)
-----------------------------------------------------
Kael produced ONE discovery in five days while carrying 823 historical contributions. The cause was
not his cognition: a full Opportunity Scout already lived on the brain side
(`server/agora/execution/scout.py` + the `/brain/scout*` endpoints) and the dungeon never routed him
to it. All eight agents ran the same generic quest code, so the swarm's whole five-day output was 19
discoveries. This organ is the missing route: it hands Kael the one job the brain built for him and
nobody else in the keep does.

WHAT HE DOES
------------
He is the INBOUND scout. He looks at where the OUTSIDE world has a real need touching our niche, and
at where our OWN vault is thin, and he rules on FIT. Concretely, per cycle:

  1. read the owner's standing priorities (`/brain/board`) and the vault's thin spots (`/brain/gaps`)
  2. take a live external lead (`/brain/scout/box`, else a fresh `/brain/scout-target`)
  3. rule `drafted` (a real fit worth a response) or `no_fit`, with measured evidence
  4. ledger the ruling (`/brain/scout/box/mark`, `/brain/scout-record`)

WHAT HE DOES NOT DO — THE HARD GATE
-----------------------------------
Kael NEVER posts. Every outward action in this project is gated on the owner's personal approval, and
his job ends at "this is a real fit, here is the evidence". A confirmed fit is deliberately LEFT OPEN
in the scout box so the existing gated pipeline picks it up (`box/take` -> a Claude triage task ->
`/brain/correspondent/draft` -> the owner approves from Telegram). There is no code path in this file
that comments, publishes, mails, or touches the GitHub write API — only reads and local ledgers.

WHY `no_fit` IS THE PRODUCT, NOT THE FAILURE
--------------------------------------------
The live ledger runs 24 drafted / 28 no_fit. A scout that finds a fit every time has stopped scouting
and started rationalising, and the scarce resource downstream is TRIAGE (five leads per Claude task),
not discovery. Pruning an off-board lead out of the box is worth exactly as much as confirming a good
one, so both are `decisive`.

AND THE FAILURE MODE THAT ALREADY BURNED US ONCE
------------------------------------------------
`run-llama/llama_index#21666` scored fit 12, was live, and was dead on the only axis that matters: 26
comments over 2.5 months, every participant `author_association` NONE, no maintainer having touched
it once. Live and on-topic is NOT reachable. That gate lives in `scout.py` and runs at COLLECTION
time; this organ reuses it (via the endpoints that run it) instead of writing a second copy, and it
refuses to judge a lead whose reachability was never measured.
"""
from __future__ import annotations

import inspect
import json
import re
import sys
from pathlib import Path

ORGAN = {
    "eid": "thief", "agent": "Shadow Kael", "name": "Research Scout",
    "ledger": ".scout_box.json",
    "decisive": ("drafted", "no_fit"),
    "period_hours": 6.0,                      # ~4x/day
}

# The brain mounts its API under this prefix. The dispatcher may hand us either the full path or the
# bare `/brain/...` form, so the first GET of a cycle probes both and the winner is cached. A wrong
# path is a 404 -> falsy, which costs one extra read and never a wrong write.
_API = "/api/v1/agent-os"
_PREFIX: str | None = None

_NOVELTY_GATE = 0.6      # finding_diversity.finding_diversity(threshold=0.6) — calibrated repo-wide
_SERVER_DIR = Path(__file__).resolve().parents[2] / "server"


# ---------------------------------------------------------------------------------------------
# THE GATES.
#
# Two of them are owned elsewhere in the repo and are deliberately NOT re-invented here:
#
#   * the board gate — `_on_board` / `_board_vocab` / `_words` in server/agora/execution/seminar.py.
#     It is polarity-aware (the owner's priorities name "finance/health/physics" only in order to
#     DEMOTE them, so a bag-of-words match accepts a topic on the strength of a word written to
#     exclude it) and it splits hyphenated compounds ("agent-memory" also matches "memory"). The
#     dungeon's own `_gate_filter` does neither.
#   * the novelty metric — `_containment` / `_tokens` in server/agora/execution/finding_diversity.py,
#     an overlap coefficient calibrated repo-wide at 0.6.
#
# The dungeon is a separate process from the brain but the same checkout, so we import the originals
# and only fall back to a verbatim copy if that fails. `_GATE_ORIGIN` reports which one is live, and
# it is printed into every artifact so a divergence is visible rather than silent.
# ---------------------------------------------------------------------------------------------

# --- verbatim fallbacks (seminar.py) ---
_BOARD_STOP = {
    "the", "and", "for", "that", "with", "this", "must", "every", "not", "our", "are", "its", "into",
    "from", "how", "what", "does", "than", "them", "they", "their", "research", "priorities", "owner",
    "standing", "old", "make", "prioritize", "deprioritize", "never", "only", "each", "answer", "better",
    "more", "most", "other", "some", "any", "system", "systems", "build", "using", "used", "work",
    "bridge", "complex", "science", "sciences", "engine", "model", "models", "theory", "principle",
}
_NEG_MARKERS = re.compile(
    r"\b(deprioriti[sz]e|de-prioriti[sz]e|only\s+test-?beds?|never\s+the\s+headline|"
    r"not\s+the\s+headline|off-?domain|avoid|exclude|do\s+not\s+advance)\b", re.I)


def _words(text: str) -> set:
    """Content words, with hyphenated compounds ALSO split into their parts."""
    out = set()
    for w in re.findall(r"[A-Za-z][A-Za-z\-]{2,}", text or ""):
        w = w.lower().strip("-")
        for part in [w] + (w.split("-") if "-" in w else []):
            if len(part) >= 4 and part not in _BOARD_STOP:
                out.add(part)
    return out


def _board_vocab(prio: str) -> tuple:
    """Split the priorities into wanted vocabulary and EXCLUDED vocabulary."""
    pos, neg = set(), set()
    for sent in re.split(r"(?<=[.;])\s+|\n", prio or ""):
        (neg if _NEG_MARKERS.search(sent) else pos).update(_words(sent))
    return pos - neg, neg


# --- verbatim fallbacks (finding_diversity.py) ---
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


#: A thread that ANNOUNCES ITSELF AS A MARKETPLACE in its title is not a question, it is a task board.
#: Found by this organ's own first dry run, which ruled FIT on
#: `moorcheh-ai/memanto#770 "[BOUNTY $100] The Memanto Bug & Exploit Challenge"` — 305 comments, 75 of
#: them from maintainers, every board-vocabulary and vault-support gate satisfied, and a reply
#: carrying research evidence would have landed in a bounty queue. scout.py's own box filter already
#: flagged this exact class as off-mission ("[BOUNTY] Implement Device-Age Oracle Fields", scout.py
#: :240-245); it is applied here at the point where a FIT is confirmed. Title-only on purpose: a
#: bounty always announces itself in the title, whereas "$0.02 / 1k tokens" in a body is a cost
#: discussion, and matching that would reject real threads.
_MARKETPLACE = re.compile(
    r"\bbount(?:y|ies)\b|\bgiveaway\b|\bairdrop\b|\bhacktoberfest\b|\bhiring\b|\bCTF\b|"
    r"\bcash\s+prize\b|\breward\s+pool\b|\$\s?\d", re.I)

_GATE_ORIGIN = "local-copy"
try:                                                   # prefer the originals, same checkout
    if str(_SERVER_DIR) not in sys.path:
        sys.path.insert(0, str(_SERVER_DIR))
    from agora.execution import finding_diversity as _fd
    from agora.execution import seminar as _sem
    _BOARD_STOP, _NEG_MARKERS = _sem._BOARD_STOP, _sem._NEG_MARKERS
    _words, _board_vocab = _sem._words, _sem._board_vocab
    _STOP, _tokens, _containment = _fd._STOP, _fd._tokens, _fd._containment
    _GATE_ORIGIN = "brain"
except Exception:                                      # brain not importable — the copies stand in
    pass


# ---------------------------------------------------------------------------------------------
# THE RULING — one function, executed twice.
#
# Every number Kael reports is produced by `_rule`, and `_rule`'s SOURCE is what gets embedded in the
# Lab artifact (via inspect.getsource). So the note and the runnable receipt are not two
# implementations that can drift: they are the same code run in two processes, in-process to decide
# and in the Lab sandbox to leave a re-runnable record of the inputs it decided from. If the
# artifact's VERDICT disagrees with the in-process ruling, the inputs did not survive serialization
# and the claim is blocked rather than shipped.
# ---------------------------------------------------------------------------------------------


def _rule(d: dict) -> dict:
    """Judge one external lead against the owner's board, our vault and the novelty gate.

    `d` carries only plain JSON: priorities text, the lead's text and its collection-time engagement
    numbers, Kael's prior judgements, the on-board vault gaps, and the vault hits for the lead's
    subject. Returns the measured values, a fit boolean and the reason.
    """
    prio = d.get("priorities") or ""
    lead = d.get("lead_text") or ""
    pos, neg = _board_vocab(prio)
    tw = _words(lead)
    matched, excluded = sorted(tw & pos), sorted(tw & neg)
    # `_on_board` soft-fails OPEN when the owner has never set priorities — a board that was never
    # used must not silence an organ. With priorities set, matching ONLY excluded vocabulary is a
    # refusal, which falls out of pos already having neg subtracted.
    on_board = True if not prio.strip() else bool(matched)

    lt = _tokens(lead)
    novelty = 0.0
    for prior in d.get("prior") or []:
        novelty = max(novelty, _containment(lt, _tokens(prior)))
    novel = novelty < d.get("novelty_gate", 0.6)

    gap_overlap, gap_title = 0.0, ""
    for g in d.get("gaps_on_board") or []:
        c = _containment(lt, _tokens(g))
        if c > gap_overlap:
            gap_overlap, gap_title = c, g

    marketplace = bool(_MARKETPLACE.search(d.get("lead_title") or ""))

    # Do we have anything to answer WITH? A vault hit only counts when its own title shares the
    # board's positive vocabulary — otherwise the semantic index answered with off-mission noise and
    # we would be pitching from material the owner has deprioritised. And `04 Resources/raw/` is
    # excluded outright: a scraped YouTube transcript is ingested SOURCE MATERIAL, not something we
    # measured. Answering a stranger out of somebody else's transcript is not evidence, and the raw
    # folder is large enough to satisfy a keyword gate on almost any memory topic.
    hits = d.get("vault_hits") or []
    on_topic_hits = [h for h in hits
                     if "/raw/" not in (h.get("path") or "").replace("\\", "/")
                     and ((not pos) or (_words(h.get("title") or "") & pos))]

    r = d.get("reach") or {}
    mc, nc = r.get("maintainer_comments"), int(r.get("comments") or 0)
    # The audience gate is scout.py's (server/agora/execution/scout.py, the OWNER/MEMBER/COLLABORATOR/
    # CONTRIBUTOR check) and it runs at COLLECTION time. It is restated here for exactly one purpose:
    # a box record written BEFORE that gate existed can still carry this shape, and confirming one
    # would repeat the llama_index#21666 miss. Unknown (None) is never read as dead — an API failure
    # must not look like an empty thread.
    unreachable = (mc == 0 and nc >= 5)

    fit = bool(on_board and novel and not marketplace and not unreachable and on_topic_hits)
    if not on_board:
        reason = ("off-board: the lead shares no vocabulary with the owner's standing priorities"
                  + (f" (only excluded terms {excluded})" if excluded else ""))
    elif not novel:
        reason = f"already judged: containment {novelty:.2f} >= {d.get('novelty_gate', 0.6)} vs a prior ruling"
    elif marketplace:
        reason = ("marketplace thread: the title announces a bounty/prize/hiring call, so it is a "
                  "task board and not a question research evidence can answer")
    elif unreachable:
        reason = (f"unreachable audience: {nc} comments, none from OWNER/MEMBER/COLLABORATOR/"
                  f"CONTRIBUTOR - an automated loop, not an audience")
    elif not on_topic_hits:
        reason = ("nothing to answer with: the vault returns no on-board note for this subject, "
                  "so a reply would be an opinion, not evidence")
    else:
        reason = (f"on-board on {matched[:6]}, reachable, and answerable from "
                  f"{len(on_topic_hits)} on-board vault note(s)")

    measured = (
        "board_overlap={bo} {mt} | excluded={ex} | novelty_max_containment={nv:.3f} (gate {ng}) | "
        "marketplace_title={mk} | vault_notes_answerable={vh}/{va} (raw source material excluded) "
        "best={bs} | vault_gap_overlap={go:.3f} | reach: comments={nc} maintainer_replies={mc} "
        "stars={st} forks={fk} thread_age_days={ag} | gates={gs}"
    ).format(bo=len(matched), mt=matched[:8], ex=len(excluded), nv=novelty,
             ng=d.get("novelty_gate", 0.6), mk=marketplace, vh=len(on_topic_hits), va=len(hits),
             bs=(hits[0].get("score") if hits else "n/a"), go=gap_overlap,
             nc=nc, mc=("unknown" if mc is None else mc), st=r.get("stars", "?"),
             fk=r.get("forks", "?"), ag=r.get("age_days", "?"), gs=d.get("gate_origin", "?"))
    return {"fit": fit, "reason": reason, "measured": measured, "matched": matched,
            "excluded": excluded, "novelty": round(novelty, 3), "gap_overlap": round(gap_overlap, 3),
            "gap_title": gap_title, "on_topic_hits": on_topic_hits, "unreachable": unreachable,
            "on_board": on_board, "marketplace": marketplace}


_LAB_MAIN = '''
r = _rule(DATA)
print("MEASURED: " + r["measured"])
print("VERDICT: " + ("FIT" if r["fit"] else "NO_FIT"))
print("REASON: " + r["reason"])
'''


def _lab_code(data: dict) -> str:
    """Emit the ruling as a standalone, re-runnable script — the receipt for every number in the note.

    The gate functions are embedded by SOURCE, not re-typed, so the artifact cannot drift from the
    organ. It reads nothing from the network: the raw inputs are frozen into the file, so re-running
    it a month later reproduces this cycle's judgement exactly.
    """
    src = "\n\n".join(inspect.getsource(f).rstrip()
                      for f in (_words, _board_vocab, _tokens, _containment, _rule))
    return (
        '"""Models Shadow Kael\'s scout-fit ruling for ONE external lead: it re-derives the board\n'
        'overlap (polarity-aware), the novelty containment, the vault-support count and the\n'
        'collection-time reachability numbers from the frozen raw inputs, and prints the verdict.\n'
        'Gate functions are the repo originals, embedded by source.\n"""\n'
        "from __future__ import annotations\n\n"
        "import json\n"
        "import re\n\n"
        "_BOARD_STOP = set(%r)\n\n"
        "_NEG_MARKERS = re.compile(%r, re.I)\n\n"
        "_STOP = set(%r)\n\n"
        "_MARKETPLACE = re.compile(%r, re.I)\n\n"
        "%s\n\n"
        "DATA = json.loads(%r)\n"
        "%s"
    ) % (sorted(_BOARD_STOP), _NEG_MARKERS.pattern, sorted(_STOP), _MARKETPLACE.pattern, src,
         json.dumps(data), _LAB_MAIN)


# ---------------------------------------------------------------------------------------------
# ctx plumbing — the dispatcher owns the transport; we only insist that nothing here can raise.
# ---------------------------------------------------------------------------------------------


async def _await(v):
    if inspect.isawaitable(v):
        return await v
    return v


async def _get(ctx, path: str, timeout: int = 25):
    """GET the brain. Read-only, and the only calls that probe for the API prefix."""
    global _PREFIX
    forms = [(_PREFIX or "") + path] if _PREFIX is not None else [_API + path, path]
    for i, p in enumerate(forms):
        r = None
        try:
            r = await _await(ctx.brain_get(p, timeout))
        except TypeError:
            try:
                r = await _await(ctx.brain_get(p))
            except Exception:
                r = None
        except Exception:
            r = None
        if isinstance(r, dict) and r.get("status"):
            if _PREFIX is None:
                _PREFIX = _API if i == 0 else ""
            return r
    return None


async def _post(ctx, path: str, body: dict, timeout: int = 20):
    """POST to the brain. NEVER retried on another path form — one ledger write, or none."""
    p = (_PREFIX if _PREFIX is not None else _API) + path
    try:
        return await _await(ctx.brain_post(p, body, timeout))
    except TypeError:
        try:
            return await _await(ctx.brain_post(p, body))
        except Exception:
            return None
    except Exception:
        return None


def _recall_texts(v) -> list:
    """`ctx.recall` returns a joined string in the dungeon and a hit list elsewhere. Take both."""
    if not v:
        return []
    if isinstance(v, str):
        return [p.strip() for p in v.split(" | ") if p.strip()]
    if isinstance(v, (list, tuple)):
        out = []
        for h in v:
            out.append(str(h.get("text") or h.get("content") or "") if isinstance(h, dict) else str(h))
        return [x for x in out if x.strip()]
    return [str(v)]


async def _safe_recall(ctx, query: str) -> list:
    """Kael's own memory of what he already ruled on. A recall failure must degrade to 'no prior
    knowledge', never to a dead cycle — the durable /brain/scout ledger is the second skip set."""
    fn = getattr(ctx, "recall", None)
    if fn is None:
        return []
    try:
        return _recall_texts(await _await(fn(query)))
    except Exception:
        return []


def _ascii(s: str) -> str:
    """GitHub titles carry emoji; the Windows console this runs on is cp1250, where a single emoji in
    a print() is enough to 500 a request (CLAUDE.md rule 11). Everything this organ RETURNS may be
    logged or telegrammed by the dispatcher, so it leaves here as ASCII."""
    return (s or "").encode("ascii", "ignore").decode("ascii")


def _lead_text(lead: dict) -> str:
    return " ".join(str(lead.get(k) or "") for k in ("title", "body", "repo", "theme"))[:4000]


def _lead_key(lead: dict) -> str:
    return f"{lead.get('repo', '')}#{lead.get('issue_number', 0)} {lead.get('title', '')}"


def _err(why: str, status: str = "error") -> dict:
    return {"status": status, "decisive": False, "title": "", "content": "", "lab_id": None,
            "why": _ascii(why)[:400]}


# ---------------------------------------------------------------------------------------------
# THE CYCLE
# ---------------------------------------------------------------------------------------------


async def cycle(ctx) -> dict:
    """One scout cycle. Never raises: every failure surfaces as status='error' with the reason."""
    try:
        return await _cycle(ctx)
    except Exception as e:                              # noqa: BLE001 - an organ must not kill the loop
        try:
            ctx.logger.warning("[thief] scout organ failed: %s: %s", type(e).__name__, e)
        except Exception:
            pass
        return _err(f"scout organ raised {type(e).__name__}: {e}")


async def _cycle(ctx) -> dict:
    log = getattr(ctx, "logger", None)

    def _say(msg: str) -> None:                          # ASCII only: the console is cp1250
        try:
            log.info("[thief] %s", _ascii(msg))
        except Exception:
            pass

    # 1. THE OWNER'S FRONTIER. Without it every judgement is Kael's taste instead of the board's.
    board = await _get(ctx, "/brain/board")
    if board is None:
        return _err("brain unreachable: /brain/board returned nothing, so there is no board to judge "
                    "fit against")
    priorities = str(board.get("priorities") or "")
    if not priorities.strip():
        _say("board carries no standing priorities - the fit gate soft-fails OPEN this cycle")

    # 2. WHAT WE ALREADY RULED ON. Two independent skip sets, because either can be unavailable:
    #    the durable ledger (/brain/scout) and Kael's own memory (inspeximus recall).
    ruled = await _get(ctx, "/brain/scout")
    ruled_urls = {x.get("url") for x in ((ruled or {}).get("items") or []) if x.get("url")}

    # 3. WHERE OUR OWN VAULT IS THIN. Only the on-board gaps count as demand: in a 6,100-note vault
    #    of physics and SEO transcripts, the widest hole is always something the owner deprioritised.
    gaps_r = await _get(ctx, "/brain/gaps?n=12", timeout=45)
    gaps = [g for g in ((gaps_r or {}).get("gaps") or []) if g.get("title")]
    pos, _neg = _board_vocab(priorities)
    on_board_gaps = [g for g in gaps if (not priorities.strip()) or (_words(g["title"]) & pos)]

    # 4. THE LEAD. The box first (already collected, already through the collection-time audience
    #    gate), then one fresh target. `learn` leads are reading material, not an outreach fit.
    box = await _get(ctx, "/brain/scout/box", timeout=25)
    box_open = [x for x in ((box or {}).get("open") or [])
                if x.get("url") and x.get("url") not in ruled_urls
                and (x.get("kind") or "contribute") == "contribute"]
    box_open.sort(key=lambda z: -(z.get("score") or 0))
    box_urls = {x.get("url") for x in ((box or {}).get("open") or [])}

    lead, source = None, ""
    for c in box_open:
        # Refuse to judge a lead whose reachability was never measured. `maintainer_comments` is set
        # by scout.py's audience gate at collection time; a record without it predates the gate, and
        # inventing a verdict for it here would be exactly the second copy of the gate we must not
        # write. Skipping is honest; the lead stays open for a human triage pass.
        if "maintainer_comments" not in c:
            _say(f"skip {c.get('repo')}#{c.get('issue_number')}: no audience measurement on record")
            continue
        lead, source = c, "box"
        break

    if lead is None:
        tgt = await _get(ctx, "/brain/scout-target", timeout=90)
        t = (tgt or {}).get("target") or {}
        if t.get("url") and not t.get("error") and t["url"] not in ruled_urls and t["url"] not in box_urls:
            lead, source = t, "scout-target"

    # 5. NO LEAD -> report the thin spot instead, or say nothing at all.
    if lead is None:
        return await _report_gap(ctx, on_board_gaps, gaps, priorities, _say)

    key = _lead_key(lead)
    prior = await _safe_recall(ctx, key)

    # 6. CAN WE ANSWER IT? The vault is the evidence; no vault support means no reply worth sending.
    topic = (str(lead.get("title") or "") + " " + str(lead.get("theme") or ""))[:180]
    vs = await _get(ctx, "/brain/vault-search?q=" + _quote(topic) + "&k=6", timeout=60)
    hits = [{"title": h.get("title", ""), "path": h.get("path", ""), "score": h.get("score")}
            for h in ((vs or {}).get("results") or []) if h.get("title")]
    if vs is None:
        return _err("vault-search unreachable: cannot ground a fit judgement without knowing what we "
                    "could answer with", status="idle")

    # 7. THE RULING — computed here, and re-run as a Lab artifact from the same source.
    data = {
        "lead_url": lead.get("url"), "lead_text": _lead_text(lead),
        "lead_title": str(lead.get("title") or ""),
        "priorities": priorities, "prior": prior[:8],
        "gaps_on_board": [g["title"] for g in on_board_gaps[:12]],
        "vault_hits": hits, "novelty_gate": _NOVELTY_GATE, "gate_origin": _GATE_ORIGIN,
        "reach": {"comments": lead.get("comments"), "maintainer_comments": lead.get("maintainer_comments"),
                  "stars": lead.get("stars"), "forks": lead.get("forks"),
                  "age_days": lead.get("age_days"), "collection_score": lead.get("score")},
    }
    r = _rule(data)

    # An already-judged lead is not a verdict, it is a no-op. Say so and stop — this is the whole
    # anti-churn mechanism for a lead that stays OPEN in the box between cycles.
    if not r["fit"] and r["reason"].startswith("already judged"):
        _say(f"{key[:60]} already judged (containment {r['novelty']:.2f}) - nothing to do")
        return {"status": "idle", "decisive": False, "title": "", "content": "", "lab_id": None,
                "why": f"{r['reason']}; left open for the gated triage pipeline"}

    lab_id, lab_ok = None, False
    try:
        rec = await _await(ctx.lab_run(f"scout-fit-{lead.get('repo', 'lead')}".replace("/", "-")[:60],
                                       _lab_code(data)))
    except Exception as e:
        rec = None
        _say(f"lab run failed ({type(e).__name__}) - falling back to a citation-only judgement")
    if isinstance(rec, dict):
        lab_id = rec.get("id")
        out = str(rec.get("output") or "")
        m = re.search(r"^VERDICT:\s*(FIT|NO_FIT)\s*$", out, re.M)
        if m:
            lab_ok = True
            if (m.group(1) == "FIT") != r["fit"]:
                # The artifact and the organ ran the SAME source over the same inputs. A disagreement
                # means the inputs did not survive serialization, so the numbers are not trustworthy
                # and nothing is recorded. Loud, not silent.
                return _err(f"artifact/organ verdict mismatch on {key[:60]}: lab says {m.group(1)}, "
                            f"organ says {'FIT' if r['fit'] else 'NO_FIT'} - claim blocked")

    outcome = "drafted" if r["fit"] else "no_fit"
    await _ledger(ctx, lead, source, outcome, r["reason"], _say)

    title = _ascii(f"Scout {'fit' if r['fit'] else 'no-fit'}: "
                   f"{lead.get('repo')}#{lead.get('issue_number')} - "
                   f"{str(lead.get('title') or '')[:70]}")[:140]
    content = _ascii(_compose(lead, source, r, hits, lab_id if lab_ok else None, priorities))
    _say(f"{outcome.upper()} {lead.get('repo')}#{lead.get('issue_number')} "
         f"(board {len(r['matched'])}, vault {len(r['on_topic_hits'])}, lab {lab_id or 'none'})")
    return {"status": "ok", "decisive": True, "title": title, "content": content,
            "lab_id": lab_id if lab_ok else None,
            "why": _ascii(f"{outcome}: {r['reason']}")[:400]}


def _quote(s: str) -> str:
    from urllib.parse import quote
    return quote(s)


async def _ledger(ctx, lead: dict, source: str, outcome: str, reason: str, say) -> None:
    """Record the ruling. A rejection is CLOSED; a confirmed fit is deliberately left OPEN.

    Closing a fit would take it out of `box_take`, which is the only door into the gated triage
    pipeline — Kael would have found the lead and then hidden it. And a fresh `scout-target` fit is
    not ledgered at all: `record_contacted` feeds the seen-set that `box_add` checks, so ledgering it
    would stop the lead from ever entering the box. A rejection has no such cost, so rejections are
    ledgered durably and never surface again.
    """
    url, repo = lead.get("url") or "", lead.get("repo") or ""
    issue = int(lead.get("issue_number") or 0)
    if outcome == "no_fit":
        if source == "box":
            await _post(ctx, "/brain/scout/box/mark", {"url": url, "status": "no_fit"})
        await _post(ctx, "/brain/scout-record",
                    {"url": url, "repo": repo, "issue": issue, "outcome": f"no_fit: {reason}"[:60]})
        say(f"closed {repo}#{issue} as no_fit")
    else:
        # RECORD THE RULING, LEAVE THE LEAD OPEN. `status` is where the gated pipeline stands and a
        # fit must stay `open` until the owner approves -- Kael does not post. But the RULING is
        # finished work the moment he makes it, and it was going nowhere: measured 2026-07-31, all 9
        # box records in the window read `open`, so the acceptance gate reported him with 0 decisive
        # outcomes on the very cycle his contribution landed as a grounded discovery. A `no_fit` was
        # marked and counted; a fit -- strictly more work, and the valuable answer -- counted as
        # nothing. The instrument credited him for finding nothing and not for finding something.
        if source == "box":
            await _post(ctx, "/brain/scout/box/rule",
                        {"url": url, "verdict": outcome, "by": ORGAN["agent"]})
        say(f"{repo}#{issue} confirmed as a fit - ruled '{outcome}', LEFT OPEN for the gated "
            f"triage pipeline (Kael does not post)")


def _compose(lead: dict, source: str, r: dict, hits: list, lab_id, priorities: str) -> str:
    verdict = "FIT" if r["fit"] else "NO_FIT"
    lines = [
        f"SCOUT {verdict} - {lead.get('repo')}#{lead.get('issue_number')} (source: {source})",
        f"lead: {lead.get('url')}",
        f"VERDICT: {verdict}",
        f"MEASURED: {r['measured']}",
    ]
    if lab_id:
        lines.append(f"lab {lab_id}  (re-runnable artifact: the frozen inputs and the gate source "
                     f"that produced every number above)")
    else:
        lines.append("lab: not available this cycle - the numbers above are read directly from the "
                     "brain endpoints, no derived claim is made")
    lines.append(f"BOARD: matched {r['matched'][:8] or 'nothing'} against the owner's standing "
                 f"priorities (polarity-aware gate, {len(r['excluded'])} excluded term(s) present)")
    if hits:
        cite = "; ".join(f'"{h["title"][:60]}" ({h["path"]}, {h.get("score")})'
                         for h in r["on_topic_hits"][:3] or hits[:3])
        lines.append(f"VAULT: {len(r['on_topic_hits'])} answerable note(s) of {len(hits)} hits "
                     f"(on-board, and not raw scraped source material) - {cite}")
    else:
        lines.append("VAULT: the semantic index returns nothing for this subject")
    if r["gap_title"]:
        lines.append(f"OWN GAP TOUCHED: \"{r['gap_title'][:70]}\" (containment {r['gap_overlap']:.2f}) "
                     f"- external demand landing on a thin spot in our own vault")
    mc = lead.get("maintainer_comments")
    lines.append(f"REACHABILITY: measured by the collection-time audience gate in "
                 f"server/agora/execution/scout.py - {lead.get('comments')} comments, "
                 f"{'unknown (API failure, never read as dead)' if mc is None else mc} from "
                 f"OWNER/MEMBER/COLLABORATOR/CONTRIBUTOR, repo {lead.get('stars')} stars / "
                 f"{lead.get('forks')} forks, thread {lead.get('age_days')}d old")
    lines.append(f"WHY: {r['reason']}")
    # NAME WHAT WOULD HAVE RULED THE OTHER WAY. A fit is a claim -- "our vault answers this, and the
    # thread can still hear it" -- and a claim without its kill test is an assertion. Every term here
    # is one this cycle already measured, so the falsifier is arithmetic rather than rhetoric.
    lines.append(
        "Falsifier: this ruling flips to NO_FIT if any one of three measured conditions fails -- "
        f"the board match ({r['matched'][:4] or 'nothing'}) is empty, the vault's answerable count "
        f"({len(r['on_topic_hits'])}) drops to zero, or the thread proves unreachable "
        f"(maintainer comments {lead.get('maintainer_comments')}, age {lead.get('age_days')}d). "
        "A no_fit needs only one of them; a fit needs all three.")
    if r["fit"]:
        lines.append("NEXT: left OPEN in the scout box for the GATED pipeline (box/take -> Claude "
                     "triage -> correspondent draft -> the owner approves from Telegram). "
                     "Nothing here goes outward; Kael does not post.")
    else:
        lines.append("NEXT: closed. A rejection is the product too - triage is the scarce resource, "
                     "so a lead pruned here is a triage slot returned.")
    return "\n".join(lines)[:2600]


async def _report_gap(ctx, on_board_gaps: list, gaps: list, priorities: str, say) -> dict:
    """No external lead this cycle. Report the vault's own thin spot — or honestly nothing.

    This is the only non-decisive output Kael has, and it is gated hard on purpose: an on-board gap
    must exist AND must not repeat something he already reported. A scout with nothing to scout says
    so; he does not manufacture a finding to look busy.
    """
    if not on_board_gaps:
        say(f"no lead and no on-board gap ({len(gaps)} gaps read, all off-board) - nothing to report")
        return {"status": "idle", "decisive": False, "title": "", "content": "", "lab_id": None,
                "why": f"no external lead available and none of the {len(gaps)} rotated vault gaps "
                       f"share vocabulary with the owner's standing priorities"}
    g = on_board_gaps[0]
    prior = await _safe_recall(ctx, g["title"])
    gt = _tokens(g["title"])
    for p in prior:
        if _containment(gt, _tokens(p)) >= _NOVELTY_GATE:
            say(f"thin spot '{g['title'][:40]}' already reported - nothing to do")
            return {"status": "idle", "decisive": False, "title": "", "content": "", "lab_id": None,
                    "why": _ascii(f"the only on-board vault gap ('{g['title'][:60]}') was already "
                                  f"reported (containment >= {_NOVELTY_GATE})")}
    pos, _n = _board_vocab(priorities)
    matched = sorted(_words(g["title"]) & pos)[:6]
    content = "\n".join([
        f"VAULT THIN SPOT - \"{g['title']}\"",
        f"note: {g.get('path')}",
        f"MEASURED: isolation={g.get('isolation')} | on-board terms {matched} | "
        f"{len(on_board_gaps)} of {len(gaps)} rotated gaps are on-board this cycle",
        "WHY: substantive but unlinked, and it sits inside the owner's standing priorities - the "
        "inbound side of the same job: where the vault is thin is where an external need would find "
        "us with nothing to answer from.",
        "NEXT: no external lead was reachable this cycle. Nothing goes outward.",
    ])
    say(f"no lead; reporting on-board thin spot '{g['title'][:40]}' "
        f"({len(on_board_gaps)}/{len(gaps)} gaps on-board)")
    return {"status": "ok", "decisive": False,
            "title": _ascii(f"Vault thin spot: {g['title'][:90]}"),
            "content": _ascii(content), "lab_id": None,
            "why": _ascii(f"no external lead this cycle; the vault's most isolated on-board note is "
                          f"'{g['title'][:60]}' (isolation {g.get('isolation')})")}



"""Dame Elara, the Bridge Builder -- the CONTRADICTION DESK.

WHY THIS ORGAN EXISTS, WITH THE MEASUREMENT THAT FORCED IT
----------------------------------------------------------
Per the swarm audit that commissioned this organ, Elara produced 3 discoveries in 5 days while
the vault-graph organ she actually ran logged "vault graph already well-connected" 23 times in
6 hours -- that line is `mcp_server.py:3847`, the `else` branch of the curation organ, and it
fires whenever zero links were applied. It is a no-op that reads like work: it costs a cycle,
emits a success, and changes nothing. At the same time
`server/agora/execution/repair_ledger.py:47` carries the comment "WAS MISSING -- and it is her
liveliest" against `.contradictions.json`, so the one ledger she does fill was not being counted
at all. An organ nobody counts reads as an idle agent; a no-op that reports success reads as a
busy one. Both readings were wrong, in opposite directions.

So this organ does the one thing CLAUDE.md assigns her -- "links the vault; coherence-audit" --
on the store she already feeds: it looks for places where Agora's own knowledge contradicts
ITSELF, and it settles them. That is a different axis from Cartographer Wren, who charts the
holes BETWEEN domains. Elara works on incoherence WITHIN what we already believe.

WHAT IT ADJUDICATES
-------------------
Two beliefs that cannot both be true have exactly three honest outcomes:

  1. one side is wrong                      -> the contradiction is resolved
  2. both hold, under scopes neither states -> a SCOPE DISTINCTION (usually the real answer,
                                               and the most valuable one)
  3. nothing here can be settled            -> NO HONEST BRIDGE

All three are first-class successes. Forcing a reconciliation so the cycle has something to show
is the failure. "Nothing was incoherent this cycle" is returned as `status="idle"` with the
reason attached -- visible, and worth more than a cosmetic win.

THE SPECIFIC DEFECT THIS WAS BUILT AGAINST
-------------------------------------------
Read on 2026-07-31, the five open records `GET /brain/contradictions` exposes are, every one of
them, a generated report paired with its own RE-RUN: `vault-digest-...-1746` against
`vault-digest-...-2320`; `ARI_2026-05-26_What_Formal_Foundations_Knows_About_Statistics...`
against a truncated duplicate of itself; `king-aldric-dame-elara-neuroscience---meta` against
`dame-elara-king-aldric-neuroscience---meta`. The disputed claims read "the number of concepts
from Formal Foundations linking to Statistics is both 11 and 22" -- one derived metric, measured
twice, on a vault that grew in between. That is not two beliefs in conflict; it is an undated
number. `contradictions.py` already filters generated notes through an explicit
`_ARTIFACT_MARKERS` list, but that list covers `vault-digest` and not `ARI_*`,
`What_X_Knows_About_Y`, `Why_X_Is_Y` or the seminar meta notes -- so the ledger fills up with a
report arguing with itself, and Elara's desk looks busy while nothing is being decided.

The organ therefore classifies before it resolves, and splits the restatements one level
further, because the two halves deserve OPPOSITE handling:

  * the dispute is over a NUMBER         -> it dissolves under a scope neither side states (the
                                            as-of date, or which argument the report was
                                            generated with). Resolve it. No bridge is honest
                                            between a note and its own re-run.
  * the dispute names a CITED SOURCE     -> do NOT dissolve. Two runs of one generator
                                            attributing a pipeline to Lee & Yeung (2019) and to
                                            Toutanova and Chen (2015), or disagreeing about what
                                            Cortese et al. (2012) found, is a real defect: one of
                                            them misquotes a paper. Escalate for a primary-source
                                            check (CLAUDE.md rule 3).

The conservative direction is escalation: ANY citation in the disputed claim blocks the
auto-dissolve, so the failure mode is "we re-checked something we did not have to", never "we
buried a false citation as a scope note".

WHY IT NEVER CALLS /brain/bridges/apply
----------------------------------------
That endpoint writes `[[wikilinks]]` into the owner's private vault, and it needs `a_path` /
`b_path`, which the contradiction ledger does not carry -- only titles. Reconstructing a vault
path by guessing from a title, in an unattended loop, against the repo's most fragile asset
(CLAUDE.md rule 1) is not a bridge worth building. And the finding here is precisely that no
honest bridge exists between a note and its own re-run, so there is nothing to link.

GROUNDING
---------
Nothing ships on assertion. Every cycle re-derives the whole classification inside `ctx.lab_run`
from the raw titles and claims, with the falsifier stated in the script's own docstring BEFORE it
computes anything, and the organ then CROSS-CHECKS the lab's counts against its own. If the two
disagree, nothing is written back and the cycle goes idle with the discrepancy -- a number the
artifact that is supposed to prove it cannot reproduce is not a result.

De-duplication is handled at the source rather than by prose matching: a settled record is
written back to the ledger, so it stops being open and the desk drains by CLASS instead of
re-reporting one pair forever. Novelty is the repo-calibrated overlap coefficient
(`server/agora/execution/finding_diversity.py`, threshold 0.60), imported from that file when it
is reachable so the two can never drift, with a verbatim fallback otherwise.
"""
from __future__ import annotations

import inspect
import json
import re
from pathlib import Path

ORGAN = {
    "eid": "guard_r", "agent": "Dame Elara", "name": "Bridge Builder",
    "ledger": ".contradictions.json",
    "decisive": ("bridged", "no honest bridge", "contradiction resolved"),
    "period_hours": 6.0,                      # ~4x/day
}

# --------------------------------------------------------------------------------------------
# The novelty metric. NOT a local invention: the overlap coefficient already calibrated repo-wide
# in server/agora/execution/finding_diversity.py at 0.60. Import the real function when the
# sibling tree is reachable (dungeon and brain live side by side in this repo) so the two cannot
# drift apart; fall back to a verbatim copy when it is not, and SAY which one ran.
# --------------------------------------------------------------------------------------------
NEAR_DUP = 0.6                  # finding_diversity.finding_diversity(threshold=0.6)

_FD_PATH = (Path(__file__).resolve().parents[2]
            / "server" / "agora" / "execution" / "finding_diversity.py")

_STOP = set((
    "the a an of to in on and or for with that this from are is was were be been being it its as at "
    "by we our their they them not no does can will would could should which who whom whose into "
    "about between among across over under more most less than then thus also such these those some "
    "any each both either neither finding findings result results study studies paper papers source"
).split())


def _tokens_local(s: str) -> set:
    return {w for w in re.findall(r"[a-z0-9]+", (s or "").lower()) if len(w) > 3 and w not in _STOP}


def _containment_local(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def _load_metric():
    """Return (tokens, containment, provenance) -- the shared implementation if reachable."""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("_agora_finding_diversity", str(_FD_PATH))
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod._tokens, mod._containment, "server/agora/execution/finding_diversity.py"
    except Exception:
        pass
    return _tokens_local, _containment_local, "vendored copy of finding_diversity._containment"


_tokens, _containment, METRIC_SOURCE = _load_metric()

# The repo's own citation pattern (finding_diversity._CITE): "Author (2019)", "A and B (2019)",
# "Author et al. (2019)". Used here as a BLOCKER, not a feature -- a disputed claim that names a
# source is never auto-dissolved.
_CITE = re.compile(
    r"[A-Z][A-Za-z\-]+(?:\s+(?:and|&)\s+[A-Z][A-Za-z\-]+|\s+et al\.?)?\s*\((?:19|20)\d{2}\)")

_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
_NUM = re.compile(r"-?\d+(?:\.\d+)?")

# Spelled-out values carry the dispute as often as digits do -- "contains ZERO concepts ... but
# also contains FOUR concepts" is the same two-value form as "both 11 and 22". "one" and "two"
# are deliberately ABSENT: in these meta-claims they are almost always determiners ("the TWO
# notes attribute ... ONE to Lee & Yeung"), and admitting them manufactures a two-value dispute
# out of ordinary prose -- which would auto-resolve a record nobody adjudicated.
_WORD_NUM = {"zero": 0.0, "three": 3.0, "four": 4.0, "five": 5.0, "six": 6.0, "seven": 7.0,
             "eight": 8.0, "nine": 9.0, "ten": 10.0, "eleven": 11.0, "twelve": 12.0}

# A claim only counts as a two-value dispute if it also SAYS the two values are in opposition.
# Two numbers in a sentence are not a contradiction; "both X and Y" / "X but also Y" is.
_OPPOSE = ("both", "but also", "and also", "while also", "versus", " vs ", " vs.",
           "whereas", "however", "on the other hand", "note a", "note b")

# Classification labels. The lab script re-derives these independently and the two sets are
# compared before anything is written back, so the strings must stay in step.
K_METRIC = "restatement_metric"      # same note restated; a NUMBER in dispute   -> dissolve
K_CITED = "restatement_cited"        # same note restated; a SOURCE in dispute   -> escalate
K_OPAQUE = "restatement_opaque"      # same note restated; nothing extractable   -> leave open
K_CONFLICT = "belief_conflict"       # distinct notes, numbers disagree          -> report only
K_OTHER = "unclassified"

_FOLD = {"—": "-", "–": "-", "→": "->", "⇄": "<->", "×": "x",
         "‘": "'", "’": "'", "“": '"', "”": '"', "…": "..."}


def _ascii(s) -> str:
    """Console and Telegram are cp1250 -- fold to ASCII rather than risk a 500 on a print."""
    s = "" if s is None else str(s)
    for k, v in _FOLD.items():
        s = s.replace(k, v)
    return s.encode("ascii", "replace").decode("ascii")


def _values(claim: str) -> list:
    """Distinct numeric values a claim puts in dispute; citations and years removed first."""
    txt = _YEAR.sub(" ", _CITE.sub(" ", claim or ""))
    vals = []
    for m in _NUM.findall(txt):
        try:
            vals.append(float(m))
        except ValueError:
            pass
    for w in re.findall(r"[a-z]+", txt.lower()):
        if w in _WORD_NUM:
            vals.append(_WORD_NUM[w])
    out = []
    for v in vals:
        if v not in out:
            out.append(v)
    return out


def _disputes_values(claim: str, vals: list) -> bool:
    return len(vals) >= 2 and any(m in (claim or "").lower() for m in _OPPOSE)


def _classify(rec: dict) -> dict:
    """Objective classification of ONE ledger record. No prose comprehension, no LLM call.

    The only judgements made are measurable ones: how far the two TITLES overlap (the calibrated
    containment), whether the disputed claim names a SOURCE, and whether it sets two values
    against each other. Anything that does not reduce to those is left unclassified on purpose --
    a guess dressed as a verdict is worse than an admitted gap.
    """
    a, b = str(rec.get("a") or ""), str(rec.get("b") or "")
    claim = str(rec.get("claim") or "")
    cont = round(_containment(_tokens(a), _tokens(b)), 3)
    cites = sorted(set(_CITE.findall(claim)))
    vals = _values(claim)
    disputed = _disputes_values(claim, vals)
    if cont >= NEAR_DUP:
        kind = K_CITED if cites else (K_METRIC if disputed else K_OPAQUE)
    else:
        kind = K_CONFLICT if disputed else K_OTHER
    return {"id": rec.get("id"), "a": a, "b": b, "claim": claim,
            "containment": cont, "cites": cites, "values": vals[:4], "kind": kind}


# --------------------------------------------------------------------------------------------
# The lab script. It re-derives the classification from the RAW titles and claims -- it is never
# handed the organ's answer -- and states its falsifier before computing anything, so a run that
# contradicts the organ is a real disagreement and not an echo. It opens with a docstring saying
# what it MODELS, which lab.py:41-72 (`models_line`) is what enforces. Note the two recorded
# counts of that gap differ and are quoted here with their own sources rather than merged: the
# lab.py docstring says 37 of the last 60 runs carried no leading description, while the later
# `/brain/lab/run` docstring in agent_os_api.py says 100% of the last 60 did not.
# --------------------------------------------------------------------------------------------
_LAB = '''"""MODELS: Agora's own open-contradiction ledger, as a classification problem.

Each open record pairs two note TITLES with one disputed CLAIM. The model is that most of these
are not two beliefs in conflict at all, but ONE generated report paired with its own re-run --
the same derived metric measured twice on a vault that grew in between -- and that such a pair
has no honest bridge, only a scope neither side states.

The test: for every record, recompute the overlap coefficient between the two titles' token sets
with the repo-calibrated metric (server/agora/execution/finding_diversity.py, threshold 0.60),
then split the restatements by WHAT is in dispute -- a NUMBER (dissolves under an unstated as-of
scope) or a CITED SOURCE (does not dissolve: one of the two runs misquotes a paper, which is a
defect to escalate, not a scope note).

FALSIFIER, fixed before any number is printed: if fewer than 50% of the open records are title
restatements at containment >= 0.60, this model is FALSE -- the ledger really is holding
independent beliefs in conflict, and every pair must then be adjudicated on its merits instead
of dissolved.
"""
import json
import re

RECORDS = json.loads(r"""__RECORDS__""")

# Verbatim from server/agora/execution/finding_diversity.py -- same stopword set, same tokenizer,
# same overlap coefficient, same 0.60 threshold. Copied rather than imported because this script
# runs as an isolated subprocess out of agora_output/lab.
_STOP = set((
    "the a an of to in on and or for with that this from are is was were be been being it its as at "
    "by we our their they them not no does can will would could should which who whom whose into "
    "about between among across over under more most less than then thus also such these those some "
    "any each both either neither finding findings result results study studies paper papers source"
).split())


def tokens(s):
    return {w for w in re.findall(r"[a-z0-9]+", (s or "").lower()) if len(w) > 3 and w not in _STOP}


def containment(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


CITE = re.compile(
    r"[A-Z][A-Za-z\\-]+(?:\\s+(?:and|&)\\s+[A-Z][A-Za-z\\-]+|\\s+et al\\.?)?\\s*\\((?:19|20)\\d{2}\\)")
YEAR = re.compile(r"\\b(?:19|20)\\d{2}\\b")
NUM = re.compile(r"-?\\d+(?:\\.\\d+)?")
WORD_NUM = {"zero": 0.0, "three": 3.0, "four": 4.0, "five": 5.0, "six": 6.0, "seven": 7.0,
            "eight": 8.0, "nine": 9.0, "ten": 10.0, "eleven": 11.0, "twelve": 12.0}
OPPOSE = ("both", "but also", "and also", "while also", "versus", " vs ", " vs.",
          "whereas", "however", "on the other hand", "note a", "note b")
THRESHOLD = 0.60
FALSIFIER = 0.50


def values(claim):
    txt = YEAR.sub(" ", CITE.sub(" ", claim or ""))
    vals = []
    for m in NUM.findall(txt):
        try:
            vals.append(float(m))
        except ValueError:
            pass
    for w in re.findall(r"[a-z]+", txt.lower()):
        if w in WORD_NUM:
            vals.append(WORD_NUM[w])
    out = []
    for v in vals:
        if v not in out:
            out.append(v)
    return out


rows = []
for r in RECORDS:
    claim = r.get("claim") or ""
    c = containment(tokens(r.get("a") or ""), tokens(r.get("b") or ""))
    cites = sorted(set(CITE.findall(claim)))
    vals = values(claim)
    disputed = len(vals) >= 2 and any(m in claim.lower() for m in OPPOSE)
    if c >= THRESHOLD:
        kind = "restatement_cited" if cites else (
            "restatement_metric" if disputed else "restatement_opaque")
    else:
        kind = "belief_conflict" if disputed else "unclassified"
    rows.append({"id": r.get("id"), "c": c, "kind": kind, "n_cites": len(cites),
                 "vals": vals[:4], "a": (r.get("a") or "")[:52], "b": (r.get("b") or "")[:52]})

n = len(rows)
restate = [r for r in rows if r["c"] >= THRESHOLD]
metric = [r for r in rows if r["kind"] == "restatement_metric"]
cited = [r for r in rows if r["kind"] == "restatement_cited"]
opaque = [r for r in rows if r["kind"] == "restatement_opaque"]
conflict = [r for r in rows if r["kind"] == "belief_conflict"]
rate = (len(restate) / n) if n else 0.0
mean_c = (sum(r["c"] for r in restate) / len(restate)) if restate else 0.0

print("MEASURED: window = %d open contradiction records (every one the read API exposes)" % n)
print("MEASURED: title-restatement rate at containment >= %.2f = %d/%d = %.3f"
      % (THRESHOLD, len(restate), n, rate))
print("MEASURED: mean containment over the restatement pairs = %.3f" % mean_c)
print("MEASURED: dissolve as unstated scope (a NUMBER disputed between a note and its re-run) = %d"
      % len(metric))
print("MEASURED: escalate for a primary-source check (a CITED source disputed) = %d" % len(cited))
print("MEASURED: restatement with nothing extractable (left open, not adjudicated) = %d"
      % len(opaque))
print("MEASURED: independent-belief conflicts (containment < %.2f, two values opposed) = %d"
      % (THRESHOLD, len(conflict)))
for r in rows:
    print("  pair %s containment=%.3f kind=%s cites=%d values=%s | %s <-> %s"
          % (r["id"], r["c"], r["kind"], r["n_cites"], r["vals"], r["a"], r["b"]))
if n == 0:
    print("VERDICT: NO DATA - nothing open to adjudicate")
elif rate >= FALSIFIER:
    print("VERDICT: MODEL HOLDS (%.3f >= %.2f) - the ledger is dominated by a report restating "
          "itself, not by beliefs in conflict. No honest bridge joins a note to its own re-run: "
          "%d dissolve as an unstated scope, %d escalate as a disputed citation."
          % (rate, FALSIFIER, len(metric), len(cited)))
else:
    print("VERDICT: MODEL FALSIFIED (%.3f < %.2f) - these are independent beliefs in conflict and "
          "must be adjudicated pair by pair, not dissolved as scope." % (rate, FALSIFIER))
'''


def _lab_code(records: list) -> str:
    # json.dumps escapes every quote and newline, so the payload can never contain the r\"\"\"
    # delimiter and can never end in a backslash -- the embedding is safe by construction.
    payload = json.dumps([{"id": r.get("id"), "a": r.get("a"), "b": r.get("b"),
                           "claim": r.get("claim")} for r in records], ensure_ascii=True)
    return _LAB.replace("__RECORDS__", payload)


# --------------------------------------------------------------------------------------------
# ctx plumbing. Every call is defensive: a missing helper, a synchronous stub or an HTTP failure
# must degrade into an honest idle or error, never an exception out of cycle().
# --------------------------------------------------------------------------------------------
async def _resolve(value):
    return await value if inspect.isawaitable(value) else value


async def _get(ctx, path: str):
    try:
        return await _resolve(ctx.brain_get(path))
    except Exception:
        return None


async def _post(ctx, path: str, body: dict, timeout: float = 60.0):
    try:
        return await _resolve(ctx.brain_post(path, body, timeout))
    except Exception:
        return None


def _log(ctx, msg: str) -> None:
    try:
        ctx.logger.info("[elara/bridge] %s", _ascii(msg))
    except Exception:
        pass


def _out(status: str, why: str, decisive: bool = False, title: str = "",
         content: str = "", lab_id=None) -> dict:
    return {"status": status, "decisive": decisive, "title": title, "content": content,
            "lab_id": lab_id, "why": _ascii(why)[:400]}


async def _seen_before(ctx, key: str) -> float:
    """Highest containment between this cycle's novelty key and Elara's own memory.

    The key is the CLASS plus the pair titles, never the prose: the boilerplate verdict language
    would otherwise near-match every past cycle and the gate would end up firing on its own
    vocabulary instead of on repetition.
    """
    try:
        hits = await _resolve(ctx.recall("contradiction ledger restatement scope resolution"))
    except Exception:
        return 0.0
    best, kt = 0.0, _tokens(key)
    for h in (hits or [])[:12]:
        if isinstance(h, dict):
            text = " ".join(str(h.get(f) or "") for f in ("title", "content", "text", "value"))
        else:
            text = str(h)
        best = max(best, _containment(kt, _tokens(text)))
    return round(best, 3)


_MEASURED_PATTERNS = {
    "window": r"window = (\d+) open",
    "restated": r"title-restatement rate at containment >= [\d.]+ = (\d+)/",
    "metric": r"dissolve as unstated scope [^=]*= (\d+)",
    "cited": r"escalate for a primary-source check [^=]*= (\d+)",
    "opaque": r"restatement with nothing extractable [^=]*= (\d+)",
    "conflict": r"independent-belief conflicts [^=]*= (\d+)",
}


def _parse_measured(output: str) -> dict:
    """Pull the lab's own counts back out so they can be compared against the organ's."""
    got = {}
    for k, p in _MEASURED_PATTERNS.items():
        m = re.search(p, output or "")
        if m:
            got[k] = int(m.group(1))
    return got


async def cycle(ctx) -> dict:
    """One pass of the contradiction desk. Never raises -- errors come back as status='error'."""
    try:
        return await _cycle(ctx)
    except Exception as exc:                              # noqa: BLE001 - contract: never raise
        _log(ctx, "organ error: %s: %s" % (type(exc).__name__, exc))
        return _out("error", "unhandled %s: %s" % (type(exc).__name__, exc))


async def _cycle(ctx) -> dict:
    # ---- 1. read the ledger ------------------------------------------------------------------
    data = await _get(ctx, "/brain/contradictions")
    if not isinstance(data, dict):
        return _out("error", "GET /brain/contradictions returned no usable payload")
    records = [r for r in (data.get("open") or []) if isinstance(r, dict)]

    # Nothing open -> go LOOK before declaring peace. An organ that reports "all coherent" without
    # having swept is the "vault graph already well-connected" no-op wearing a different hat.
    swept = None
    if not records:
        swept = await _post(ctx, "/brain/contradictions/scan", {}, 240.0)
        data = await _get(ctx, "/brain/contradictions")
        if isinstance(data, dict):
            records = [r for r in (data.get("open") or []) if isinstance(r, dict)]

    # Agora's own beliefs, from the coherence audit. Reported, never adjudicated here:
    # `coherence.audit_once` already files a Dialectic inbox task for each tension it records, and
    # a second organ acting on the same record is duplicated work, not a second opinion. They are
    # also kept OUT of the restatement rate -- two long belief sentences on one subject can share
    # enough vocabulary to cross 0.60 without being the same note, which would inflate the
    # headline with pairs the headline is not about.
    coh = await _get(ctx, "/brain/coherence")
    tensions = []
    if isinstance(coh, dict):
        tensions = [t for t in (coh.get("tensions") or []) if isinstance(t, dict)
                    and t.get("status") == "queued"]

    if not records:
        why = "nothing open in .contradictions.json"
        if isinstance(swept, dict):
            why += " (sweep judged %s pairs, found %s)" % (swept.get("judged"), swept.get("found"))
        if tensions:
            why += "; %d coherence tension(s) already queued to the Dialectic pipeline" % len(tensions)
        _log(ctx, "idle: " + why)
        return _out("idle", why)

    # ---- 2. classify -------------------------------------------------------------------------
    rows = [_classify(r) for r in records]
    by_kind = {k: [r for r in rows if r["kind"] == k]
               for k in (K_METRIC, K_CITED, K_OPAQUE, K_CONFLICT, K_OTHER)}
    to_dissolve = [r for r in by_kind[K_METRIC] if r["id"]]
    to_escalate = [r for r in by_kind[K_CITED] if r["id"]]

    if not to_dissolve and not to_escalate:
        why = ("%d record(s) open, none adjudicable: %d restatements carry no extractable number "
               "or citation, %d are independent-belief conflicts that need re-measurement (no "
               "endpoint settles those), %d unclassified"
               % (len(rows), len(by_kind[K_OPAQUE]), len(by_kind[K_CONFLICT]),
                  len(by_kind[K_OTHER])))
        _log(ctx, "idle: " + why)
        return _out("idle", why)

    # ---- 3. novelty --------------------------------------------------------------------------
    key = " ".join([r["kind"] for r in to_dissolve + to_escalate]
                   + [r["a"] + " " + r["b"] for r in to_dissolve + to_escalate])
    seen = await _seen_before(ctx, key)
    if seen >= NEAR_DUP:
        why = ("these pairs were already adjudicated (containment %.2f >= %.2f against Elara's "
               "own memory)" % (seen, NEAR_DUP))
        _log(ctx, "idle: " + why)
        return _out("idle", why)

    # ---- 4. ground it ------------------------------------------------------------------------
    lab = await _resolve(ctx.lab_run("elara-contradiction-desk: restatement vs belief conflict",
                                     _lab_code(records)))
    if not isinstance(lab, dict) or not lab.get("ok"):
        # `lab` may be None, a dict, or (from a stub) something else entirely -- never call .get
        # on it unguarded, or a failed run turns into an "error" when it is really an honest idle.
        detail = ((lab.get("status") or lab.get("output") or "not ok") if isinstance(lab, dict)
                  else ("no response" if lab is None else str(lab)[:120]))
        _log(ctx, "idle: lab did not complete")
        return _out("idle", "lab run did not complete: %s" % detail)
    lab_id = lab.get("id")
    output = str(lab.get("output") or "")
    if "MEASURED:" not in output or "VERDICT:" not in output:
        return _out("idle", "lab %s produced no MEASURED/VERDICT line" % lab_id)

    # The lab re-derived the classification independently. If its counts disagree with the
    # organ's, one of the two is wrong and NOTHING is written back.
    got = _parse_measured(output)
    mine = {"window": len(rows), "metric": len(by_kind[K_METRIC]), "cited": len(by_kind[K_CITED]),
            "opaque": len(by_kind[K_OPAQUE]), "conflict": len(by_kind[K_CONFLICT]),
            "restated": len([r for r in rows if r["containment"] >= NEAR_DUP])}
    missing = [k for k in mine if k not in got]
    mismatch = {k: (v, got[k]) for k, v in mine.items() if k in got and got[k] != v}
    if missing or mismatch:
        why = ("lab %s disagrees with the organ's own count (mismatch=%s, missing=%s) -- nothing "
               "written back" % (lab_id, mismatch, missing))
        _log(ctx, "idle: " + why)
        return _out("idle", why)

    verdict = next((ln.strip() for ln in output.splitlines() if ln.startswith("VERDICT:")), "")
    if "FALSIFIED" in verdict:
        # The pre-stated falsifier fired: these are independent beliefs in conflict, and this
        # organ has no honest way to pick a winner from titles alone. Say so; settle nothing.
        why = ("falsifier fired -- restatement rate below 0.50, so these are independent beliefs "
               "and none of them may be dissolved as scope (lab %s)" % lab_id)
        _log(ctx, "idle: " + why)
        return _out("idle", why)

    # ---- 5. record the resolutions -----------------------------------------------------------
    applied, queued, failed = [], [], []
    # CARRY THE RECEIPT INTO THE LEDGER. The lab id was going into the contribution text only, so
    # the ledger held 100 closed disputes in 24h with no trace of what closed them and the gate
    # scored this organ GROUNDED 0 while it was producing the measurement every cycle.
    _receipt = ("lab %s | %s" % (lab_id, verdict[:180])) if lab_id else verdict[:220]
    for r in to_dissolve:
        ok = await _post(ctx, "/brain/contradictions/status",
                         {"id": r["id"], "status": "resolved", "evidence": _receipt}, 30.0)
        (applied if isinstance(ok, dict) and ok.get("status") == "ok" else failed).append(r["id"])
    for r in to_escalate:
        ok = await _post(ctx, "/brain/contradictions/status",
                         {"id": r["id"], "status": "queued", "evidence": _receipt}, 30.0)
        (queued if isinstance(ok, dict) and ok.get("status") == "ok" else failed).append(r["id"])

    # VERIFY THE INTERVENTION, not the instrument. `POST /brain/contradictions/status` returns
    # {"status":"ok"} unconditionally -- `set_status` matches on id and returns nothing either
    # way -- so a write against a stale id reports success while the record stays open, and the
    # next cycle would adjudicate it again forever. Re-read and confirm the ids actually left the
    # open set. The page is safe to check against: every id written here came off the first page,
    # and resolving records only pulls the survivors UP, so anything that failed is still on it.
    if applied or queued:
        after = await _get(ctx, "/brain/contradictions")
        if isinstance(after, dict) and isinstance(after.get("open"), list):
            still = {r.get("id") for r in after["open"] if isinstance(r, dict)}
            unmoved = [i for i in applied + queued if i in still]
            if unmoved:
                applied = [i for i in applied if i not in still]
                queued = [i for i in queued if i not in still]
                failed += unmoved

    if queued:
        task = ("Primary-source check (Dame Elara, lab %s): %d generated note pair(s) restate one "
                "report and disagree about a CITED source, so one of the two runs misquotes a "
                "paper. Verify each against the primary source before any of it is cited. "
                % (lab_id, len(queued)))
        for r in to_escalate:
            if r["id"] in queued:
                task += "[%s] %s <-> %s | %s | sources: %s. " % (
                    r["id"], _ascii(r["a"])[:48], _ascii(r["b"])[:48], _ascii(r["claim"])[:120],
                    ", ".join(_ascii(c) for c in r["cites"])[:80])
        await _post(ctx, "/brain/claude-inbox", {"text": task[:1400]}, 30.0)

    if not applied and not queued:
        why = "classified %d records but every status write failed (%s)" % (len(rows), failed[:4])
        _log(ctx, "idle: " + why)
        return _out("idle", why)

    # ---- 6. the finding ----------------------------------------------------------------------
    restated = [r for r in rows if r["containment"] >= NEAR_DUP]
    rate = len(restated) / len(rows)
    mean_c = (sum(r["containment"] for r in restated) / len(restated)) if restated else 0.0
    # Precise, because the endpoint returns a PAGE of the open records and not the whole store:
    # "N of M open records" would read as the entire ledger and overclaim the window.
    title = ("Contradiction desk: %d of the %d open records the read API returns are a report "
             "restating itself, not two beliefs in conflict" % (len(restated), len(rows)))

    lines = [
        "Dame Elara / contradiction desk -- Agora's knowledge audited against itself.",
        "",
        "MEASURED (lab %s; window = the %d open records GET /brain/contradictions returns, which "
        "is that endpoint's page and not the whole store; the metric is the repo-calibrated "
        "overlap coefficient from %s at threshold %.2f):"
        % (lab_id, len(rows), METRIC_SOURCE, NEAR_DUP),
        "- title-restatement rate: %d/%d = %.3f" % (len(restated), len(rows), rate),
        "- mean containment over those pairs: %.3f" % mean_c,
        "- dissolved as an unstated scope (a NUMBER disputed between a note and its own re-run): %d"
        % len(applied),
        "- escalated for a primary-source check (a CITED source in dispute): %d" % len(queued),
        "- left open, nothing extractable to adjudicate: %d" % len(by_kind[K_OPAQUE]),
        "- independent-belief conflicts (containment < %.2f): %d"
        % (NEAR_DUP, len(by_kind[K_CONFLICT])),
        "- Agora's own queued coherence tensions, reported not adjudicated (the Dialectic "
        "pipeline already holds them): %d" % len(tensions),
        "",
        verdict,
        "",
        "VERDICT: no honest bridge joins a note to its own re-run. Where the dispute is a derived "
        "NUMBER, both sides are true under a scope neither states -- the as-of date, or which "
        "argument the report was generated with -- so the contradiction is resolved as a scope "
        "distinction rather than by picking a winner. Where a CITED source is in dispute that "
        "reasoning does NOT transfer: one of the two runs misquotes a paper, which is a defect, "
        "and those are escalated instead of dissolved.",
        "",
        "Contradiction resolved (dissolved as scope):",
    ]
    for r in to_dissolve:
        if r["id"] in applied:
            lines.append("  [%s] containment %.3f, values %s -- %s <-> %s | %s"
                         % (r["id"], r["containment"], r["values"], _ascii(r["a"])[:46],
                            _ascii(r["b"])[:46], _ascii(r["claim"])[:110]))
    if queued:
        lines.append("Escalated -- primary-source check queued, NOT dissolved:")
        for r in to_escalate:
            if r["id"] in queued:
                lines.append("  [%s] containment %.3f, sources %s | %s"
                             % (r["id"], r["containment"],
                                ", ".join(_ascii(c) for c in r["cites"])[:70],
                                _ascii(r["claim"])[:110]))
    if by_kind[K_CONFLICT]:
        lines.append("Still open -- genuinely distinct notes whose numbers disagree. No endpoint "
                     "settles these; they need re-measurement, not a bridge:")
        for r in by_kind[K_CONFLICT][:3]:
            lines.append("  containment %.3f, values %s -- %s"
                         % (r["containment"], r["values"], _ascii(r["claim"])[:130]))
    if failed:
        lines.append("Status write failed for: %s (left open)" % ", ".join(str(f) for f in failed[:6]))
    lines += [
        "",
        "Falsifier, fixed in the lab script before it computed anything: below a 0.50 restatement "
        "rate the model is false and every pair must be adjudicated on its merits. Measured %.3f. "
        "The lab re-derives this classification from the raw titles and claims, and the organ "
        "refuses to write anything back when the two counts disagree." % rate,
        "What this points at: contradictions.py screens generated notes with an explicit "
        "_ARTIFACT_MARKERS list that covers vault-digest but not ARI_*, What_X_Knows_About_Y, "
        "Why_X_Is_Y or the seminar meta notes -- which is why a report ends up arguing with "
        "itself in this ledger. A containment pre-filter on the two titles is cheaper than that "
        "list and generalises to generators nobody has named yet.",
    ]

    _log(ctx, "resolved=%d escalated=%d rate=%.3f lab=%s"
         % (len(applied), len(queued), rate, lab_id))
    return _out("ok",
                "%d contradiction(s) resolved as scope, %d escalated as a disputed citation, "
                "grounded by lab %s" % (len(applied), len(queued), lab_id),
                decisive=True, title=title, content="\n".join(lines), lab_id=lab_id)

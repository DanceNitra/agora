"""swarm_health.py -- THE ACCEPTANCE GATE for the 8-agent research swarm.

This is the instrument that decides when the organ rebuild is DONE. It does not improve any agent;
it refuses to say the batch is finished until every agent has produced serious, attributable,
grounded work in the last 24 hours.

THE OWNER'S BAR (verbatim, do not soften it):

    per agent, last 24h:
      decisive_outcomes >= 1
      attributed_to_real_name == True
      has_lab_id_or_citation == True
    swarm:
      near_dup_rate < 0.30
      agents_with_zero == 0

Exit code is the whole point: 0 ONLY when the bar is met in full. Anything else exits non-zero.

BASELINE MEASURED THE DAY THIS GATE WAS WRITTEN (2026-07-31), i.e. what "broken" looks like:
  * 19 discoveries in 5 days across 8 agents (re-measured here as 17 rows of knowledge_type
    'discovery' in the trailing 5 days -- the two figures differ by the type filter, not by luck;
    either way it is single-digit-per-day for an eight-agent swarm).
  * High Priest Orin, Artificer Rooke and Cartographer Wren at ZERO.
  * 1,417 discovery rows with a blank contributor_name.
  * 2,234 planning cycles in 6 hours producing 0 quests.

AND THE THING THE BASELINE ITSELF GOT WRONG, found while building this gate: all 1,417 blank-name
discovery rows carry contributor_id = 'Artificer Rooke', and a further 1,590 carry
contributor_id = 'Cartographer Wren'. Rooke and Wren are not silent -- they write their name into
the ID column, so every instrument that joins on contributor_name reads them as zero. That is the
same defect class repair_ledger.py was written to catch (measuring your own map instead of the
system), one layer down in the database. This gate therefore resolves attribution through BOTH
columns, counts the work, and still FAILS the agent -- with the reason naming the wrong column --
because `attributed_to_real_name` is exactly the property that is missing.

WHAT IS REUSED, AND WHY NOT REINVENTED (this file measures; it does not invent metrics):
  * repair_ledger._ORGANS / _DECISIVE / _INCONCLUSIVE / _is_decisive -- organ ownership and the
    repo-wide decisive vocabulary. Imported, never copied, so a sibling extending that map extends
    this gate too.
  * finding_diversity(db, n=60, threshold=0.6) -- the calibrated near-duplicate metric. Called
    as-is over a read-only shim; 0.6 containment is the repo's number, not ours.
  * agent_os_api._G_MEASURED / _G_CITE and quality_gate._DOI / _CITES -- the grounding regexes.
    If they cannot be imported this gate FAILS rather than grounding on a pattern it made up.

PER-ORGAN VOCABULARY IS MANDATORY, NOT A NICETY. repair_ledger.py:71 records what happens without
it: "each organ speaks its own vocabulary, and a ledger that only knows one of them reports the
others as idle" -- Wren scored 0 of 80, Orin 10 read as 1, Elara 93 in a day read as 0, and every
error fell AGAINST the agent. Every vocabulary below was read off the live store on 2026-07-31 with
a Counter over its own verdict field, per the rule in that file. Do not extend it from memory.

USAGE
    python probes/swarm_health.py [--server-dir DIR] [--hours 24] [--why] [--json]
    --why   for every FAILING agent, print the most recent thing it actually produced (or
            "nothing ever"), so the failure names the dead layer instead of saying "something
            is wrong".

SAFETY: the database is opened read-only (mode=ro) and the SQL facade refuses anything that is not
a SELECT. The live brain owns that file. This probe never writes to it, never touches :8000.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

# --------------------------------------------------------------------------------------------
# Roster. The owner's table: agent -> eid -> organ -> ledger(s). This is the specification, so it
# is the authority here; where repair_ledger._ORGANS disagrees about ownership we print the
# disagreement rather than silently picking a side.
# --------------------------------------------------------------------------------------------
ROSTER = (
    # (eid,            real name,             organ label,        ledger files)
    ("thief",         "Shadow Kael",          "Research Scout",   (".scout_box.json",)),
    ("scholar",       "Sage Mira",            "Knowledge Curator", (".press.json",)),
    ("priest",        "High Priest Orin",     "Idea Alchemist",   (".analogies.json", ".theory.json")),
    ("king",          "King Aldric",          "Engineering Lead", (".oracle.json",)),
    ("guard_r",       "Dame Elara",           "Bridge Builder",   (".contradictions.json",)),
    ("guard_l",       "Sergeant Voss",        "Quality Assurance", (".bounty.json",)),
    ("artificer",     "Artificer Rooke",      "Replication Unit", (".replications.json",)),
    ("cartographer",  "Cartographer Wren",    "Map-maker",        (".cartography.json",)),
)

# --------------------------------------------------------------------------------------------
# Per-organ ledger specs. Measured 2026-07-31 off the live stores (Counter over the verdict field);
# the owner's stated verdicts are folded in so an organ rebuilt to speak them is scored correctly
# from its first record.
#
#   verdict_fields  fields that may carry a verdict (the decisive scan reads ONLY these, never the
#                   free-text notes -- a note saying "this failed to load" must not score a kill)
#   primary         the field whose value decides inconclusive-vs-decisive first
#   decisive        substrings that mean THIS ENTRY CHANGED SOMETHING (organ's own words + owner's)
#   inconclusive    prefixes that mean work merely STARTED; checked first so nothing talks its way in
#   ts_fields       timestamp fields; the MAX present is when the record reached its current state
#   foreign_text    fields holding verbatim third-party text, excluded from the grounding scan --
#                   a DOI inside a stranger's GitHub issue is not OUR evidence
# --------------------------------------------------------------------------------------------
LEDGERS = {
    ".scout_box.json": dict(
        # live counts 2026-07-31: taken 28 / no_fit 19 / done 8. "taken" is work picked up, not a
        # decision. Owner's vocabulary for this organ is drafted / no_fit.
        verdict_fields=("status", "outcome", "verdict"), primary="status",
        decisive=("drafted", "no_fit", "done", "posted", "declined"),
        inconclusive=("taken", "new", "open", "queued", "pending"),
        # `ruled_ts` FIRST: it is when the Scout DECIDED, which is the work being measured. `found_ts`
        # is when the lead was collected and can be a day older, so a ruling made this cycle on an
        # older lead would otherwise fall outside the window and read as no work at all.
        ts_fields=("ruled_ts", "closed_ts", "taken_ts", "found_ts", "ts"),
        actor_fields=("by", "agent", "author", "actor", "who"),
        foreign_text=("body", "title", "url", "repo"),
    ),
    ".press.json": dict(
        # live counts: published 25 / draft 1.
        verdict_fields=("status", "outcome", "verdict"), primary="status",
        decisive=("published", "merged"),
        inconclusive=("draft", "queued", "pending", "open"),
        ts_fields=("published_ts", "ts"),
        actor_fields=("by", "agent", "author", "actor", "who"),
        foreign_text=(),
    ),
    ".analogies.json": dict(
        # live outcomes are free text: "no viable mapping", "viable", "forged", "SURVIVED (lab
        # 3a7e67): ...", "REJECTED as a bridge + FALSIFIED ...". Substring match is required here.
        verdict_fields=("outcome", "verdict", "status"), primary="outcome",
        decisive=("survived", "corroborated", "strained", "forged", "mapped", "viable",
                  "rejected", "falsified", "refuted", "no viable mapping"),
        inconclusive=("hypothesized", "queued", "pending", "open", "charted"),
        ts_fields=("ts",),
        actor_fields=("by", "agent", "author", "actor", "who"),
        foreign_text=(),
    ),
    ".theory.json": dict(
        # live verdicts: corroborated 4 / strained 2. Both are decisive -- "strained" is a belief
        # that moved, which is the point of the organ.
        verdict_fields=("verdict", "outcome", "status"), primary="verdict",
        decisive=("corroborated", "strained", "survived", "refuted", "falsified", "revised"),
        inconclusive=("hypothesized", "queued", "pending", "open"),
        ts_fields=("ts",),
        actor_fields=("by", "agent", "author", "actor", "who"),
        foreign_text=(),
    ),
    ".oracle.json": dict(
        # The one organ whose decisiveness is not a WORD. A forecast becomes decisive when the
        # market RESOLVES: status flips to 'resolved' and outcome / brier_agora / beat_market
        # appear. Scanning for verdict words alone scores every resolved forecast at 0.
        verdict_fields=("status", "outcome", "verdict"), primary="status",
        decisive=("resolved", "correct", "incorrect", "beat_market"),
        inconclusive=("open", "queued", "pending"),
        ts_fields=("resolved_ts", "ts"),
        actor_fields=("by", "agent", "author", "actor", "who"),
        foreign_text=(),
        resolved_when=("outcome", "brier_agora", "beat_market", "resolved_ts"),
    ),
    ".contradictions.json": dict(
        # live counts: compatible 287 / open 13. repair_ledger.py:83 settled that "compatible" is
        # decisive: Elara EXAMINED the pair and ruled they do not conflict. A negative verdict
        # closes the pair.
        verdict_fields=("status", "outcome", "verdict"), primary="status",
        decisive=("compatible", "resolved", "bridged", "no honest bridge", "no bridge",
                  "no conflict", "contradiction", "reconciled"),
        inconclusive=("open", "queued", "pending"),
        ts_fields=("ts",),
        actor_fields=("by", "agent", "author", "actor", "who"),
        foreign_text=(),
    ),
    ".bounty.json": dict(
        # live counts: survived 20 / revised 10 / retired 1. This store DOES name its actor (`by`).
        verdict_fields=("verdict", "outcome", "status", "kill"), primary="verdict",
        decisive=("kill", "killed", "survived", "revised", "retired", "falsified", "rejected"),
        inconclusive=("open", "queued", "pending", "hypothesized"),
        ts_fields=("ts",),
        actor_fields=("by", "killed_by", "agent", "author", "actor", "who"),
        foreign_text=(),
    ),
    ".replications.json": dict(
        # live counts: REPRODUCED 25 / NOT_COMPUTABLE 22 / FAILED 13. All three are decisive --
        # NOT_COMPUTABLE is a ruling about the claim, not an absence of one.
        verdict_fields=("outcome", "verdict", "status"), primary="outcome",
        decisive=("reproduced", "failed", "not_computable", "not computable"),
        inconclusive=("queued", "pending", "open", "hypothesized", "running"),
        ts_fields=("ts",),
        actor_fields=("by", "agent", "author", "actor", "who"),
        foreign_text=(),
    ),
    ".cartography.json": dict(
        # live counts: hypothesized 68 / no honest bridge 9 / forged 1 / already bridged 1 /
        # charted 1. 68 of 80 stop at "hypothesized" -- a hypothesis nobody is obliged to test --
        # which is precisely the churn this gate exists to refuse.
        verdict_fields=("outcome", "verdict", "status"), primary="outcome",
        decisive=("forged", "no honest bridge", "no bridge", "already bridged", "bridged",
                  "rejected", "falsified"),
        inconclusive=("hypothesized", "charted", "queued", "pending", "open"),
        ts_fields=("resolved_ts", "ts"),
        actor_fields=("by", "agent", "author", "actor", "who"),
        foreign_text=(),
    ),
}

BAR_NEAR_DUP_MAX = 0.30          # swarm: near_dup_rate < 0.30
DIVERSITY_N = 60                 # finding_diversity window, the repo's calibrated setting
DIVERSITY_THRESHOLD = 0.6        # containment threshold, likewise
DB_ROW_CAP = 20000               # sanity cap on rows pulled from the live db


class GateError(Exception):
    """A measurement-integrity failure. Never silently downgraded to a pass."""


# --------------------------------------------------------------------------------------------
# ASCII hygiene. The console here is cp1250: one em dash out of a ledger note kills the print, and
# a gate that crashes while reporting is worse than no gate.
# --------------------------------------------------------------------------------------------
def ascii_only(s: object, limit: int = 0) -> str:
    t = str(s if s is not None else "")
    t = t.replace("—", "-").replace("–", "-").replace("’", "'")
    t = t.replace("“", '"').replace("”", '"').replace("…", "...")
    t = t.encode("ascii", "replace").decode("ascii").replace("\n", " ").replace("\r", " ")
    t = re.sub(r"\s+", " ", t).strip()
    return (t[:limit - 3] + "...") if limit and len(t) > limit else t


# --------------------------------------------------------------------------------------------
# Imports from the repo. Failure to import is a GATE FAILURE, not a fallback: a grounding check
# that quietly swaps in a pattern this file invented is exactly the "measured nothing, reported
# success" defect the owner has been burned by.
# --------------------------------------------------------------------------------------------
def load_repo_parts(code_dirs):
    for d in code_dirs:
        p = str(d.resolve())
        if p not in sys.path:
            sys.path.insert(0, p)
    parts = {}
    try:
        from agora.execution.repair_ledger import (_ORGANS, _DECISIVE, _INCONCLUSIVE,
                                                   _is_decisive)
        parts.update(organs=_ORGANS, rl_decisive=_DECISIVE, rl_inconclusive=_INCONCLUSIVE,
                     rl_is_decisive=_is_decisive)
    except Exception as e:                                          # pragma: no cover - env issue
        raise GateError("cannot import agora.execution.repair_ledger (%s: %s) -- refusing to "
                        "score organs against a map this file invented" % (type(e).__name__, e))
    try:
        from agora.execution.finding_diversity import finding_diversity
        parts["finding_diversity"] = finding_diversity
    except Exception as e:                                          # pragma: no cover - env issue
        raise GateError("cannot import agora.execution.finding_diversity (%s: %s) -- refusing to "
                        "invent a near-duplicate metric" % (type(e).__name__, e))
    try:
        from agora.api.agent_os_api import _G_MEASURED
        # THE CITATION FORK IS FIXED AT THE ROOT NOW (2026-07-31), so this gate no longer has to
        # OR two disagreeing regexes together. What this comment used to say still stands as the
        # evidence: while this gate was being built, the checker returned '' for "Mockus et al.
        # (2002) measured the same split in Apache" -- a real citation scored as ungrounded, an
        # error falling AGAINST the agent. The cause was that quality_gate._CITES matched only the
        # fully-parenthesised "(Mockus et al., 2002)" while finding_diversity._CITE matched only the
        # narrative "Mockus et al. (2002)": mirror images, each rejecting the other's style. SEVEN
        # such detectors existed; measured over the 4,000 most recent discoveries, 1,127 (28.2%)
        # were turned away from the vault while holding a real narrative citation. They now delegate
        # to agora/execution/grounding.py, so this gate asks the SAME question the vault door asks
        # instead of approximating it -- which matters, because a gate that grades grounding
        # differently from the door would pass agents the door rejects, and fail agents it accepts.
        from agora.execution import grounding as _grounding
        parts.update(g_measured=_G_MEASURED, grounding=_grounding)
    except Exception as e:                                          # pragma: no cover - env issue
        raise GateError("cannot import the repo grounding regexes (%s: %s) -- refusing to measure "
                        "grounding with a made-up pattern" % (type(e).__name__, e))
    return parts


# The bar wants a lab id AND a measured marker, but the repo keeps both inside one alternation
# (agent_os_api._G_MEASURED). Rather than re-typing the sub-patterns from memory, they are declared
# here and CHECKED to be literal substrings of the live pattern -- if agent_os_api ever rewrites its
# regex this raises instead of silently matching nothing (a falsification control aimed at nothing
# is the failure mode; assert the target exists).
_LAB_ID_SRC = r"\blab[:_ ]?[0-9a-f]{6}\b"
_MEAS_SRC = r"MEASURED:|VERDICT:"
_LAB_ID = re.compile(_LAB_ID_SRC, re.I)
_MEAS = re.compile(_MEAS_SRC, re.I)


def check_grounding_patterns(parts) -> None:
    src = parts["g_measured"].pattern
    for name, sub in (("lab-id", _LAB_ID_SRC), ("MEASURED:/VERDICT:", _MEAS_SRC)):
        if sub not in src:
            raise GateError("grounding sub-pattern %r is no longer part of "
                            "agent_os_api._G_MEASURED -- the grounding check would silently stop "
                            "matching. Re-derive it from that module before trusting this gate."
                            % name)


def grounding_of(text: str, parts) -> str:
    """'' if ungrounded, else the kind of grounding found.

    The bar: a `lab <6-hex>` id PLUS a MEASURED:/VERDICT: marker, OR a real citation.
    """
    t = text or ""
    if parts["grounding"].is_cited(t):
        return "citation"
    if _LAB_ID.search(t) and _MEAS.search(t):
        return "lab+measured"
    return ""


# --------------------------------------------------------------------------------------------
# Read-only database access. Two independent guards: the sqlite URI is mode=ro, and the facade
# rejects any statement that is not a SELECT.
# --------------------------------------------------------------------------------------------
class _RoCursor:
    def __init__(self, cur):
        self._cur = cur

    async def fetchall(self):
        return self._cur.fetchall()

    async def fetchone(self):
        return self._cur.fetchone()


class RoDb:
    """Minimal async facade over stdlib sqlite3 so the repo's own async finding_diversity() runs
    unmodified without pulling in aiosqlite and without a write handle ever existing."""

    def __init__(self, path: Path):
        if not path.exists():
            raise GateError("database not found: %s" % path)
        uri = "file:%s?mode=ro" % path.resolve().as_posix()
        try:
            self._c = sqlite3.connect(uri, uri=True, timeout=10)
        except sqlite3.Error as e:
            raise GateError("cannot open %s read-only (%s)" % (path, e))
        self._c.row_factory = sqlite3.Row

    async def execute(self, sql, params=()):
        return _RoCursor(self.q(sql, params))

    def q(self, sql, params=()):
        if not sql.lstrip().lower().startswith("select"):
            raise GateError("this probe issues SELECT only; refused: %s" % ascii_only(sql, 60))
        try:
            return self._c.execute(sql, params)
        except sqlite3.Error as e:
            raise GateError("query failed on the live db (%s): %s" % (e, ascii_only(sql, 80)))

    def close(self):
        try:
            self._c.close()
        except Exception:
            pass


# --------------------------------------------------------------------------------------------
# Ledger reading
# --------------------------------------------------------------------------------------------
def load_ledger(server_dir: Path, name: str) -> list:
    """A missing or unparseable ledger raises. It must never read as 'that organ was quiet'."""
    p = server_dir / name
    if not p.exists():
        raise GateError("ledger MISSING: %s (expected in %s)" % (name, server_dir))
    try:
        data = json.loads(p.read_text(encoding="utf-8", errors="replace"))
    except Exception as e:
        raise GateError("ledger UNREADABLE: %s (%s: %s)" % (name, type(e).__name__, e))
    if isinstance(data, dict):
        for key in ("items", "entries", "records", "rows"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
    if not isinstance(data, list):
        raise GateError("ledger SHAPE unexpected: %s holds %s, expected a list of records"
                        % (name, type(data).__name__))
    return [r for r in data if isinstance(r, dict)]


def record_ts(rec: dict, spec: dict) -> float:
    """The most recent timestamp on the record -- when it reached its current state."""
    best = 0.0
    for f in spec["ts_fields"]:
        try:
            v = float(rec.get(f) or 0)
        except (TypeError, ValueError):
            v = 0.0
        best = max(best, v)
    return best


def verdict_blob(rec: dict, spec: dict) -> str:
    return " ".join(str(rec.get(f, "")) for f in spec["verdict_fields"]).lower()


_WORD_RE_CACHE: dict = {}


def _says(blob: str, word: str) -> bool:
    """Word-boundary match, never a raw substring.

    A raw `in` test is how a vocabulary quietly grows false positives: "done" is a substring of
    "abandoned", so a scout store that ever writes status 'abandoned' would score a decision the
    agent never made. A false decisive is the dangerous direction -- it makes the gate bless the
    churn it exists to refuse -- so decisive words are matched on word boundaries.
    """
    rx = _WORD_RE_CACHE.get(word)
    if rx is None:
        rx = _WORD_RE_CACHE[word] = re.compile(r"\b%s\b" % re.escape(word))
    return bool(rx.search(blob))


def is_decisive(rec: dict, spec: dict, parts) -> bool:
    """Decisive = this entry CHANGED something, judged in THIS organ's vocabulary.

    Order matters: the inconclusive prefixes are checked on the primary field first, so a record
    whose outcome is 'hypothesized' can never be talked into counting by a stray word elsewhere.
    repair_ledger._is_decisive is then consulted as a repo-wide safety net, so a sibling that adds
    a new decisive word there is honoured here without editing this file.
    """
    primary = str(rec.get(spec["primary"], "") or "").lower().strip()
    inconclusive = tuple(spec["inconclusive"]) + tuple(parts["rl_inconclusive"])
    if any(primary.startswith(w) for w in inconclusive):
        return False
    if "resolved_when" in spec and any(rec.get(f) is not None for f in spec["resolved_when"]):
        return True
    blob = verdict_blob(rec, spec)
    if any(_says(blob, w) for w in spec["decisive"]):
        return True
    try:
        return bool(parts["rl_is_decisive"](rec))
    except Exception:
        return False


def record_actor(rec: dict, spec: dict) -> str:
    for f in spec["actor_fields"]:
        v = rec.get(f)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


_LAB_FIELDS = ("lab", "lab_id", "labid")


def record_text(rec: dict, spec: dict) -> str:
    """Everything the record says in its own voice -- verbatim third-party text excluded, because
    a DOI inside somebody else's GitHub issue is not evidence WE produced.

    A dedicated lab field is rendered in the canonical "lab <id>" form the repo's own regex looks
    for. That is a FORMAT normalisation of the same datum, not manufactured evidence: .theory.json
    stores {"lab": "672181"} and .replications.json {"lab_id": "8e30bb"}, and an organ that
    dutifully files its lab id in the right field should not be scored ungrounded for it. The
    MEASURED:/VERDICT: half of the bar is never synthesised -- it has to be in the record's text.
    """
    skip = set(spec.get("foreign_text", ()))
    out = []
    for k, v in rec.items():
        if k in skip:
            continue
        if k in _LAB_FIELDS and isinstance(v, (str, int)):
            out.append("lab %s" % v)
        elif isinstance(v, str):
            out.append(v)
        elif isinstance(v, (int, float, bool)):
            out.append("%s=%s" % (k, v))
        elif isinstance(v, (list, dict)):
            out.append(json.dumps(v, ensure_ascii=True)[:2000])
    return " ".join(out)


def record_summary(rec: dict, spec: dict) -> str:
    for f in (spec["primary"],) + tuple(spec["verdict_fields"]):
        v = rec.get(f)
        if isinstance(v, str) and v.strip():
            head = v.strip()
            break
    else:
        head = "(no verdict field)"
    for f in ("claim", "target", "question", "title", "note", "mechanism", "a", "id"):
        v = rec.get(f)
        if isinstance(v, str) and v.strip():
            return "%s :: %s" % (ascii_only(head, 48), ascii_only(v, 70))
    return ascii_only(head, 110)


# --------------------------------------------------------------------------------------------
# Measurement
# --------------------------------------------------------------------------------------------
def measure_db(db: RoDb, hours: float, parts, names) -> dict:
    """Per-agent discoveries in the window, with attribution resolved through BOTH columns.

    created_at is written by sqlite's own `datetime('now')` default (UTC), so the window is
    computed by sqlite too -- comparing a UTC column against a local-time Python clock would have
    silently shifted the window by the machine's offset.
    """
    total = db.q("SELECT COUNT(*) FROM collective_knowledge").fetchone()[0]
    if not total:
        raise GateError("collective_knowledge is EMPTY -- there is nothing to measure, which is a "
                        "failure, not a pass")
    window = "-%g hours" % hours
    rows = db.q(
        "SELECT title, content, contributor_name, contributor_id, created_at "
        "FROM collective_knowledge WHERE knowledge_type='discovery' "
        "AND created_at > datetime('now', ?) ORDER BY created_at DESC LIMIT ?",
        (window, DB_ROW_CAP)).fetchall()
    per = {n: {"discoveries": 0, "named": 0, "id_only": 0, "grounded": 0} for n in names}
    unattributed = 0
    by_name = {n.lower(): n for n in names}
    for r in rows:
        nm = (r["contributor_name"] or "").strip()
        cid = (r["contributor_id"] or "").strip()
        who, mode = "", ""
        if nm.lower() in by_name:
            who, mode = by_name[nm.lower()], "named"
        elif not nm and cid.lower() in by_name:
            # The 1,417-row defect: the real name is in the ID column and contributor_name is
            # blank. Counted as output, reported as DEGRADED attribution -- every other instrument
            # in this repo joins on contributor_name and reads these rows as nobody's.
            who, mode = by_name[cid.lower()], "id_only"
        if not who:
            unattributed += 1
            continue
        a = per[who]
        a["discoveries"] += 1
        a[mode] += 1
        if grounding_of("%s %s" % (r["title"] or "", r["content"] or ""), parts):
            a["grounded"] += 1
    return {"per_agent": per, "rows_in_window": len(rows), "table_rows": total,
            "unattributed_rows": unattributed}


def diversity_span_hours(db: RoDb, n: int) -> float:
    """How much WALL-CLOCK TIME the near-duplicate window actually covers.

    STATE THE NUMBER'S PARAMETERS. finding_diversity looks at the last N findings, not the last N
    hours, so on a starved swarm those 60 findings can span weeks -- and findings weeks apart are
    naturally diverse. Measured 2026-07-31: near_dup_rate is 0.000 over the last 60 findings but
    0.860 over the last 400 at the same 0.6 threshold. The churn is real; a 60-row window cannot
    see it while the swarm produces ~3 findings a day. Report the span so nobody reads 0.000 as
    "the churn is fixed".
    """
    r = db.q("SELECT MIN(created_at) lo, MAX(created_at) hi FROM (SELECT created_at FROM "
             "collective_knowledge WHERE knowledge_type='discovery' ORDER BY created_at DESC "
             "LIMIT ?)", (n,)).fetchone()
    if not r or not r["lo"] or not r["hi"]:
        return 0.0
    fmt = "%Y-%m-%d %H:%M:%S"
    try:
        lo = time.mktime(time.strptime(r["lo"][:19], fmt))
        hi = time.mktime(time.strptime(r["hi"][:19], fmt))
    except ValueError:
        return 0.0
    return max(0.0, (hi - lo) / 3600.0)


def measure_ledgers(server_dir: Path, hours: float, parts) -> dict:
    cutoff = time.time() - hours * 3600.0
    out = {}
    for name, spec in LEDGERS.items():
        recs = load_ledger(server_dir, name)
        rows = []
        for rec in recs:
            ts = record_ts(rec, spec)
            rows.append({"rec": rec, "ts": ts, "in_window": ts > cutoff,
                         "decisive": is_decisive(rec, spec, parts),
                         "actor": record_actor(rec, spec),
                         "grounding": grounding_of(record_text(rec, spec), parts)})
        no_ts = sum(1 for r in rows if not r["ts"])
        if recs and no_ts == len(recs):
            # Windowing a store with no usable timestamp would silently report every record as
            # stale (or every record as fresh). Say so instead of guessing.
            raise GateError("ledger %s has %d records and NO usable timestamp in %s -- a 24h "
                            "window cannot be computed, so this measurement is void"
                            % (name, len(recs), ", ".join(spec["ts_fields"])))
        out[name] = {"rows": rows, "total": len(recs), "no_ts": no_ts}
    return out


def evaluate(db_stats: dict, led_stats: dict, hours: float) -> list:
    agents = []
    for eid, name, organ, files in ROSTER:
        d = db_stats["per_agent"][name]
        decisive = grounded_led = 0
        named_actor = False
        by_organ_only = []
        newest_ts, newest_txt = 0.0, ""
        for f in files:
            spec = LEDGERS[f]
            st = led_stats[f]
            organ_named = organ_decisive = False
            for row in st["rows"]:
                if row["ts"] > newest_ts:
                    newest_ts = row["ts"]
                    newest_txt = "%s  [%s]" % (record_summary(row["rec"], spec), f)
                if not row["in_window"]:
                    continue
                if row["decisive"]:
                    decisive += 1
                    organ_decisive = True
                    # Grounding is credited only on DECISIVE records on purpose: the bar asks for
                    # the work that CLOSED something to be evidence-backed. A grounded record that
                    # decided nothing does not make a verdict defensible.
                    if row["grounding"]:
                        grounded_led += 1
                    if row["actor"] and row["actor"].lower() == name.lower():
                        named_actor = organ_named = True
            # Only a store that actually produced something in the window can be blamed for
            # producing it anonymously; naming an idle ledger here would misdirect the fix.
            if organ_decisive and not organ_named:
                by_organ_only.append(f)
        window_records = sum(1 for f in files for r in led_stats[f]["rows"] if r["in_window"])
        attributed = bool(d["named"]) or named_actor
        grounded = d["grounded"] + grounded_led
        produced = d["discoveries"] + window_records

        reasons = []
        if decisive < 1:
            reasons.append("0 decisive outcomes in %gh (organ ledger %s is not closing anything)"
                           % (hours, "/".join(files)))
        if not attributed:
            if d["id_only"]:
                reasons.append("attribution DEGRADED: %d discovery row(s) name it only in "
                               "contributor_id, contributor_name is blank -- every instrument "
                               "joining on contributor_name reads this agent as zero"
                               % d["id_only"])
            elif decisive:
                reasons.append("no named actor: %d decisive outcome(s) attributed BY ORGAN only "
                               "(%s records no actor) -- write the agent name into a `by` field "
                               "or log the discovery under contributor_name"
                               % (decisive, "/".join(by_organ_only)))
            else:
                reasons.append("nothing attributable in %gh (no named discovery row, no named "
                               "ledger actor)" % hours)
        if grounded < 1:
            reasons.append("0 grounded artifacts: nothing in %gh carries a `lab <6hex>` id with "
                           "MEASURED:/VERDICT:, nor a DOI/arXiv/Author-year citation" % hours)
        agents.append({
            "eid": eid, "agent": name, "organ": organ, "ledgers": list(files),
            "discoveries": d["discoveries"], "named_rows": d["named"], "id_only_rows": d["id_only"],
            "decisive": decisive, "grounded": grounded, "ledger_records": window_records,
            "attributed": attributed, "produced": produced, "pass": not reasons,
            "reasons": reasons, "newest_ts": newest_ts, "newest": newest_txt,
        })
    return agents


# --------------------------------------------------------------------------------------------
# --why : name the dead layer
# --------------------------------------------------------------------------------------------
def last_db_artifact(db: RoDb, name: str):
    r = db.q("SELECT title, knowledge_type, created_at FROM collective_knowledge "
             "WHERE TRIM(COALESCE(contributor_name,'')) = ? "
             "   OR (TRIM(COALESCE(contributor_name,'')) = '' AND contributor_id = ?) "
             "ORDER BY created_at DESC LIMIT 1", (name, name)).fetchone()
    return None if not r else {"when": r["created_at"], "type": r["knowledge_type"],
                               "what": ascii_only(r["title"], 90)}


def print_why(db: RoDb, agents: list) -> None:
    print("")
    print("WHY (last thing each FAILING agent actually produced)")
    print("-" * 118)
    for a in agents:
        if a["pass"]:
            continue
        print("  %s  [%s]" % (a["agent"], a["organ"]))
        if a["newest_ts"]:
            age_h = (time.time() - a["newest_ts"]) / 3600.0
            print("    ledger : %s ago -- %s"
                  % (fmt_age(age_h), ascii_only(a["newest"], 96)))
        else:
            print("    ledger : nothing ever (no timestamped record in %s)"
                  % "/".join(a["ledgers"]))
        d = last_db_artifact(db, a["agent"])
        if d:
            print("    db     : %s (%s) -- %s" % (d["when"], d["type"], d["what"]))
        else:
            print("    db     : nothing ever under this name")
        for r in a["reasons"]:
            print("    FAIL   : %s" % ascii_only(r))
    print("-" * 118)


def fmt_age(hours: float) -> str:
    if hours < 48:
        return "%.1fh" % hours
    return "%.1fd" % (hours / 24.0)


# --------------------------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------------------------
def print_table(agents: list) -> None:
    print("AGENT                 ORGAN               LEDGER-REC  DISC  DECISIVE  GROUNDED  ATTR  "
          "VERDICT")
    print("-" * 118)
    for a in agents:
        print("  %-19s %-19s %8d  %4d  %8d  %8d  %-4s  %s"
              % (ascii_only(a["agent"], 19), ascii_only(a["organ"], 19), a["ledger_records"],
                 a["discoveries"], a["decisive"], a["grounded"],
                 "Y" if a["attributed"] else "N", "PASS" if a["pass"] else "FAIL"))
        for r in a["reasons"]:
            print("      - %s" % ascii_only(r))
    print("-" * 118)


# --------------------------------------------------------------------------------------------
# --self-test : a gate that has never been seen to pass is not a gate.
#
# Builds a synthetic fixture (a database with the production DDL plus all nine ledgers) in which
# all eight agents clear the bar, and checks the gate exits 0. Then knocks out ONE thing at a time
# and checks the exit code flips AND the reason names the right agent -- otherwise a gate could be
# green because it checks nothing, or red for a reason unrelated to the defect.
#
# The fixture is BUILT, not copied from agora.db: the live database is under continuous write by
# the brain, and copying it mid-write can yield a torn file. The DDL below is the one in
# agora/main.py:399, verified against PRAGMA table_info on the live table.
# --------------------------------------------------------------------------------------------
_DDL = """
CREATE TABLE collective_knowledge (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    contributor_id TEXT NOT NULL,
    contributor_name TEXT NOT NULL DEFAULT '',
    knowledge_type TEXT DEFAULT 'observation',
    confidence REAL DEFAULT 0.7,
    verification_count INTEGER DEFAULT 0,
    tags TEXT DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT
);
"""

# One grounded finding per agent. Deliberately disjoint vocabularies: eight paraphrases of one
# claim would trip the near-duplicate bar and the fixture would fail for the wrong reason.
_FIXTURE_FINDINGS = {
    "Shadow Kael": (
        "Issue triage latency predicts maintainer response probability",
        "Across 240 sampled repository threads the interval between issue creation and the first "
        "maintainer comment predicted eventual merge better than patch size. MEASURED: median "
        "latency 31 hours for merged threads versus 196 hours for abandoned ones (lab 3a7e67). "
        "Falsifier: the gap disappears once repository popularity is held fixed."),
    "Sage Mira": (
        "Curated note survival depends on retrieval, not on authorship effort",
        "Notes retrieved at least twice in their first fortnight survived pruning at four times "
        "the base rate, while drafting minutes showed no relationship. MEASURED: survival 0.71 "
        "versus 0.18, n=612 notes (lab 91cd0e). Falsifier: effort predicts survival once early "
        "retrieval is controlled."),
    "High Priest Orin": (
        "Percolation gives the analogy between debt cascades and coherence collapse",
        "Treating shared belief as a connected component reproduces the abrupt coherence loss "
        "seen in obligation networks. VERDICT: corroborated, the transition sits near occupancy "
        "0.75 rather than degrading smoothly (lab 672181). Falsifier: a smooth monotone decline "
        "under randomised occupancy."),
    "King Aldric": (
        "Forecast calibration beat the market on resolved contracts",
        "Thirteen recorded forecasts resolved this quarter; scoring them against contemporaneous "
        "market prices separates skill from drift. MEASURED: Brier 0.0225 for the desk against "
        "0.0410 for the market (lab 11c99e). Falsifier: the edge vanishes after excluding "
        "contracts settled inside a week."),
    "Dame Elara": (
        "Vocabulary drift, not disagreement, drives apparent contradiction between domains",
        "Pairs flagged as contradictory were re-read after normalising terminology; most survived "
        "as compatible. MEASURED: 287 of 300 pairs compatible once shared terms were aligned "
        "(lab 5b2f10). Falsifier: normalisation leaves the contradiction count unchanged."),
    "Sergeant Voss": (
        "Belief challenges retire more claims than they overturn",
        "Adversarial review of standing beliefs was scored by what changed afterwards rather than "
        "by the verdict word. MEASURED: 10 revisions and 1 retirement against 20 survivals, "
        "n=31 challenges (lab 7d4a12). Falsifier: revisions revert within two review cycles."),
    "Artificer Rooke": (
        "Erasure claims fail at the write path, not at the delete primitive",
        "Re-implementing published forgetting routines as minimal models shows the primitive "
        "usually works while nothing calls it. VERDICT: NOT_COMPUTABLE for 22 of 60 claims, "
        "FAILED for 13 (lab 8e30bb). Falsifier: a live caller exists and the value still "
        "survives decryption."),
    "Cartographer Wren": (
        "Most forced domain collisions yield no honest bridge and should be recorded as such",
        "Charting pairs of distant fields and demanding a mechanism, rather than a metaphor, "
        "kills the majority. MEASURED: 9 refusals and 1 forged bridge from 80 charted pairs "
        "(lab 4c1d92). Falsifier: refusals become bridges under an independent reviewer."),
}

# One decisive, in-window record per ledger, in that organ's own vocabulary.
_FIXTURE_LEDGERS = {
    ".scout_box.json": [{"url": "https://example.invalid/repo/issues/1", "repo": "example/repo",
                         "issue_number": 1, "title": "fixture issue", "body": "fixture body",
                         "theme": "agent memory", "score": 0.9, "kind": "contribute",
                         "status": "no_fit", "found_ts": 0.0, "closed_ts": 0.0}],
    ".press.json": [{"id": "fx0001", "title": "fixture post", "body": "fixture body",
                     "source": "fixture", "status": "published", "ts": 0.0,
                     "published_ts": 0.0}],
    ".analogies.json": [{"mechanism": "percolation", "target": "coherence",
                         "note": "fixture", "outcome": "forged", "ts": 0.0}],
    ".theory.json": [{"title": "fixture theory", "verdict": "corroborated", "lab": "672181",
                      "summary": "fixture", "ts": 0.0}],
    ".oracle.json": [{"id": "fx", "market_id": "fx", "question": "fixture?", "market_prob": 0.5,
                      "agora_prob": 0.6, "edge": 0.1, "side": "YES", "reasoning": "fixture",
                      "ends": "2026-12-31", "ts": 0.0, "status": "resolved", "outcome": 1.0,
                      "brier_agora": 0.16, "brier_market": 0.25, "beat_market": True,
                      "resolved_ts": 0.0}],
    ".contradictions.json": [{"id": "fx", "a": "alpha", "b": "beta", "sim": 0.9,
                              "contradict": False, "claim": "fixture", "status": "compatible",
                              "ts": 0.0}],
    ".bounty.json": [{"verdict": "retired", "kill": True, "target": "fixture-belief",
                      "by": "Sergeant Voss", "ts": 0.0}],
    ".replications.json": [{"claim": "fixture claim", "source": "fixture", "outcome": "FAILED",
                            "note": "fixture", "lab_id": "8e30bb", "ts": 0.0}],
    ".cartography.json": [{"a": "Biology", "b": "Economics", "bridges_then": 0, "note": "fixture",
                           "outcome": "no honest bridge", "status": "charted", "ts": 0.0,
                           "id": "fx"}],
}


def build_fixture(root: Path) -> None:
    now = time.time()
    for name, recs in _FIXTURE_LEDGERS.items():
        out = []
        for r in recs:
            r = dict(r)
            for f in LEDGERS[name]["ts_fields"]:
                if f in r:
                    r[f] = now
            out.append(r)
        (root / name).write_text(json.dumps(out, indent=1), encoding="utf-8")
    con = sqlite3.connect(str(root / "agora.db"))
    con.executescript(_DDL)
    for who, (title, content) in _FIXTURE_FINDINGS.items():
        con.execute("INSERT INTO collective_knowledge (title, content, contributor_id, "
                    "contributor_name, knowledge_type) VALUES (?,?,?,?, 'discovery')",
                    (title, content, "fixture-%s" % who.split()[-1].lower(), who))
    con.commit()
    con.close()


def run_gate(server_dir: Path, extra=()) -> tuple:
    """Run the real CLI entry point and parse its JSON. Testing main() rather than an internal is
    deliberate: the exit code is the product, so the exit code is what gets tested."""
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = main(["--server-dir", str(server_dir), "--json"] + list(extra))
    try:
        return rc, json.loads(buf.getvalue())
    except json.JSONDecodeError:
        return rc, {"integrity": ["unparseable output: " + ascii_only(buf.getvalue(), 200)]}


def _reason_text(res: dict, agent: str = "") -> str:
    bits = list(res.get("integrity", [])) + list(res.get("swarm", {}).get("reasons", []))
    for a in res.get("agents", []):
        if not agent or a["agent"] == agent:
            bits += a.get("reasons", [])
    return " | ".join(bits).lower()


def self_test() -> int:
    import shutil
    import tempfile
    checks, root = [], Path(tempfile.mkdtemp(prefix="swarm_health_fixture_"))

    def scenario(label, mutate, want_rc, want_in_reason, agent=""):
        d = root / label
        d.mkdir(parents=True, exist_ok=True)
        build_fixture(d)
        if mutate:
            mutate(d)
        rc, res = run_gate(d)
        why = _reason_text(res, agent)
        ok = (rc == want_rc) and all(w.lower() in why for w in want_in_reason)
        if want_rc == 0:
            ok = ok and res.get("ok") is True
        checks.append((ok, label, rc, want_rc, ascii_only(why, 150)))

    def drop_ledger_record(name):
        def f(d):
            (d / name).write_text("[]", encoding="utf-8")
        return f

    def blank_name(agent):
        def f(d):
            con = sqlite3.connect(str(d / "agora.db"))
            con.execute("UPDATE collective_knowledge SET contributor_id=?, contributor_name='' "
                        "WHERE contributor_name=?", (agent, agent))
            con.commit()
            con.close()
        return f

    def strip_grounding(agent):
        def f(d):
            con = sqlite3.connect(str(d / "agora.db"))
            con.execute("UPDATE collective_knowledge SET content=? WHERE contributor_name=?",
                        ("A broadly worded claim about institutions with no measurement, no "
                         "laboratory identifier and no reference to any external publication "
                         "whatsoever, deliberately unfalsifiable and entirely ungrounded prose.",
                         agent))
            con.commit()
            con.close()
        return f

    def silence(agent, ledger):
        def f(d):
            (d / ledger).write_text("[]", encoding="utf-8")
            con = sqlite3.connect(str(d / "agora.db"))
            con.execute("DELETE FROM collective_knowledge WHERE contributor_name=?", (agent,))
            con.commit()
            con.close()
        return f

    def flood_duplicates(d):
        con = sqlite3.connect(str(d / "agora.db"))
        for i in range(60):
            con.execute("INSERT INTO collective_knowledge (title, content, contributor_id, "
                        "contributor_name, knowledge_type) VALUES (?,?,?,?, 'discovery')",
                        ("Repeated finding", "The same finding restated once more with a "
                         "measured number attached. MEASURED: 0.5 (lab 3a7e67). Repetition %d "
                         "of the identical claim." % i, "fixture-voss", "Sergeant Voss"))
        con.commit()
        con.close()

    def empty_table(d):
        con = sqlite3.connect(str(d / "agora.db"))
        con.execute("DELETE FROM collective_knowledge")
        con.commit()
        con.close()

    def delete_ledger(d):
        (d / ".oracle.json").unlink()

    def corrupt_ledger(d):
        (d / ".bounty.json").write_text("{not json", encoding="utf-8")

    scenario("00_all_pass", None, 0, [])
    scenario("01_rooke_no_decisive", drop_ledger_record(".replications.json"), 1,
             ["0 decisive"], "Artificer Rooke")
    scenario("02_wren_blank_name", blank_name("Cartographer Wren"), 1,
             ["attribution degraded", "contributor_id"], "Cartographer Wren")
    scenario("03_orin_ungrounded", strip_grounding("High Priest Orin"), 1,
             ["0 grounded"], "High Priest Orin")
    scenario("04_kael_silent", silence("Shadow Kael", ".scout_box.json"), 1,
             ["agents_with_zero", "shadow kael"])
    scenario("05_near_dup_flood", flood_duplicates, 1, ["near_dup_rate"])
    scenario("06_empty_table", empty_table, 2, ["empty"])
    scenario("07_missing_ledger", delete_ledger, 2, ["missing"])
    scenario("08_corrupt_ledger", corrupt_ledger, 2, ["unreadable"])

    shutil.rmtree(root, ignore_errors=True)
    print("")
    print("SELF-TEST -- can this gate pass, and does each criterion fail on its own?")
    print("-" * 118)
    for ok, label, rc, want, why in checks:
        print("  %-4s %-22s exit %d (want %d)  %s" % ("ok" if ok else "FAIL", label, rc, want, why))
    bad = [c for c in checks if not c[0]]
    print("-" * 118)
    print("SELF-TEST: %d/%d scenarios behaved as specified" % (len(checks) - len(bad), len(checks)))
    return 1 if bad else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Acceptance gate for the 8-agent swarm. Exit 0 only when the owner's bar is "
                    "met in full.")
    ap.add_argument("--server-dir", default=os.getenv("AGORA_SERVER_DIR"),
                    help="directory holding agora.db and the organ ledgers "
                         "(default: <repo>/server, or $AGORA_SERVER_DIR)")
    ap.add_argument("--hours", type=float, default=24.0, help="window in hours (bar: 24)")
    ap.add_argument("--why", action="store_true",
                    help="for each failing agent, print the last thing it actually produced")
    ap.add_argument("--json", action="store_true", help="machine-readable result on stdout")
    ap.add_argument("--self-test", action="store_true",
                    help="prove on a synthetic fixture that this gate CAN pass, and that each "
                         "criterion fails on its own")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()

    repo = Path(__file__).resolve().parents[1]
    server_dir = Path(args.server_dir).resolve() if args.server_dir else (repo / "server")
    names = [n for _e, n, _o, _f in ROSTER]

    result = {"ok": False, "hours": args.hours, "server_dir": str(server_dir),
              "integrity": [], "warnings": [], "agents": [], "swarm": {}}
    db = None
    try:
        if len(ROSTER) != 8 or len(set(names)) != 8:
            raise GateError("roster is %d agents, expected 8 distinct" % len(set(names)))
        if not server_dir.is_dir():
            raise GateError("server dir not found: %s (pass --server-dir)" % server_dir)
        parts = load_repo_parts([repo / "server", server_dir])
        check_grounding_patterns(parts)

        # Ownership cross-check against repair_ledger._ORGANS. The owner's table in the brief is
        # the specification here, so a disagreement is REPORTED rather than silently resolved
        # either way -- silently preferring one map is how you end up measuring your own map.
        warns = []
        for _eid, name, _organ, files in ROSTER:
            for f in files:
                theirs = parts["organs"].get(f)
                if theirs is None:
                    warns.append("%s (%s) is NOT in repair_ledger._ORGANS -- the repair ledger "
                                 "cannot see this organ" % (f, name))
                elif theirs[0] != name:
                    warns.append("ownership disagreement on %s: this gate credits %s, "
                                 "repair_ledger._ORGANS credits %s" % (f, name, theirs[0]))
        result["warnings"] = warns

        db = RoDb(server_dir / "agora.db")
        db_stats = measure_db(db, args.hours, parts, names)
        led_stats = measure_ledgers(server_dir, args.hours, parts)
        agents = evaluate(db_stats, led_stats, args.hours)

        # Records with no usable timestamp are treated as OUTSIDE the window (the safe direction --
        # they can never manufacture a pass) but they are invisible to the count, so say so.
        for lname, st in led_stats.items():
            if st["no_ts"]:
                warns.append("%s: %d of %d records carry no usable timestamp (%s) and are "
                             "excluded from the window -- they cannot count for or against any "
                             "agent" % (lname, st["no_ts"], st["total"],
                                        ", ".join(LEDGERS[lname]["ts_fields"])))

        div = asyncio.run(parts["finding_diversity"](db, n=DIVERSITY_N,
                                                     threshold=DIVERSITY_THRESHOLD))
        if not div.get("window"):
            raise GateError("near-duplicate rate measured over ZERO findings -- a rate with an "
                            "empty denominator is not a measurement")
        near_dup = float(div["near_dup_rate"])
        span_h = diversity_span_hours(db, DIVERSITY_N)
        zeros = [a["agent"] for a in agents if a["produced"] == 0]

        swarm_reasons = []
        if near_dup >= BAR_NEAR_DUP_MAX:
            swarm_reasons.append("near_dup_rate %.3f >= %.2f (%d of last %d findings have a "
                                 "near-duplicate at containment >= %.1f)"
                                 % (near_dup, BAR_NEAR_DUP_MAX, div["near_dup_count"],
                                    div["window"], DIVERSITY_THRESHOLD))
        if zeros:
            swarm_reasons.append("agents_with_zero = %d (%s produced NOTHING in %gh)"
                                 % (len(zeros), ", ".join(zeros), args.hours))

        result["agents"] = agents
        result["swarm"] = {"near_dup_rate": near_dup, "near_dup_window": div["window"],
                           "near_dup_span_hours": round(span_h, 1),
                           "distinct_sources": div.get("distinct_sources"),
                           "agents_with_zero": len(zeros), "zero_agents": zeros,
                           "rows_in_window": db_stats["rows_in_window"],
                           "unattributed_rows": db_stats["unattributed_rows"],
                           "reasons": swarm_reasons}
        result["ok"] = all(a["pass"] for a in agents) and not swarm_reasons

        if args.json:
            slim = dict(result)
            slim["agents"] = [{k: v for k, v in a.items() if k != "newest"} for a in agents]
            print(json.dumps(slim, indent=2, default=str))
        else:
            print("")
            print("SWARM ACCEPTANCE GATE -- window %gh -- %s"
                  % (args.hours, time.strftime("%Y-%m-%d %H:%M:%S")))
            print("data: %s" % ascii_only(server_dir))
            print("bar : per agent decisive>=1, attributed_to_real_name, lab-id-or-citation ; "
                  "swarm near_dup<%.2f, agents_with_zero==0" % BAR_NEAR_DUP_MAX)
            print("")
            print_table(agents)
            print("SWARM  near_dup_rate %.3f over %d findings (bar < %.2f)  |  agents_with_zero "
                  "%d  |  discovery rows in window %d  |  unattributed rows in window %d"
                  % (near_dup, div["window"], BAR_NEAR_DUP_MAX, len(zeros),
                     db_stats["rows_in_window"], db_stats["unattributed_rows"]))
            for r in swarm_reasons:
                print("      - %s" % ascii_only(r))
            if span_h > args.hours:
                print("      ! CAVEAT: those %d findings span %s, not %gh -- findings that far "
                      "apart are diverse by default, so a low near_dup_rate here is NOT evidence "
                      "the churn is fixed" % (div["window"], fmt_age(span_h), args.hours))
            for w in warns:
                print("WARN  %s" % ascii_only(w))
            if args.why:
                print_why(db, agents)
            print("")
            n_pass = sum(1 for a in agents if a["pass"])
            print("RESULT: %s  (%d/8 agents pass)"
                  % ("PASS - the bar is met" if result["ok"] else "FAIL - the bar is NOT met",
                     n_pass))
        return 0 if result["ok"] else 1

    except GateError as e:
        result["integrity"].append(ascii_only(e))
        if args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            print("")
            print("SWARM ACCEPTANCE GATE -- MEASUREMENT INTEGRITY FAILURE")
            print("  %s" % ascii_only(e))
            print("")
            print("RESULT: FAIL - the gate could not measure. An unmeasured swarm is never a pass.")
        return 2
    except Exception as e:                      # noqa: BLE001 - a crash is an integrity failure
        # An unhandled crash must never leave exit 1, which reads as "the bar is simply unmet".
        # It is exit 2 (could not measure) and the traceback is printed, loudly, on stderr.
        import traceback
        result["integrity"].append("CRASH %s: %s" % (type(e).__name__, ascii_only(e)))
        traceback.print_exc()
        if args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            print("")
            print("SWARM ACCEPTANCE GATE -- CRASHED while measuring (%s: %s)"
                  % (type(e).__name__, ascii_only(e)))
            print("RESULT: FAIL - the gate could not measure. An unmeasured swarm is never a pass.")
        return 2
    finally:
        if db is not None:
            db.close()


if __name__ == "__main__":
    sys.exit(main())

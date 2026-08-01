"""The REPAIR ledger — the second book, beside the creation book.

Agora counted one thing: vault notes, by `author:`. On that instrument, over 14 days, Sage Mira scored
89 of 138 and four agents scored zero. I read that as four broken agents and reported it as such.

It is a measurement error. Writing a note is CREATION. Killing a false belief, replicating someone's
claim and finding it FAILED, burying a dead idea, charting a hole between domains, rejecting an analogy
that does not map -- none of those produce a note, and all of them are the work. A creation metric
applied to repairers reads zero and calls it idle.

Mockus, Fielding & Herbsleb (ACM TOSEM 11(3), 2002) measured the same split in Apache: the top 15
developers produced >83% of modification requests but only 66% of FIXES -- 26 developers per 100 fixes
against 4 per 100 code submissions. Their own conclusion: "participation of wider development community
is more significant in defect repair than in the development of new functionality." Mozilla went
further: 113 people filed half the problem reports and 46 of them wrote no code at all. A member who
produces zero creation artifacts and is still fully productive is a documented organizational form, not
an excuse.

ATTRIBUTION IS HONEST ABOUT ITS LIMITS. Only two of the eleven organ stores record who acted
(.bounty.json `by`, .graveyard.json `killed_by`). Replication, cartography, the analogy forge, the
theory bench, the oracle, the press desk and the scout box record no actor, so their entries are
attributed to the organ's OWNER as defined in CLAUDE.md, and every such row is marked `by_organ` so
nobody later mistakes a design assumption for a measurement.

2026-07-31 -- THE REGISTRY WAS EXTENDED TO ALL EIGHT AGENTS, AND WHY.
The trigger was three agents reading as dead on the DB instrument: over the 5 days to 2026-07-31 a
`contributor_name` read of `collective_knowledge` showed High Priest Orin, Artificer Rooke and
Cartographer Wren at ZERO discoveries. Two of those three zeros were the instrument, not the agent:
3,017 of 17,467 rows carry a BLANK `contributor_name` -- 1,417 of them Rooke's and 1,590 Wren's --
because their `contributor_id` holds the agent NAME where the other six hold the NPC UUID, so the name
column was never filled. Reading through the id, Rooke and Wren each produced 2 rows in that window.
Orin's zero was real: his analogy organ had been idle 150.8h, past the 72h alarm.

That is this file's thesis restated by a different instrument, so the registry was completed to all 8:
one agent, one organ, one ledger, one vocabulary, plus the `eid` that joins an organ to its dungeon
entity and to the DB roster. Measured on the live stores the same day, BEFORE the change:
  scout_box     55 rows ->  0 decisive AND 0 rows reaching repair_ledger() at all (see ts_fields)
  bounty        31 rows -> 11 decisive (20 "survived" rulings unread)
  replications  60 rows -> 35 decisive (25 "REPRODUCED" verdicts unread)
  analogies     22 rows -> 10 decisive ("viable"/"survived"/"shipped" unread)
  press/theory/oracle -- not in the map at all, so Mira's press organ, Orin's theory bench and
  Aldric's oracle were invisible to both the ledger and the starvation alarm.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import NamedTuple

_ROOT = Path(__file__).resolve().parents[2]

#: The eight canonical agent names. These are the KEYS of `agora.agent_os.agent_os.NPC_UUIDS` and the
#: values of `collective_knowledge.contributor_name`; spelling them differently here would silently
#: break every join. Duplicated as a literal rather than imported, because agent_os pulls in the DB
#: layer and this module must stay importable from a probe or a one-line script. The test pins this
#: tuple against NPC_UUIDS so the duplication cannot drift.
ROSTER = ("Shadow Kael", "Sage Mira", "High Priest Orin", "King Aldric",
          "Dame Elara", "Sergeant Voss", "Artificer Rooke", "Cartographer Wren")

#: The Seminar is not a member of the roster: it is all eight co-producing one Contribution.
SEMINAR = "THE SEMINAR (all 8, co-produced)"


class Organ(NamedTuple):
    """One agent, one organ, one ledger file.

    `eid` is the dungeon entity id (agora-game-server/mcp_server.py) -- the join key between this
    registry, the 3D world and anything that needs organ -> agent -> DB `contributor_name`. It is
    carried here so a probe can import ONE map instead of re-deriving a second, drifting copy.

    `ts_fields` exists because not every store writes `ts`. Reading a fixed "ts" off .scout_box.json
    returns 0 for all 55 records, the window filter drops every one of them, and Shadow Kael's organ
    contributes NOTHING to the ledger while looking perfectly healthy -- the same failure as a missing
    verdict word, arriving through the clock instead of the vocabulary. Fields are tried in order and
    the newest one present wins.
    """
    agent: str
    eid: str
    role: str
    actor_field: str | None = None
    ts_fields: tuple[str, ...] = ("ts",)


#: organ store -> Organ(agent, dungeon eid, role, actor field, timestamp fields)
#:
#: THE FIRST VERSION OF THIS MAP COVERED FIVE STORES AND HALF THE ROSTER WENT UNWATCHED. Kael, Mira,
#: Voss and Elara had no organ here at all, so those four could go dark and nothing would fire — an
#: alarm with a blind spot over half the thing it guards, which is the exact defect class this file
#: was written to catch. Worse, it made me report "Elara produces nothing" when .contradictions.json
#: had been written to an hour earlier. I was measuring my map, not the system.
#:
#: Every entry below was read off the live store (2026-07-29, extended 2026-07-31), not assumed.
_ORGANS: dict[str, Organ] = {
    # --- Shadow Kael (thief) -- Research Scout ------------------------------------------------
    # No `ts`: the box writes found_ts on discovery, taken_ts when picked up, closed_ts when we rule
    # on it. closed_ts is OUR decision time (scout.py box_mark), so it leads.
    ".scout_box.json": Organ("Shadow Kael", "thief", "Research Scout", None,
                             ("closed_ts", "taken_ts", "found_ts")),

    # --- Sage Mira (scholar) -- Knowledge Curator ---------------------------------------------
    # NO actor field. `source` looks like one and is NOT: read on the live store it holds the piece's
    # PROVENANCE -- a vault note filename, a Lab id, a cited paper ("Gilovich, Vallone & Tversky
    # (1985)"). Wiring it in as the actor would have invented twenty agents named after notes. Read
    # the store before you trust a field name.
    ".press.json": Organ("Sage Mira", "scholar", "Knowledge Curator"),
    # The CANON is Mira's primary organ per CLAUDE.md and had no store; `.press.json` is the
    # secondary arm's. A curator whose rulings are unqueryable reads as a curator doing nothing.
    ".canon.json": Organ("Sage Mira", "scholar", "Knowledge Curator"),


    # --- High Priest Orin (priest) -- Idea Alchemist -------------------------------------------
    # OWNERSHIP CONFLICT, DECIDED — NOT OVERLOOKED. `agent_activity.py:44` attributes .analogies.json
    # to Sage Mira. This registry gives it to Orin, per CLAUDE.md, which names him the Idea Alchemist
    # who "fuses distant concepts"; forging and rejecting analogies is that job by definition, while
    # Mira's is curation into the vault. agent_activity.py STILL DISAGREES and is owned elsewhere --
    # if you are reconciling the two, this file is the decision and that one is the stale copy.
    ".analogies.json": Organ("High Priest Orin", "priest", "Idea Alchemist"),
    ".theory.json": Organ("High Priest Orin", "priest", "Idea Alchemist (theory bench)"),

    # --- King Aldric (king) -- Engineering Lead / Orchestrator ---------------------------------
    ".oracle.json": Organ("King Aldric", "king", "Engineering Lead (forecast oracle)"),
    ".graveyard.json": Organ("King Aldric", "king", "Engineering Lead (graveyard)", "killed_by"),

    # --- Dame Elara (guard_r) -- Bridge Builder ------------------------------------------------
    ".contradictions.json": Organ("Dame Elara", "guard_r", "Bridge Builder"),  # WAS MISSING once,
    #                                                                          and it is her liveliest

    # --- Sergeant Voss (guard_l) -- Quality Assurance ------------------------------------------
    # OWNERSHIP RESOLVED 2026-07-31: bounty is VOSS's. CLAUDE.md makes him QA who "stress-tests every
    # claim"; the roadmap panel's "Bounty/Court under Aldric" is a UI grouping, and CLAUDE.md wins.
    # The store's `by` field agrees on every record written so far, so this is a resolution, not an
    # override. Aldric keeps the graveyard, which is where a killed belief is buried.
    ".bounty.json": Organ("Sergeant Voss", "guard_l", "Quality Assurance", "by"),

    # --- Artificer Rooke (artificer) -- Replication Unit ---------------------------------------
    ".replications.json": Organ("Artificer Rooke", "artificer", "Replication Unit"),

    # --- Cartographer Wren (cartographer) -- Map-maker -----------------------------------------
    ".cartography.json": Organ("Cartographer Wren", "cartographer", "Map-maker"),

    # NOT an individual's organ. Every record carries a `partners` list naming ALL EIGHT agents —
    # this is the Seminar, where the group co-produces one Contribution. Crediting it to Mira, as the
    # first version of this map did, hands one agent the work eight of them did together and then
    # scores her 0 decisive on a store that has no verdict field at all. Attributed to the group.
    ".contributions.json": Organ(SEMINAR, "", "Group seminar"),
}

#: Public aliases. A sibling probe (probes/swarm_health.py) joins organ -> dungeon agent -> DB
#: `contributor_name` and imports THESE rather than duplicating the map; a second copy of an
#: ownership map is a second copy that goes stale, which is how .analogies.json ended up owned by two
#: different agents in two different files.
ORGANS = _ORGANS
AGENT_EID: dict[str, str] = {o.agent: o.eid for o in _ORGANS.values() if o.agent in ROSTER}
ORGANS_BY_AGENT: dict[str, list[str]] = {}
for _s, _o in _ORGANS.items():
    ORGANS_BY_AGENT.setdefault(_o.agent, []).append(_s)

#: Ownership notes. Both cases that were once open are now DECIDED (see the comments in _ORGANS);
#: this string is what the API surfaces so a reader is never left guessing whether a call was made.
_OWNERSHIP_NOTE = (
    "bounty: RESOLVED to Sergeant Voss (CLAUDE.md QA role beats the roadmap panel's Bounty/Court "
    "grouping; the store's `by` field agrees on every record). analogies: RESOLVED to High Priest "
    "Orin (CLAUDE.md Idea Alchemist); agent_activity.py still credits Sage Mira and is the stale copy."
)

#: A repair is only worth counting when the organ REACHED A VERDICT. Two counts come out of that, and
#: they are never merged: `decisive` (a verdict was reached at all) and `corrective` (the subset that
#: removed or changed something). A replication that reproduces a claim confirms it; one that FAILS
#: removes an error, which is the scarcer and more valuable event -- and the Crucible thesis is built
#: on exactly those. Both are counted, separately.
#:
#: EACH ORGAN SPEAKS ITS OWN VOCABULARY, and a ledger that only knows one of them reports the others
#: as idle. Measured 2026-07-29: the list first held only the replication/bounty words, so
#: Cartographer Wren scored 0 decisive across 80 entries — while 9 of them read "no honest bridge",
#: which is a decision, just a negative one, and one read "already bridged". I reported him as pure
#: volume-without-value on that reading. He was not; I was measuring him in a language he does not
#: speak. Measured again 2026-07-31: a FLAT word list also leaks across organs, so the vocabulary is
#: now keyed BY STORE -- "resolved" is a verdict in the oracle and in the coherence audit and means
#: nothing in the scout box, and a shared list cannot say so.
#: Before adding an organ here, open its store, run a Counter over its outcome/status field, and take
#: ITS words. Do not extend this map from memory.
_DECISIVE: dict[str, tuple[str, ...]] = {
    # Kael: measured no_fit 19, done 8, taken 28 (started, not decided). "drafted" is written by
    # scout.record_contacted and is declared here so a drafted contribution never reads as idle.
    ".scout_box.json": ("no_fit", "done", "drafted", "posted"),

    # Mira: measured published 25, draft 1. "merged" is the canon-merge outcome, declared per the
    # 2026-07-31 assignment; "rejected" closes a piece that will not ship.
    ".press.json": ("published", "merged", "rejected"),

    # Mira, canon bench. The CANON is her primary organ per CLAUDE.md and had no store until
    # 2026-08-01, so it had no vocabulary either. These are organs/scholar.py ORGAN["decisive"]
    # verbatim -- the organ's own declared words, not a new set invented at the reader.
    ".canon.json": ("merged", "rejected", "retired"),

    # Orin, analogy forge: measured no viable mapping 7, survived 5, viable* 6, forged 2, shipped 1,
    # "rejected as a bridge + falsified" 1 -- 22 of 22 records carry one of these.
    ".analogies.json": ("forged", "mapped", "viable", "no viable mapping",
                        "survived", "shipped", "rejected", "falsified"),

    # Orin, theory bench: measured corroborated 4, strained 2. "survived" and "unmodelable" are
    # declared by the assignment and not yet written by the store -- kept so the first one that lands
    # is not read as idle, which is the whole point of this map.
    ".theory.json": ("corroborated", "strained", "unmodelable", "survived"),

    # Aldric, oracle: measured status resolved 6 / open 7. The store encodes the CALL as numbers
    # (`outcome` 0.0/1.0, `brier_*`) and a boolean `beat_market`, not as words -- so "resolved" is the
    # only one of these four that fires today, and `beat_market` fires only because _FLAG_FIELDS
    # renders a true boolean as its own field name. "correct"/"incorrect" are declared, not observed.
    ".oracle.json": ("resolved", "correct", "incorrect", "beat_market"),

    # Aldric, graveyard: measured status dead 18 of 18.
    ".graveyard.json": ("dead", "buried", "killed", "retired", "revised",
                        "falsified", "no viable mapping"),

    # Elara, coherence audit: "compatible" means she EXAMINED the pair and ruled they do not conflict.
    # 287 of her 300 records say that. A negative verdict closes the pair and is exactly as decisive as
    # finding a contradiction — arguably more useful, since it is the outcome nobody bothers to record.
    # "bridged"/"no honest bridge" are declared by the assignment; "resolved" already covers the
    # assignment's "contradiction resolved".
    ".contradictions.json": ("compatible", "resolved", "no conflict",
                             "bridged", "no honest bridge"),

    # Voss, bounty: measured survived 20, revised 10, retired 1 -- 31 of 31. "survived" was ABSENT
    # from the old flat list, so two thirds of his rulings read as no ruling at all. "kill" fires via
    # _FLAG_FIELDS on the boolean.
    ".bounty.json": ("survived", "kill", "killed", "retired", "revised", "rejected", "falsified"),

    # Rooke, Crucible: measured REPRODUCED 25, NOT_COMPUTABLE 22, FAILED 13 -- 60 of 60. "reproduced"
    # was absent, so 25 completed replications read as idle volume.
    ".replications.json": ("reproduced", "failed", "not_computable"),

    # Wren, cartography: a refusal to bridge is a finding, not an absence of one.
    ".cartography.json": ("forged", "no honest bridge", "no bridge", "already bridged", "bridged"),

    # The Seminar has no verdict vocabulary: its quality signal is the boolean `verified`, handled
    # structurally in _is_decisive. Listed so the coverage test sees an entry and so the reason is
    # written down rather than inferred from an absence.
    ".contributions.json": ("verified",),
}

#: THE RULE THAT SHOULD HAVE EXISTED BEFORE THE FIRST ENTRY IN THIS FILE.
#: Three times in one day I scored an agent at zero because this list did not speak its organ's
#: language — Wren (11 decisive, read as 0), Orin (10, read as 1), Elara (93 in a single day, read
#: as 0). Every time the error fell AGAINST the agent, and every time I reported it to the owner as
#: the agent producing nothing. Before adding an organ to _ORGANS: open its store, run a Counter over
#: the outcome/status field, and take ITS words. Do not extend this map from memory.

#: Fallback for a store that somehow has no vocabulary of its own. Over-counting is the safer error
#: here: this file exists because under-counting gets reported to the owner as a broken agent. The
#: test pins every organ to a real entry so this should never be reached.
_ANY_DECISIVE: tuple[str, ...] = tuple(sorted({w for ws in _DECISIVE.values() for w in ws}))

#: The subset of the vocabulary that means something was REMOVED or CHANGED, as opposed to confirmed.
#: Without this split, adding "reproduced"/"survived"/"compatible" to the vocabulary (which had to
#: happen -- they are real verdicts) would quietly erase the distinction the ledger was built on: a
#: stream of confirmations is not the same contribution as one refutation.
_CORRECTIVE: tuple[str, ...] = ("failed", "killed", "kill", "retired", "revised", "rejected",
                                "falsified", "dead", "buried", "not_computable", "unmodelable",
                                "strained", "incorrect", "no_fit", "no viable mapping",
                                "no honest bridge", "no bridge")

#: Outcomes that record only that work STARTED. Counted as repairs, never as decisive — 69 of Wren's
#: 80 entries end here (68 "hypothesized" + 1 "charted"), which is the real defect: a hypothesis
#: nobody is obliged to test. Matched with startswith, because these words arrive with suffixes.
#:
#: SPLIT PER-ORGAN 2026-07-31, and the test is what forced it. A single global list held "draft"
#: (1 press record) beside Kael's decisive "drafted", and startswith made "draft" swallow "drafted" --
#: so a drafted contribution would have read as work-not-yet-done. That is the SAME failure as a
#: missing word, produced by an extra one. An inconclusive word is only inconclusive in the organ
#: that writes it; _INCONCLUSIVE_ANY holds only the generic started-words that collide with nothing.
_INCONCLUSIVE_ANY = ("hypothesized", "charted", "queued", "pending", "open")
_INCONCLUSIVE: dict[str, tuple[str, ...]] = {
    ".canon.json": ("deferred", "escalated"),
    ".scout_box.json": ("taken",),   # 28 records: found and picked up, not yet ruled on
    ".press.json": ("draft",),       # 1 record: written, not shipped
}
#:
#: KNOWN UNDER-COUNT, LEFT UNPAPERED: 2 cartography records carry status "bridged" WITH bridges_now
#: and bridged_ts set, while their `outcome` still reads "hypothesized" -- the bridging path updates
#: status and never rewrites outcome. _CLOSURE_FIELDS reads `outcome` first, so those 2 read
#: inconclusive. That precedence is deliberate: loosening it would let any stray word elsewhere in a
#: record talk a "hypothesized" into counting, which is the leak the guard exists to stop. The fix
#: belongs in cartography.py (write the outcome when you write the status), not here.

#: Fields scanned for verdict words, and the boolean fields rendered as their own NAME when true.
#: `kill: true` used to stringify to "True", which matches nothing -- so the flag that literally says
#: a belief was killed was invisible to the word scan. Kept deliberately small: `contradict` is NOT
#: here, because it records that a pair was FLAGGED, not that it was ruled on.
_BLOB_FIELDS = ("verdict", "outcome", "status", "cause", "kill")
_FLAG_FIELDS = ("kill", "beat_market")

#: Fields consulted, in order, for the record's closure word. A store that closes on `status`
#: (scout box, press, coherence audit) needs status read; a store that also carries an `outcome`
#: (cartography) must NOT have status consulted, or a stale `status` would override the real verdict.
_CLOSURE_FIELDS = ("outcome", "verdict", "status")


def _organ_name(store: str) -> str:
    return store.strip(".").replace(".json", "")


def _load(name: str) -> list:
    try:
        d = json.loads((_ROOT / name).read_text(encoding="utf-8"))
        return d if isinstance(d, list) else []
    except Exception:
        return []


def _ts(rec: dict, fields: tuple[str, ...]) -> float:
    """Newest usable timestamp on a record. Zero means the record carries none at all."""
    for f in fields:
        try:
            v = float(rec.get(f) or 0)
        except (TypeError, ValueError):
            v = 0.0
        if v:
            return v
    return 0.0


def _blob(rec: dict) -> str:
    parts = [str(rec.get(k, "")) for k in _BLOB_FIELDS]
    parts += [k for k in _FLAG_FIELDS if rec.get(k)]
    return " ".join(parts).lower()


def _is_decisive(rec: dict, store: str = "") -> bool:
    """Decisive = this entry REACHED A VERDICT. Checked against the inconclusive list first, because
    'hypothesized' must never be talked into counting by a stray word elsewhere in the record.
    """
    # The Seminar store carries no verdict vocabulary at all — its quality signal is the boolean
    # `verified`, set when a Contribution passed verification. Reading it for outcome words scores
    # every one of 3023 records at 0, which is how the whole organ read as pure volume.
    if "verified" in rec and "claim" in rec:
        return bool(rec.get("verified"))
    closure = ""
    for f in _CLOSURE_FIELDS:
        closure = str(rec.get(f, "") or "").lower().strip()
        if closure:
            break
    if any(closure.startswith(w) for w in _INCONCLUSIVE_ANY + _INCONCLUSIVE.get(store, ())):
        return False
    return any(w in _blob(rec) for w in (_DECISIVE.get(store) or _ANY_DECISIVE))


def _is_corrective(rec: dict, store: str = "") -> bool:
    """The subset of decisive that REMOVED or CHANGED something, rather than confirming it."""
    if not _is_decisive(rec, store):
        return False
    if "verified" in rec and "claim" in rec:
        return False          # a verified Contribution confirms; it does not correct
    return any(w in _blob(rec) for w in _CORRECTIVE)


def repair_ledger(days: float = 14.0) -> dict:
    """Per-agent repair output over a window, beside the note count that already exists.

    Returns `decisive` (the organ reached a verdict) AND `corrective` (the verdicts that removed or
    changed something) because a raw count would let a stream of 'REPRODUCED' or 'survived' verdicts
    look like the same contribution as a FAILED replication. It is not: one confirms, the other
    corrects. Both are work; only one is scarce.
    """
    cutoff = time.time() - days * 86400
    agents: dict[str, dict] = {}
    caveats = []
    for store, organ in _ORGANS.items():
        rows = [r for r in _load(store)
                if isinstance(r, dict) and _ts(r, organ.ts_fields) > cutoff]
        if organ.actor_field is None and rows:
            caveats.append(f"{store}: {len(rows)} entries attributed to {organ.agent} BY ORGAN "
                           f"(the store records no actor)")
        name = _organ_name(store)
        for r in rows:
            who = str((r.get(organ.actor_field) or organ.agent) if organ.actor_field else organ.agent)
            # The eid belongs to WHO ACTED, never to the organ that logged the row. Taking organ.eid
            # here gave Sergeant Voss the eid "king", because the beliefs he kills are buried in
            # Aldric's graveyard and `killed_by` names Voss on Aldric's store. Measured, not guessed.
            a = agents.setdefault(who, {"repairs": 0, "decisive": 0, "corrective": 0,
                                        "eid": AGENT_EID.get(who, ""), "organs": {}})
            a["repairs"] += 1
            a["organs"][name] = a["organs"].get(name, 0) + 1
            if _is_decisive(r, store):
                a["decisive"] += 1
                if _is_corrective(r, store):
                    a["corrective"] += 1
            if organ.actor_field is None:
                a["by_organ"] = True
    return {"window_days": days, "agents": agents,
            "total_repairs": sum(a["repairs"] for a in agents.values()),
            "total_decisive": sum(a["decisive"] for a in agents.values()),
            "total_corrective": sum(a["corrective"] for a in agents.values()),
            "attribution_caveats": caveats}


def starvation_report(idle_alarm_h: float = 72.0) -> dict:
    """Which organs have produced NOTHING recently, and for how long.

    A starved agent is UP and healthy -- it simply never receives work -- so liveness monitoring cannot
    see it. Bounty/Court and the Graveyard sat at zero for 42 days while every health check passed.
    This is the alarm that would have fired: age since the organ's last output, not process liveness.

    With all 8 agents registered, several organs legitimately read STARVING on any given day. That is
    the true state of a research keep, not a bug in the alarm: an organ that fires twice a month is
    starving by this definition and the owner should see it.
    """
    now = time.time()
    out = []
    for store, organ in _ORGANS.items():
        rows = _load(store)
        last = max((_ts(r, organ.ts_fields) for r in rows if isinstance(r, dict)), default=0.0)
        via = "record ts"
        if not last:
            # No per-record timestamp: fall back to file mtime rather than reporting a permanent
            # starve. A false alarm discredits the alarm. (Before ts_fields existed, .scout_box.json
            # landed here and its 55 real records were invisible to repair_ledger() entirely.)
            try:
                last, via = (_ROOT / store).stat().st_mtime, "file mtime"
            except Exception:
                last, via = 0.0, "unreadable"
        idle_h = (now - last) / 3600 if last else float("inf")
        out.append({"organ": _organ_name(store), "owner": organ.agent, "eid": organ.eid,
                    "role": organ.role, "entries": len(rows), "freshness_from": via,
                    "idle_h": round(idle_h, 1) if last else None,
                    "starving": (idle_h > idle_alarm_h)})
    out.sort(key=lambda x: -(x["idle_h"] if x["idle_h"] is not None else 1e9))
    #: Which of the eight are covered at all. An agent absent from _ORGANS cannot starve *visibly*,
    #: and that silence used to read as "produces nothing". Since 2026-07-31 all eight are covered,
    #: so this list is expected to be EMPTY -- if it ever refills, an organ was dropped.
    #: Mira is also measured on the CREATION ledger (authored vault notes, 92 in the last 14 days);
    #: that is now an additional reading of her, not the reason she is missing from this one, because
    #: she is no longer missing -- .press.json is her repair-side organ.
    creation_side = {"Sage Mira": "curation -> authored vault notes (creation ledger), in addition "
                                  "to her .press.json organ below"}
    watched = {o.agent for o in _ORGANS.values()}
    return {"alarm_after_h": idle_alarm_h, "organs": out,
            "starving": [o["organ"] for o in out if o["starving"]],
            "unwatched_agents": sorted(set(ROSTER) - watched),
            "measured_on_the_creation_ledger": creation_side,
            "ownership_caveat": _OWNERSHIP_NOTE}


def format_repair_ledger(days: float = 14.0) -> str:
    """ASCII only — the Telegram path and a cp1250 console both choke on anything else."""
    led, st = repair_ledger(days), starvation_report()
    lines = [f"REPAIR LEDGER (last {days:.0f}d) - the second book, beside note counts",
             f"  total repairs {led['total_repairs']} | decisive (a verdict was reached) "
             f"{led['total_decisive']} | corrective (removed/changed something) "
             f"{led['total_corrective']}"]
    if not led["agents"]:
        lines.append("  NOBODY repaired anything in the window.")
    for who, a in sorted(led["agents"].items(), key=lambda kv: -kv[1]["decisive"]):
        mark = " [by organ]" if a.get("by_organ") else ""
        lines.append(f"  {who:22s} repairs {a['repairs']:4d} | decisive {a['decisive']:4d} "
                     f"| corrective {a['corrective']:4d}{mark}")
    if st["unwatched_agents"]:
        lines.append(f"  UNWATCHED (no organ in the registry): {', '.join(st['unwatched_agents'])}")
    if st["starving"]:
        lines.append(f"  STARVING (no output > {st['alarm_after_h']:.0f}h): {', '.join(st['starving'])}")
    for c in led["attribution_caveats"]:
        lines.append(f"  caveat: {c}")
    return "\n".join(lines)

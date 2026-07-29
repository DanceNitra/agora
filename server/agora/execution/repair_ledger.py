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

ATTRIBUTION IS HONEST ABOUT ITS LIMITS. Only two of the five organ stores record who acted
(.bounty.json `by`, .graveyard.json `killed_by`). Replication, cartography and the analogy forge record
no actor, so their entries are attributed to the organ's OWNER as defined in CLAUDE.md, and every such
row is marked `by_organ` so nobody later mistakes a design assumption for a measurement.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]

#: organ store -> (owning agent, the field naming the actor if the store records one)
#:
#: THE FIRST VERSION OF THIS MAP COVERED FIVE STORES AND HALF THE ROSTER WENT UNWATCHED. Kael, Mira,
#: Voss and Elara had no organ here at all, so those four could go dark and nothing would fire — an
#: alarm with a blind spot over half the thing it guards, which is the exact defect class this file
#: was written to catch. Worse, it made me report "Elara produces nothing" when .contradictions.json
#: had been written to an hour earlier. I was measuring my map, not the system.
#:
#: Every entry below was read off the live store on 2026-07-29, not assumed.
_ORGANS = {
    ".bounty.json":        ("Sergeant Voss", "by"),          # belief challenges; `by` names the actor
    ".graveyard.json":     ("King Aldric", "killed_by"),     # buried ideas; `killed_by` names it
    ".replications.json":  ("Artificer Rooke", None),
    ".cartography.json":   ("Cartographer Wren", None),
    ".analogies.json":     ("High Priest Orin", None),
    ".contradictions.json": ("Dame Elara", None),            # WAS MISSING — and it is her liveliest
    ".scout_box.json":     ("Shadow Kael", None),            # no ts field; freshness via mtime
    # NOT an individual's organ. Every record carries a `partners` list naming ALL EIGHT agents —
    # this is the Seminar, where the group co-produces one Contribution. Crediting it to Mira, as the
    # first version of this map did, hands one agent the work eight of them did together and then
    # scores her 0 decisive on a store that has no verdict field at all. Attributed to the group.
    ".contributions.json": ("THE SEMINAR (all 8, co-produced)", None),
}

#: Stores whose records carry NO `ts`, so per-record age is unavailable and file mtime is the only
#: freshness signal there is. Reading `ts` on these returns 0 and would report them permanently
#: starving — a false alarm is as useless as a missing one.
_NO_TS = {".scout_box.json", ".predictions.json", ".topics.json"}

#: Ownership that could not be settled from the code and is NOT guessed here. CLAUDE.md gives Voss
#: belief-challenge duty while the roadmap panel labels Bounty/Court as Aldric's instrument; the
#: bounty store's own `by` field is therefore the authority, and Aldric is credited only through the
#: graveyard. Stated so nobody later mistakes this for a measured fact.
_AMBIGUOUS_OWNERSHIP = ("bounty: CLAUDE.md assigns belief challenges to Voss, the roadmap panel "
                        "shows Bounty/Court under Aldric. The store's `by` field decides per record.")

#: A repair is only worth counting when it CHANGED the knowledge base. A replication that reproduces a
#: claim confirms it; one that FAILS removes an error, which is the scarcer and more valuable event --
#: and the Crucible thesis is built on exactly those. Both are counted, separately, never merged.
#: EACH ORGAN SPEAKS ITS OWN VOCABULARY, and a ledger that only knows one of them reports the others
#: as idle. Measured 2026-07-29: this list first held only the replication/bounty words, so
#: Cartographer Wren scored 0 decisive across 80 entries — while 9 of them read "no honest bridge",
#: which is a decision, just a negative one, and one read "already bridged". I reported him as pure
#: volume-without-value on that reading. He was not; I was measuring him in a language he does not
#: speak. Before adding an organ here, read its store and take ITS words.
_DECISIVE = ("failed", "killed", "retired", "revised", "rejected", "falsified", "dead",
             "not_computable", "buried",
             # cartography (Wren): a refusal to bridge is a finding, not an absence of one
             "no honest bridge", "no bridge", "already bridged", "forged",
             # analogy forge (Orin)
             "no viable mapping", "mapped",
             # coherence audit (Elara): "compatible" means she EXAMINED the pair and ruled they do
             # not conflict. 289 of her 300 records say that. A negative verdict closes the pair and
             # is exactly as decisive as finding a contradiction — arguably more useful, since it is
             # the outcome nobody bothers to record.
             "compatible", "resolved", "no conflict")

#: THE RULE THAT SHOULD HAVE EXISTED BEFORE THE FIRST ENTRY IN THIS FILE.
#: Three times in one day I scored an agent at zero because this list did not speak its organ's
#: language — Wren (11 decisive, read as 0), Orin (10, read as 1), Elara (93 in a single day, read
#: as 0). Every time the error fell AGAINST the agent, and every time I reported it to the owner as
#: the agent producing nothing. Before adding an organ to _ORGANS: open its store, run a Counter over
#: the outcome/status field, and take ITS words. Do not extend this tuple from memory.

#: Outcomes that record only that work STARTED. Counted as repairs, never as decisive — 68 of Wren's
#: 80 entries end here, which is the real defect: a hypothesis nobody is obliged to test.
_INCONCLUSIVE = ("hypothesized", "charted", "queued", "pending", "open")


def _load(name: str) -> list:
    try:
        d = json.loads((_ROOT / name).read_text(encoding="utf-8"))
        return d if isinstance(d, list) else []
    except Exception:
        return []


def _is_decisive(rec: dict) -> bool:
    """Decisive = this entry CHANGED the knowledge base. Checked against the inconclusive list first,
    because 'hypothesized' must never be talked into counting by a stray word elsewhere in the record.
    """
    # The Seminar store carries no verdict vocabulary at all — its quality signal is the boolean
    # `verified`, set when a Contribution passed verification. Reading it for outcome words scores
    # every one of 3023 records at 0, which is how the whole organ read as pure volume.
    if "verified" in rec and "claim" in rec:
        return bool(rec.get("verified"))
    blob = " ".join(str(rec.get(k, "")) for k in ("verdict", "outcome", "status", "cause", "kill")).lower()
    outcome = str(rec.get("outcome", "") or rec.get("verdict", "")).lower().strip()
    if any(outcome.startswith(w) for w in _INCONCLUSIVE):
        return False
    return any(w in blob for w in _DECISIVE)


def repair_ledger(days: float = 14.0) -> dict:
    """Per-agent repair output over a window, beside the note count that already exists.

    Returns totals AND `decisive` (the repairs that removed or changed something) because a raw count
    would let a stream of 'REPRODUCED' or 'survived' verdicts look like the same contribution as a
    FAILED replication. It is not: one confirms, the other corrects.
    """
    cutoff = time.time() - days * 86400
    agents: dict[str, dict] = {}
    caveats = []
    for store, (owner, actor_field) in _ORGANS.items():
        rows = [r for r in _load(store) if isinstance(r, dict) and float(r.get("ts", 0) or 0) > cutoff]
        if actor_field is None and rows:
            caveats.append(f"{store}: {len(rows)} entries attributed to {owner} BY ORGAN "
                           f"(the store records no actor)")
        for r in rows:
            who = (r.get(actor_field) or owner) if actor_field else owner
            a = agents.setdefault(str(who), {"repairs": 0, "decisive": 0, "organs": {}})
            a["repairs"] += 1
            a["organs"][store.strip(".").replace(".json", "")] = \
                a["organs"].get(store.strip(".").replace(".json", ""), 0) + 1
            if _is_decisive(r):
                a["decisive"] += 1
            if actor_field is None:
                a["by_organ"] = True
    return {"window_days": days, "agents": agents,
            "total_repairs": sum(a["repairs"] for a in agents.values()),
            "total_decisive": sum(a["decisive"] for a in agents.values()),
            "attribution_caveats": caveats}


def starvation_report(idle_alarm_h: float = 72.0) -> dict:
    """Which organs have produced NOTHING recently, and for how long.

    A starved agent is UP and healthy -- it simply never receives work -- so liveness monitoring cannot
    see it. Bounty/Court and the Graveyard sat at zero for 42 days while every health check passed.
    This is the alarm that would have fired: age since the organ's last output, not process liveness.
    """
    now = time.time()
    out = []
    for store, (owner, _f) in _ORGANS.items():
        rows = _load(store)
        last = max((float(r.get("ts", 0) or 0) for r in rows if isinstance(r, dict)), default=0.0)
        via = "record ts"
        if not last:
            # No per-record timestamp: fall back to file mtime rather than reporting a permanent
            # starve. Three stores are in this shape, and a false alarm discredits the alarm.
            try:
                last, via = (_ROOT / store).stat().st_mtime, "file mtime"
            except Exception:
                last, via = 0.0, "unreadable"
        idle_h = (now - last) / 3600 if last else float("inf")
        out.append({"organ": store.strip(".").replace(".json", ""), "owner": owner,
                    "entries": len(rows), "freshness_from": via,
                    "idle_h": round(idle_h, 1) if last else None,
                    "starving": (idle_h > idle_alarm_h)})
    out.sort(key=lambda x: -(x["idle_h"] if x["idle_h"] is not None else 1e9))
    #: Which of the eight are covered at all. An agent absent from _ORGANS cannot starve *visibly*,
    #: and that silence used to read as "produces nothing".
    roster = {"Shadow Kael", "Sage Mira", "High Priest Orin", "King Aldric",
              "Dame Elara", "Sergeant Voss", "Artificer Rooke", "Cartographer Wren"}
    #: Agents whose organ is CREATION, not repair. Their absence from this ledger is correct, not a
    #: blind spot — Mira curates findings into the vault and is measured by authored notes (92 in the
    #: last 14 days). Listing her under `unwatched_agents` would read as a gap and invite the same
    #: false "produces nothing" conclusion this file exists to prevent.
    creation_side = {"Sage Mira": "curation -> authored vault notes (creation ledger)"}
    watched = {o for _s, (o, _f) in _ORGANS.items()}
    return {"alarm_after_h": idle_alarm_h, "organs": out,
            "starving": [o["organ"] for o in out if o["starving"]],
            "unwatched_agents": sorted(roster - watched - set(creation_side)),
            "measured_on_the_creation_ledger": creation_side,
            "ownership_caveat": _AMBIGUOUS_OWNERSHIP}


def format_repair_ledger(days: float = 14.0) -> str:
    """ASCII only — the Telegram path and a cp1250 console both choke on anything else."""
    led, st = repair_ledger(days), starvation_report()
    lines = [f"REPAIR LEDGER (last {days:.0f}d) - the second book, beside note counts",
             f"  total repairs {led['total_repairs']} | decisive (removed/changed something) "
             f"{led['total_decisive']}"]
    if not led["agents"]:
        lines.append("  NOBODY repaired anything in the window.")
    for who, a in sorted(led["agents"].items(), key=lambda kv: -kv[1]["decisive"]):
        mark = " [by organ]" if a.get("by_organ") else ""
        lines.append(f"  {who:22s} repairs {a['repairs']:3d} | decisive {a['decisive']:3d}{mark}")
    if st["starving"]:
        lines.append(f"  STARVING (no output > {st['alarm_after_h']:.0f}h): {', '.join(st['starving'])}")
    for c in led["attribution_caveats"]:
        lines.append(f"  caveat: {c}")
    return "\n".join(lines)

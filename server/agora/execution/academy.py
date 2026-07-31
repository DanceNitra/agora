"""
The Academy — the firm trains its own people, and measures whether the training works.

Mastery already records whose findings survive verification; nothing acted on it. The Academy
pairs the weakest verifier (the mentee) with the strongest (the mentor): the mentee's discovery
prompts carry the mentor's discipline — one sharp rule reflecting how the mentor actually works —
until the mentee's verification rate measurably improves (graduation) or doesn't (the lesson
rotates). No vibes: enrollment snapshots the rate, graduation requires +0.10 on >=4 new
attempts. A company whose people measurably improve is the only kind that compounds.

TWO rule sets, because they answer two different questions:

  _LESSONS       — each agent's OWN standing organ discipline. Always injected into that agent's
                   discovery prompt (dungeon `_academy_lesson`, 1h cache), enrolled or not. This
                   is the cheapest per-agent behavioural lever we have: one row changes what an
                   agent does. Each row names the organ, its DECISIVE verdicts, and the grounding
                   requirement (a `lab <id>` carrying MEASURED: and VERDICT:, or a real citation)
                   — ungrounded output is dropped at the gate anyway (quality_gate
                   `_real_grounding`; the promote filter wants "Source:" or MEASURED:+VERDICT:),
                   so an agent that does not know this burns its whole cycle.
  _MENTOR_RULES  — the TRANSFERABLE discipline a mentor hands to a mentee. Deliberately organ-
                   agnostic: transplanting a mentor's organ rule (e.g. Rooke's "hunt claims where
                   FAILED is live") into a mentee working a different organ would steer it OFF its
                   own mission. The mentor rule layers ON TOP of the mentee's organ discipline.

WHY the 2026-07-31 rewrite (measured, not felt): in the 5 days before it, Orin, Rooke and Wren
produced ZERO discoveries each while the whole 8-agent swarm produced 19 in total. The organs
existed; the agents were never told what a WIN looks like on them. So every lesson now states
that a NEGATIVE verdict (no_fit, a rejected finding, strained, a wrong forecast, "compatible",
"no honest bridge", FAILED, survived-with-a-named-killer) is a first-class RESULT — an agent
rewarded only for positives manufactures them, which is exactly the churn we were paying for
(Elara's organ logged "vault graph already well-connected" 23 times in 6 hours).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

_STORE = Path(__file__).resolve().parents[2] / ".academy.json"
_MIN_ATTEMPTS = 4          # both to enroll (mentee history) and to graduate (new evidence)
_GRADUATE_GAIN = 0.10

# Each agent's STANDING organ discipline — always injected into that agent's own discovery prompt.
# Keys MUST equal NPC_UUIDS exactly (looked up by full name; a typo silently returns no lesson —
# see tests/test_academy_lessons.py). ASCII only: these strings reach a cp1250 console.
#
# Register: terse, concrete, names the organ + its DECISIVE verdicts + the grounding requirement,
# and makes the NEGATIVE verdict a first-class RESULT so nobody manufactures positives.
#
# The verdict words are the ones the LIVE STORES actually contain (counted 2026-07-31, not assumed):
#   .scout_box.json  taken 28 / no_fit 19 / done 8      .contradictions.json  compatible 287 / open 13
#   .analogies.json  no viable mapping / viable / forged / "SURVIVED (lab <id>)"
#   .theory.json     corroborated 4 / strained 2        .bounty.json  survived 20 / revised 10 / retired 1
#   .cartography.json  charted 73 / bridged 7, outcome hypothesized 68 / "no honest bridge" 9
#   .replications.json  REPRODUCED 25 / NOT_COMPUTABLE 22 / FAILED 13   .oracle.json  open / resolved
# Writing a verdict in the wrong organ's language is how repair_ledger scored three agents at ZERO
# (see repair_ledger.py) — an agent obeying a lesson must not be the next victim of that class.
#
# NOTE — a lesson states what the FIRM values, never what the scorer pays. It must not claim a
# negative verdict "scores as high as" a positive one: metabolism.py pays drafted 2.0 vs 0.5,
# published 5.0 vs 1.0, bridged 4.0 vs 1.0, kill 3.0 vs 0.75. Only replication is verdict-neutral
# (FAILED == REPRODUCED == 2.5, deliberately, as an anti-manufactured-FAILED guard). Asserting a
# parity the code contradicts would be exactly the kind of unverified claim we gate everywhere else.
_LESSONS = {
    "Shadow Kael":
        "Scout (.scout_box.json): if a live thread's last 5+ comments carry no OWNER/MEMBER/"
        "COLLABORATOR reply it is an automated loop, not an audience -- mark it no_fit and move on, a "
        "no_fit is a real result. Any draft rests on a real source or a lab <id> with MEASURED: and VERDICT:.",
    "Sage Mira":
        "Curate by REPLACING, not appending: a finding that contradicts the canon must CHANGE it, and "
        "rejecting a finding is a real curation result -- accretion is the failure. Anything merged or "
        "published carries a real citation or a lab <id> with MEASURED: and VERDICT:.",
    "High Priest Orin":
        "An analogy needs a shared MECHANISM you can name, never a surface resemblance: record survived "
        "or 'no viable mapping' (.analogies.json), corroborated/strained/unmodelable (.theory.json) -- "
        "the negative verdict is a real result. Ground it: a lab <id> with MEASURED: and VERDICT:, or a real source.",
    "King Aldric":
        "Forecast (.oracle.json) only what a NAMED metric resolves, state confidence BEFORE the outcome, "
        "and resolve every forecast that comes due -- one you got WRONG is a real result; beat_market is "
        "derived from Brier, never claimed. Name the resolver: a real source or a lab <id> with MEASURED: and VERDICT:.",
    "Dame Elara":
        "Rule a NAMED pair of notes (.contradictions.json): they contradict -- say which claim must "
        "change -- or they are compatible, which is a real verdict. 'The vault graph is already well-"
        "connected' is a no-op, not work. Cite both sides: a real source or a lab <id> with MEASURED: and VERDICT:.",
    "Sergeant Voss":
        "Before recording survived (.bounty.json), state what WOULD have killed the belief -- a challenge "
        "that could not kill is not a test. A kill (revised or retired) is the win; survived counts only "
        "with its killer named. Ground both: a real citation or a lab <id> with MEASURED: and VERDICT:.",
    "Artificer Rooke":
        "Replicate (.replications.json) only claims where FAILED is a live possibility -- a claim too "
        "safe to fail wastes the run. FAILED is our rarest export and NOT_COMPUTABLE an honest pass, "
        "neither is a miss. Every verdict needs a lab <id> with MEASURED: and VERDICT:, or a real citation.",
    "Cartographer Wren":
        "Chart a domain pair to a VERDICT (.cartography.json): 'bridged' names the shared mechanism, "
        "'no honest bridge' is an equally real result -- never force a connection to produce an output, "
        "and charted/hypothesized is not a verdict. Ground it: a real source or a lab <id> with MEASURED: and VERDICT:.",
}

# The transferable discipline a mentor hands to its mentee (organ-agnostic on purpose — see docstring).
# ASCII, same reason as above: this text is concatenated into the same prompt string.
_MENTOR_RULES = {
    "Sergeant Voss": "Before claiming, name the weakest assumption -- if you can't, don't ship it.",
    "Sage Mira": "State the claim in ONE precise sentence and cite the paper's actual result, not its topic.",
    "Artificer Rooke": "Include the NUMBER the source measured; a claim without a number is a vibe.",
    "Dame Elara": "Say which existing note this connects to -- an unconnected claim is probably unread.",
    "High Priest Orin": "Name the mechanism, not the correlation -- what would make this true?",
    "King Aldric": "Say what someone could BUILD from this claim; unusable truths rank last.",
    "Shadow Kael": "State what would surprise us if false -- no stake, no finding.",
    "Cartographer Wren": "Name the domain this claim lives in and its nearest foreign neighbor.",
}


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


def active_enrollment() -> dict | None:
    return next((x for x in _load() if x.get("status") == "active"), None)


def lesson_for(agent_name: str) -> str:
    """The rule to inject into this agent's discovery prompts.

    Always this agent's own organ discipline (that is the per-agent lever — it must fire whether or
    not the Academy has an active pair), plus the mentor's transferable rule while it is the mentee.
    Returns '' only for an unknown name.
    """
    base = _LESSONS.get(agent_name, "")
    e = active_enrollment()
    if e and e.get("mentee") == agent_name and e.get("lesson"):
        mentor = f"MENTOR'S RULE (from {e['mentor']}): {e['lesson']}"
        return f"{base} {mentor}".strip()
    return base


def tick() -> dict:
    """Enroll a new pair, or measure the active mentee for graduation/rotation."""
    from agora.execution.mastery import scores
    s = scores()
    rated = {n: v for n, v in s.items() if v["rate"] is not None and v["total"] >= _MIN_ATTEMPTS}
    items = _load()
    e = next((x for x in items if x.get("status") == "active"), None)

    if e:
        cur = rated.get(e["mentee"])
        if not cur:
            return {"status": "active", "mentee": e["mentee"], "note": "no new data yet"}
        new_attempts = cur["total"] - e["total_at_enroll"]
        if new_attempts < _MIN_ATTEMPTS:
            return {"status": "active", "mentee": e["mentee"],
                    "note": f"{new_attempts}/{_MIN_ATTEMPTS} new attempts"}
        gain = round(cur["rate"] - e["rate_at_enroll"], 3)
        e["rate_now"], e["gain"], e["resolved_ts"] = cur["rate"], gain, time.time()
        e["status"] = "graduated" if gain >= _GRADUATE_GAIN else "rotated"
        _save(items)
        return {"status": e["status"], "mentee": e["mentee"], "mentor": e["mentor"], "gain": gain}

    if len(rated) < 2:
        return {"status": "idle", "note": "not enough rated agents"}
    mentor_name = max(rated, key=lambda n: rated[n]["rate"])
    mentee_name = min(rated, key=lambda n: rated[n]["rate"])
    if mentor_name == mentee_name or rated[mentor_name]["rate"] - rated[mentee_name]["rate"] < 0.15:
        return {"status": "idle", "note": "no meaningful mentor-mentee gap"}
    rec = {"mentee": mentee_name, "mentor": mentor_name,
           "lesson": _MENTOR_RULES.get(mentor_name,
                                       "Cite the exact result; name the weakest assumption."),
           "rate_at_enroll": rated[mentee_name]["rate"],
           "total_at_enroll": rated[mentee_name]["total"],
           "status": "active", "ts": time.time()}
    items.append(rec)
    _save(items[-40:])
    return {"status": "enrolled", "mentee": mentee_name, "mentor": mentor_name,
            "rate": rated[mentee_name]["rate"]}


def format_academy() -> str:
    items = _load()
    if not items:
        return "🎓 _The academy has no enrollments yet — mastery data is still gathering._"
    grads = sum(1 for x in items if x.get("status") == "graduated")
    lines = [f"🎓 *The Academy* — {grads} graduated / {len(items)} enrollments"]
    icon = {"active": "📖", "graduated": "🎓", "rotated": "🔁"}
    for x in items[-5:][::-1]:
        lines.append(f"{icon.get(x['status'], '•')} {x['mentee']} ← {x['mentor']} "
                     f"(enrolled at {x['rate_at_enroll']:.0%}"
                     + (f", gain {x.get('gain', 0):+.0%}" if x.get("gain") is not None
                        and x["status"] != "active" else "") + ")")
    return "\n".join(lines)

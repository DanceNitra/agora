"""
The Academy — the firm trains its own people, and measures whether the training works.

Mastery already records whose findings survive verification; nothing acted on it. The Academy
pairs the weakest verifier (the mentee) with the strongest (the mentor): the mentee's discovery
prompts carry the mentor's discipline — one sharp rule reflecting how the mentor actually works —
until the mentee's verification rate measurably improves (graduation) or doesn't (the lesson
rotates). No vibes: enrollment snapshots the rate, graduation requires +0.10 on >=4 new
attempts. A company whose people measurably improve is the only kind that compounds.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

_STORE = Path(__file__).resolve().parents[2] / ".academy.json"
_MIN_ATTEMPTS = 4          # both to enroll (mentee history) and to graduate (new evidence)
_GRADUATE_GAIN = 0.10

# each mentor teaches the discipline they actually practice — injected into the mentee's prompts
_LESSONS = {
    "Sergeant Voss": "Before claiming, name the weakest assumption — if you can't, don't ship it.",
    "Sage Mira": "State the claim in ONE precise sentence and cite the paper's actual result, not its topic.",
    "Artificer Rooke": "Include the NUMBER the source measured; a claim without a number is a vibe.",
    "Dame Elara": "Say which existing note this connects to — an unconnected claim is probably unread.",
    "High Priest Orin": "Name the mechanism, not the correlation — what would make this true?",
    "King Aldric": "Say what someone could BUILD from this claim; unusable truths rank last.",
    "Shadow Kael": "State what would surprise us if false — no stake, no finding.",
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
    """The mentor's rule to inject into this agent's discovery prompts ('' if not enrolled)."""
    e = active_enrollment()
    if e and e.get("mentee") == agent_name:
        return f"MENTOR'S RULE (from {e['mentor']}): {e['lesson']}"
    return ""


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
           "lesson": _LESSONS.get(mentor_name, "Cite the exact result; name the weakest assumption."),
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

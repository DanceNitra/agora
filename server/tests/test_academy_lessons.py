"""The Academy's per-agent organ lessons — key integrity and prompt safety.

A lesson is looked up by the agent's FULL name (dungeon `_academy_lesson` ->
GET /brain/academy?agent=<full name>). A misspelled key does not raise: it silently returns no
lesson, and the agent keeps churning with nobody the wiser. That is the exact class of bug this
repo keeps finding, so it is asserted here instead of hoped for.

The anti-churn requirement is asserted as CODE too: each lesson must name its organ's NEGATIVE
verdict in that organ's own vocabulary (counted off the live stores 2026-07-31), because a lesson
that only rewards positives produces manufactured positives.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agora.execution import academy
from agora.agent_os.agent_os import NPC_UUIDS
from agora.execution.academy import _LESSONS, _MENTOR_RULES, lesson_for

# The lesson is concatenated into a discovery system prompt; long ones dilute or get truncated.
_MAX_LESSON_CHARS = 320
# With the mentor rule layered on top, the whole injected string still has to stay prompt-sized.
_MAX_INJECTED_CHARS = 460

# The negative verdict each agent must be told counts as a real result, in ITS OWN store's words.
_NEGATIVE_VERDICT = {
    "Shadow Kael": "no_fit",
    "Sage Mira": "reject",
    "High Priest Orin": "no viable mapping",
    "King Aldric": "WRONG",
    "Dame Elara": "compatible",
    "Sergeant Voss": "could not kill",
    "Artificer Rooke": "NOT_COMPUTABLE",
    "Cartographer Wren": "no honest bridge",
}


def test_lessons_cover_every_agent_exactly():
    """No missing agent, no typo'd key — set equality both ways."""
    assert set(_LESSONS) == set(NPC_UUIDS), (
        f"missing={sorted(set(NPC_UUIDS) - set(_LESSONS))} "
        f"unknown={sorted(set(_LESSONS) - set(NPC_UUIDS))}")


def test_mentor_rules_cover_every_agent_exactly():
    """Any agent can become the mentor, so the transferable rules need the same coverage."""
    assert set(_MENTOR_RULES) == set(NPC_UUIDS), (
        f"missing={sorted(set(NPC_UUIDS) - set(_MENTOR_RULES))} "
        f"unknown={sorted(set(_MENTOR_RULES) - set(NPC_UUIDS))}")


def test_lessons_are_prompt_safe():
    """Non-empty, bounded, ASCII (the Windows console here is cp1250)."""
    for name, lesson in _LESSONS.items():
        assert lesson.strip(), f"{name}: empty lesson"
        assert len(lesson) <= _MAX_LESSON_CHARS, f"{name}: {len(lesson)} chars > {_MAX_LESSON_CHARS}"
        assert lesson.isascii(), f"{name}: non-ASCII lesson"


def test_mentor_rules_are_prompt_safe():
    """They land in the same prompt string as the organ lesson, so the same invariants apply."""
    for name, rule in _MENTOR_RULES.items():
        assert rule.strip() and rule.isascii(), f"{name}: empty or non-ASCII mentor rule"


def test_every_lesson_states_the_grounding_requirement():
    """Ungrounded output is dropped at the gate, so every lesson must say what grounding means."""
    for name, lesson in _LESSONS.items():
        assert "MEASURED:" in lesson and "VERDICT:" in lesson, f"{name}: no lab-grounding clause"
        assert "citation" in lesson or "source" in lesson.lower(), f"{name}: no citation clause"


def test_every_lesson_makes_its_negative_verdict_a_result():
    """Anti-churn: an agent told only how to win positively will manufacture positives."""
    for name, token in _NEGATIVE_VERDICT.items():
        assert token in _LESSONS[name], f"{name}: lesson never names its negative verdict ({token!r})"


def test_no_lesson_claims_a_reward_parity_the_scorer_contradicts():
    """metabolism.py pays drafted 2.0 vs 0.5, published 5.0 vs 1.0, bridged 4.0 vs 1.0, kill 3.0 vs
    0.75. A lesson may say a negative verdict is a real RESULT; it must not assert it scores equally."""
    for name, lesson in _LESSONS.items():
        low = lesson.lower()
        assert "scores as high as" not in low and "as good an outcome as" not in low, \
            f"{name}: asserts a reward parity metabolism.py does not pay"


def test_lesson_for_returns_the_agents_own_organ_rule(monkeypatch):
    """The per-agent lever must fire for every agent when NOTHING is enrolled."""
    monkeypatch.setattr(academy, "active_enrollment", lambda: None)
    for name in NPC_UUIDS:
        assert lesson_for(name) == _LESSONS[name]
    assert lesson_for("Nobody At All") == ""


def test_lesson_for_layers_the_mentor_rule_on_the_mentee(monkeypatch):
    """The enrolled mentee gets organ discipline FIRST, mentor rule appended — and stays prompt-sized."""
    monkeypatch.setattr(academy, "active_enrollment",
                        lambda: {"mentee": "Dame Elara", "mentor": "Sergeant Voss",
                                 "lesson": _MENTOR_RULES["Sergeant Voss"], "status": "active"})
    out = lesson_for("Dame Elara")
    assert out.startswith(_LESSONS["Dame Elara"])
    assert "MENTOR'S RULE (from Sergeant Voss)" in out
    assert _MENTOR_RULES["Sergeant Voss"] in out
    assert len(out) <= _MAX_INJECTED_CHARS, f"injected prompt is {len(out)} chars"
    # everyone else is untouched by the enrollment
    assert lesson_for("Shadow Kael") == _LESSONS["Shadow Kael"]


def test_lesson_for_survives_a_record_with_no_lesson_field(monkeypatch):
    """Old/partial store records must degrade to the organ rule, never to 'MENTOR'S RULE: '."""
    monkeypatch.setattr(academy, "active_enrollment",
                        lambda: {"mentee": "Sage Mira", "mentor": "King Aldric", "status": "active"})
    assert lesson_for("Sage Mira") == _LESSONS["Sage Mira"]

"""A non-answer must not become work, and a null result must not be mistaken for one.

Two failures, measured on the live system 2026-07-31.

RECALL. The refusal pattern required a source noun IMMEDIATELY after "no", so a single adjective
defeated it. Of the ten pending inbox tasks carrying a refusal, the guard caught **one**; every miss
read "No REAL sources were provided to support any claim about ...". A guard with 10% recall reports
safe.

REACH. The check lived privately inside `_garbage_finding`, guarding the DISCOVERY door only. The
corp's `_file_ship_review` / `_file_research_dossier` path queues Crucible candidates and research
dossiers straight into Claude's inbox and never asked the question, so a refusal that could never
become a finding still became a task -- 10 of 33 pending tasks, 30% of the queue, several of them
days old.

The line this filter must not cross is between a NON-ANSWER and a NULL RESULT. "No sources were
found" is an unanswered question; "no significant difference was found (p=0.31)" is science, and it
is exactly the kind of honest negative this organization exists to produce. The pattern therefore
anchors on nouns that name a SOURCE and on nothing else.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agora.execution.grounding import is_refusal  # noqa: E402

#: Lifted verbatim from tasks sitting in the live inbox.
REFUSALS = [
    "No real sources were provided to support any claim about SHD in structure learning.",
    "No real sources were provided or found to ground this analysis.",
    "No real sources were provided or found that report a discontinuity at that threshold.",
    "None of the provided sources directly address the specific question of whether restricting "
    "to the top decile reverses the sign.",
    "No sources were provided to support the claim.",
    "No paper directly supports this.",
    "Whether the minimum occurs at an intermediate density cannot be assessed from the available "
    "evidence.",
    "No relevant peer-reviewed studies address this mechanism.",
    "I could not find any literature on this.",
    "The closest are two unrelated abstracts.",
]

#: Real findings and honest nulls. Every one of these must survive.
KEEPERS = [
    "MEASURED: no significant difference between arms, p=0.31 at n=100 (lab a1b2c3).",
    "We found no effect of reinforcement on recall order at n=200; the null is the result.",
    "Supersession retires a RECORD, not a VALUE: the retired value stays reachable (lab 4f21ab).",
    "Recall falls 12% once the store passes 4,000 records (Zheng et al., 2018).",
    "The influence gate blocks rare uncorroborated true memories at a measured rate of 0.19.",
    "No correlation survived the Bonferroni correction, which is itself the finding.",
    "Three sources support this: the postmortem, the runbook and the vendor advisory.",
]


@pytest.mark.parametrize("text", REFUSALS)
def test_a_refusal_is_caught(text):
    assert is_refusal(text), "a non-answer would have become work: %r" % text[:70]


@pytest.mark.parametrize("text", KEEPERS)
def test_a_null_result_is_not_a_refusal(text):
    assert not is_refusal(text), "an honest negative was filtered as a non-answer: %r" % text[:70]


def test_recall_beats_the_pattern_it_replaces():
    """The control. Without it, this suite passes whether or not the fix improved anything.

    Runs the OLD private pattern over the same corpus and asserts it does markedly worse -- if it
    ever stops doing worse, the fixture has lost the cases that motivated the change.
    """
    import re
    old = re.compile(
        r"\bno (?:paper|papers|source|sources|study|studies|abstract|abstracts|evidence)\b[^.\n]{0,40}"
        r"\b(?:support|provide|relate|address|mention|match|fit|confirm)\w*"
        r"|\bdoes not (?:support|fit|apply)|\b(?:are|is) unrelated|\bcould not find"
        r"|\bunable to (?:find|locate)|\bthe closest (?:are|is)\b", re.I)
    old_hits = sum(1 for t in REFUSALS if old.search(t))
    new_hits = sum(1 for t in REFUSALS if is_refusal(t))
    assert new_hits == len(REFUSALS), "%d/%d caught" % (new_hits, len(REFUSALS))
    assert old_hits < new_hits, ("the old pattern already caught %d/%d, so this fixture no longer "
                                 "reproduces the recall hole" % (old_hits, len(REFUSALS)))


def test_empty_input_is_not_a_refusal():
    assert not is_refusal("")
    assert not is_refusal(None)


def test_both_doors_ask_the_same_question():
    """Pins the reach half: the discovery door and the corp->inbox path must share one definition."""
    api = (Path(__file__).resolve().parents[1] / "agora" / "api" / "agent_os_api.py"
           ).read_text(encoding="utf-8", errors="replace")
    worker = (Path(__file__).resolve().parents[1] / "agora" / "dungeon_os" / "agent_worker.py"
              ).read_text(encoding="utf-8", errors="replace")
    assert "is_refusal" in api, "the discovery door no longer uses the shared refusal test"
    assert "is_refusal" in worker, "the corp -> Claude inbox path does not check for refusals"

"""The length gate must measure the note, not the first line before the word "source".

`_garbage_finding` strips a trailing citation block before checking that a finding has substance.
It did that with a flat `content.split("source:")[0]`, which also cuts at an INLINE parenthetical --
and declaring provenance in the opening line is exactly what a scout verdict does.

Measured 2026-07-31 on the live swarm: Shadow Kael's organ returned `ok DECISIVE` with a lab id,
composing a twelve-line verdict (VERDICT, MEASURED, lab, BOARD match, VAULT citations, REACHABILITY
audit, WHY, NEXT). Its first line reads

    SCOUT FIT - fmind-ai/fgentic#333 (source: github-scan)

so the flat split measured the whole note at 34 characters and the door refused it as "too short".
The rejection ledger recorded it; nothing else did. His organ had been doing real work and being
turned away at the threshold.

The fix anchors the split to the start of a line, which is what a trailing citation block looks like
and what an inline parenthetical never does.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agora.api.agent_os_api import _garbage_finding  # noqa: E402

#: Shortened but structurally faithful to what organs/thief.py:_compose emits.
SCOUT_NOTE = (
    "SCOUT FIT - fmind-ai/fgentic#333 (source: github-scan)\n"
    "lead: https://github.com/fmind-ai/fgentic/issues/333\n"
    "VERDICT: FIT\n"
    "MEASURED: on-board on ['agent', 'memory', 'retrieval'], reachable, and answerable from 1 "
    "on-board vault note\n"
    "lab 4ae810  (re-runnable artifact: the frozen inputs and the gate source)\n"
    "BOARD: matched ['agent', 'memory', 'retrieval'] against the owner's standing priorities\n"
    "VAULT: 1 answerable note of 4 hits - \"Supersession retires a record\" (04 Resources/x.md, 0.71)\n"
    "REACHABILITY: 12 comments, 3 from OWNER/MEMBER, repo 1420 stars / 96 forks, thread 9d old\n"
    "WHY: external demand lands on a thin spot in our own vault\n"
)


def test_a_note_declaring_its_source_in_the_first_line_is_not_too_short():
    assert _garbage_finding("Scout fit: fmind-ai/fgentic#333", SCOUT_NOTE) is None


def test_the_old_flat_split_would_have_refused_it():
    """The control. Without it, this suite passes whether or not the fixture reproduces the bug."""
    flat_body = SCOUT_NOTE.lower().split("source:")[0].strip()
    assert len(flat_body) < 50, (
        "the fixture no longer reproduces the defect (flat body is %d chars), so the test above "
        "proves nothing" % len(flat_body))


def test_a_trailing_source_block_is_still_cut():
    """The behaviour the split exists for must survive: a stub plus citations is still too short."""
    stub = "A short claim.\nsource: " + "https://example.com/a-very-long-citation-url " * 6
    assert _garbage_finding("A short claim", stub) == "too short"


def test_a_trailing_sources_block_is_cut_too():
    stub = "A short claim.\nSources:\n - https://example.com/one\n - https://example.com/two\n"
    assert _garbage_finding("A short claim", stub) == "too short"


def test_a_genuinely_empty_note_is_still_refused():
    assert _garbage_finding("Anything", "tiny") == "too short"


def test_substance_before_a_trailing_block_still_passes():
    note = ("The gate refuses a rare uncorroborated memory at a measured rate, so recall is being "
            "traded for integrity and we should say which way.\nsource: lab 9f21ac\n")
    assert _garbage_finding("Influence gate trades recall for integrity", note) is None

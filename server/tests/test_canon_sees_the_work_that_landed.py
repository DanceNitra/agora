"""The Canon's intake must be able to see the day's work, and must not mistake a date for a source.

Three defects, all measured on the live vault 2026-08-01, all in the path between "an agent produced
an artifact" and "the curator can consider it".

1. A SAME-DAY DEAD ZONE. `_canon_updated_ts` returned 23:59 of the Canon's `updated:` date while an
   artifact's `created:` line is stamped at 12:00 of its own date. So `ts > cutoff` was False for
   every artifact produced on the day the Canon was merged -- and stayed False forever, because both
   sides are frozen to fixed times of day rather than to when anything happened. Not "not yet
   eligible": permanently invisible, and aimed precisely at the artifacts whose arrival triggered the
   merge. Live casualty: `insight-grounding-breaks-the-wall-aggregation-cannot.md`, created
   2026-07-31, excluded by a Canon updated 2026-07-31, while Sage Mira reported an honest
   "nothing new landed".

2. A ONE-SPELLING CORE EXTRACTOR. The core was pulled from `## The insight|Hypothesis|Answer` and
   nowhere else, so a note headed `## The finding` -- our own Theory Engine's wording -- yielded an
   EMPTY core and was then graded on its bare title. Same failure the falsifier detector already made
   one file over ("falsifier" is not a substring of "falsification").

3. A CITATION DETECTOR THAT ACCEPTED A MONTH. `(January 2026)` matched the shared parenthetical
   author-year pattern, so any claim mentioning a month and a year read as externally cited. That one
   is in `grounding.py`, which every caller in the repo shares -- the quality gate, the promotion
   pipeline, this scan -- so the blast radius was the whole notion of "is this cited".

The receipt scan added here deliberately does NOT re-derive author-year matching. A private copy
repeated the known mirror-image bug within minutes of being written: it missed `Watts (2002)` and
accepted `(January 2026)`. Author-year matching is not a thing to write twice.
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "server"))

from agora.execution import canon as C  # noqa: E402
from agora.execution.grounding import citation, is_cited  # noqa: E402


# ---------------------------------------------------------------- 1. the same-day dead zone

def _canon(tmp_path: Path, updated: str) -> Path:
    root = tmp_path / "04 Resources" / "Concepts" / "Agora Agents"
    root.mkdir(parents=True)
    (root / "Canon.md").write_text("---\nupdated: %s\n---\n# Canon\n- a belief\n" % updated,
                                   encoding="utf-8")
    return root


def test_the_cutoff_is_the_start_of_the_day_not_the_end(monkeypatch, tmp_path):
    monkeypatch.setattr(C, "read_canon", lambda v: "---\nupdated: 2026-07-31\n---\n")
    ts = C._canon_updated_ts(str(tmp_path))
    assert time.localtime(ts).tm_hour == 0, (
        "cutoff is at %02d:00; an artifact stamped 12:00 on the same date is excluded forever"
        % time.localtime(ts).tm_hour)


def test_an_artifact_created_the_day_the_canon_moved_is_still_visible(monkeypatch, tmp_path):
    root = _canon(tmp_path, "2026-07-31")
    (root / "insight-same-day.md").write_text(
        "---\ncreated: 2026-07-31\ntitle: Same day insight\n---\n"
        "## The finding\nGrounding beats aggregation by 20pp. lab 4b4fbf\n", encoding="utf-8")
    monkeypatch.setattr(C, "read_canon", lambda v: "---\nupdated: 2026-07-31\n---\n")
    got = C.new_artifacts_since_canon(str(tmp_path))
    assert [a["title"] for a in got] == ["Same day insight"], (
        "the artifact that landed on the merge day is invisible to the curator: %s" % got)


def test_an_artifact_from_before_the_canon_moved_is_not_reoffered(monkeypatch, tmp_path):
    """The guard against over-correcting. Widening the window must not re-open everything already
    considered, or the curator re-litigates the whole vault every cycle."""
    root = _canon(tmp_path, "2026-07-31")
    (root / "insight-old.md").write_text(
        "---\ncreated: 2026-07-01\ntitle: Old insight\n---\n## The finding\nsomething. lab aaaaaa\n",
        encoding="utf-8")
    monkeypatch.setattr(C, "read_canon", lambda v: "---\nupdated: 2026-07-31\n---\n")
    assert C.new_artifacts_since_canon(str(tmp_path)) == []


# ---------------------------------------------------------------- 2. the core extractor

@pytest.mark.parametrize("heading", [
    "## The insight", "## The finding", "## The result", "## Answer", "## Hypothesis",
    "## The claim", "## Conclusion", "### The thesis",
])
def test_the_core_is_read_under_every_heading_our_agents_write(heading):
    core = C._core_of("---\ntitle: x\n---\n%s\nThe substance of the note lives here.\n" % heading)
    assert "substance" in core, "heading %r yielded an empty core" % heading


def test_a_note_with_no_recognised_heading_still_yields_its_substance():
    """No recognised heading is not the same as no content; handing the grader a bare title is how a
    real note gets graded as empty."""
    core = C._core_of("---\ntitle: x\n---\n\nA paragraph of real substance that runs well past the "
                      "eighty character floor and says something concrete.\n")
    assert "real substance" in core


# ---------------------------------------------------------------- 3. receipts vs decoys

RECEIPTS = [
    ("lab id", "We ran it. lab 4b4fbf reproduced the effect."),
    ("MEASURED", "Results:\nMEASURED: tipping_fraction = 0.0528\n"),
    ("VERDICT", "VERDICT: NOT_COMPUTABLE -- system size unstated"),
    ("author outside", "This follows Watts (2002) on cascade windows."),
    ("author inside", "Low-water-mark integrity (Biba, 1975) applies."),
    ("et al.", "As shown in (Breznau et al., 2022) the effect varies."),
    ("doi", "See doi: 10.1145/2500127 for the full result."),
    ("arxiv", "Reported in arXiv:2605.14421 for agent memory."),
]

DECOYS = [
    ("prose about measuring", "a fully-measured thesis with verdict-like confidence"),
    ("month-year", "we started this in (January 2026) and kept going"),
    ("quarter-year", "the plan slipped to (Q3 2025) before anyone noticed"),
    ("season-year", "shipped in (Winter 2024) after a long delay"),
    ("version-year", "tagged as (Version 2024) in the release notes"),
]


@pytest.mark.parametrize("label,text", RECEIPTS, ids=[r[0] for r in RECEIPTS])
def test_a_real_receipt_is_found(label, text):
    assert C._receipt_line(text), "%s went undetected, so a grounded note reads as ungrounded" % label


@pytest.mark.parametrize("label,text", DECOYS, ids=[d[0] for d in DECOYS])
def test_a_decoy_is_not_a_receipt(label, text):
    assert not C._receipt_line(text), (
        "%s was accepted as a receipt -- the gate becomes decoration while still reporting it ran"
        % label)


@pytest.mark.parametrize("label,text", DECOYS[1:], ids=[d[0] for d in DECOYS[1:]])
def test_the_shared_citation_detector_rejects_dates(label, text):
    """Fixed in grounding.py, not locally: every caller in the repo inherits this one."""
    assert not is_cited(text), "%s reads as an external citation repo-wide: %r" % (label, citation(text))


def test_a_date_early_in_the_text_does_not_hide_a_real_citation_later():
    """The over-correction guard: skipping a date must scan ON, not abandon the search."""
    t = "we noted (January 2026) and later Watts (2002) confirmed it"
    assert citation(t) == "Watts (2002)", "got %r" % citation(t)


def test_the_live_artifact_is_not_credited_with_a_receipt_it_lacks():
    """THE CONTROL, on real data. `insight-grounding-breaks-the-wall...` has 6,810 chars of real
    research and genuinely no Lab id, no MEASURED:/VERDICT: and no citation. If the scan ever starts
    crediting it, the detector has gone loose and every assertion above is worth less."""
    p = next(iter(Path("C:/Users/Danculus/my-second-brain/04 Resources/Concepts/Agora Agents")
                  .rglob("insight-grounding-breaks-the-wall*.md")), None)
    if p is None:
        pytest.skip("the reference artifact is not on this machine")
    text = p.read_text(encoding="utf-8", errors="replace")
    assert not re.search(r"\blab\s+[0-9a-f]{6}\b", text), "the fixture note changed; re-pick one"
    assert not C._receipt_line(text), (
        "a note with no Lab id, no MEASURED: line and no citation was credited with a receipt")

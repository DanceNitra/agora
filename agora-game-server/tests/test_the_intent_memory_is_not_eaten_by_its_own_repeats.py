"""The anti-repetition memory was consumed by the repetition it exists to prevent.

Measured 2026-08-08 on the live `.recent_intents.json`: all EIGHT agents held **50 entries carrying
5-7 DISTINCT intents** -- roughly eight copies apiece. `_seen.append()` spent a slot per pick, so a
50-entry recency window actually remembered ~6 topics, and every agent was permanently saturated.

Saturated, `fresh` came back empty and `chosen = (fresh or interleaved)` re-served the same picks.
The 2026-07-31 note in `mcp_server.py` had already named that exact inversion -- "a dedup that
produces duplicates precisely when it is working hardest" -- and fixed only the per-agent half of it.

What it cost, measured over 17.9 h: **400 refusals (22.4/h) carrying 28 distinct titles**, a 14.3x
resubmission factor, one title submitted **53 times by all eight agents**, every one correctly
refused by the brain as a near-duplicate. The dedup gate was right; the producer was looping.

Two fixes, tested here:
  (a) a repeat MOVES an entry instead of adding one, and the saturated file heals ON LOAD;
  (b) no `or interleaved` fallback -- exhausted means no research this cycle.

And the trap (b) creates, which is why the third test exists: an agent that legitimately plans
nothing must NOT be counted as a plan failure, or `_plan_fails` escalates "the brain may be down" to
the owner three cycles later -- the same false alarm the `off_priority` branch was built to prevent,
re-created by the fix for something else.

mcp_server is NOT imported: it is `__main__` and importing it starts a second server. The helper is
exec'd from source so these assertions run the REAL function, not a restatement of it.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
SRC = (HERE / "mcp_server.py").read_text(encoding="utf-8", errors="replace")

#: Source with comment-only lines removed. A plain substring check cannot tell CODE from a comment
#: ABOUT that code -- the first version of `test_the_fallback...` below failed on the very comment
#: that documents the removal, which would have read as "the bug is back".
CODE = "\n".join(l for l in SRC.split("\n") if not l.lstrip().startswith("#"))


def _load_helper():
    """exec ONLY the helper's definition, so the test exercises shipped code without a server."""
    i = SRC.index("def _dedup_keep_last(")
    j = SRC.index("\ndef _load_recent_intents(", i)
    ns: dict = {}
    exec(SRC[i:j], ns)          # noqa: S102 -- deliberate: run the real definition, not a copy
    return ns["_dedup_keep_last"]


def test_the_anchors_exist():
    """THE CONTROL. Every assertion below reads source text; if these move, they stop examining
    anything and would report a pass on code that no longer exists."""
    assert "def _dedup_keep_last(" in SRC
    assert "def _load_recent_intents(" in SRC
    assert "_seen = _recent_intents.setdefault(eid, [])" in SRC


def test_a_repeat_moves_an_entry_it_does_not_spend_a_slot():
    dedup = _load_helper()
    assert dedup(["a", "b", "a", "c", "a"]) == ["b", "c", "a"], "must keep the MOST RECENT position"
    assert dedup([]) == []
    assert dedup(["x"] * 9) == ["x"], "nine copies of one intent must occupy ONE slot, not nine"


def test_the_live_saturation_shape_heals():
    """The measured state: 50 entries, 6 distinct. After the fix that is 6 entries, 6 distinct --
    leaving 44 slots of real history instead of 0."""
    dedup = _load_helper()
    saturated = (["i1", "i2", "i3", "i4", "i5", "i6"] * 9)[:50]
    assert len(saturated) == 50 and len(set(saturated)) == 6      # the fixture IS the defect
    healed = dedup(saturated)
    assert len(healed) == 6 and set(healed) == set(saturated)


def test_the_fallback_that_produced_duplicates_is_gone():
    assert "(fresh or interleaved)" not in CODE, (
        "the `or interleaved` fallback is back: once `fresh` is empty it re-serves exactly the "
        "intents the memory is holding, which is what produced 14.3x resubmission")
    assert "chosen = fresh[:want]" in CODE
    # and the comment explaining WHY must survive, so the next reader does not restore it
    assert "(fresh or interleaved)" in SRC, "the rationale comment was deleted with the code"


def test_load_and_save_both_dedup():
    """Both directions, because healing only on save would leave the poisoned file poisoned until
    something happened to write it, and healing only on load would re-poison it every cycle."""
    i = SRC.index("def _load_recent_intents(")
    j = SRC.index("\n_recent_intents: dict =", i)
    assert "_dedup_keep_last" in SRC[i:j], "load path does not dedup"
    k = SRC.index("def _save_recent_intents(")
    assert "_dedup_keep_last" in SRC[k:k + 500], "save path does not dedup"


def test_exhaustion_is_not_reported_as_a_broken_brain():
    """The trap the no-fallback fix creates. `exhausted` must reach the same non-blocker branch as
    `off_priority`, or three quiet cycles escalate 'the brain may be down' to the owner."""
    assert '_plan_reason[eid] = "exhausted"' in SRC
    assert '_plan_reason.get(eid) in ("off_priority", "exhausted")' in SRC, (
        "an exhausted agent falls through to the escalation branch and will alarm the owner")


def _load_stripper():
    """The real `_strip_quest_prefix` plus the two regexes and the roster it is built from."""
    ns: dict = {"re": __import__("re")}
    i = SRC.index("_AGENT_NAMES = {")
    exec(SRC[i:SRC.index("\n\n", SRC.index("}", i))], ns)          # noqa: S102
    i = SRC.index("_QUEST_PREFIX_RE = re.compile")
    exec(SRC[i:SRC.index("def _strip_quest_prefix", i)], ns)       # noqa: S102
    i = SRC.index("def _strip_quest_prefix")
    exec(SRC[i:SRC.index("\n\n#: Why an agent ended", i)], ns)     # noqa: S102
    return ns["_strip_quest_prefix"]


def test_the_author_pair_prefix_is_not_part_of_the_subject():
    """One subject reached the pool once per author pair that had touched it. Measured on the live
    top-8: 8 rows, 7 distinct strings, TWO real subjects."""
    strip = _load_stripper()
    # the AUTHOR pair goes; "MemOps:" is the SUBJECT and must survive -- a peeler that took it too
    # would merge unrelated findings into one topic, which is the opposite failure
    assert strip("King Aldric + Sage Mira: MemOps: Benchmarking") == "MemOps: Benchmarking"
    assert strip("Cartographer Wren + Artificer Rooke: MemOps: X") == "MemOps: X"
    assert strip("Pipeline: QVal: Cheaply Evaluating") == "QVal: Cheaply Evaluating"


def test_the_stripper_does_not_eat_ordinary_prose():
    """THE CONTROL that matters for a prefix-peeler: it must key on the ROSTER, not on 'any words
    then a colon', or it silently truncates real subjects."""
    strip = _load_stripper()
    for kept in ("Poison resistance under echo attack",
                 "King Aldric walked into the hall: a story",
                 "Supersession: what a correction retires"):
        assert strip(kept) == kept, "the stripper ate %r" % kept


def test_findings_are_sampled_by_topic_not_by_row():
    assert "_topics: dict[str, str] = {}" in CODE
    assert "random.sample(list(_topics.values())" in CODE, (
        "sampling rows again: the top-8 is an author-pair cross-product of a couple of subjects, so "
        "row-sampling returns copies of one topic and calls them separate quests")
    assert "topic.lower()[:40]" in CODE, (
        "exact-string keying cannot merge titles stored ALREADY TRUNCATED, where a longer author "
        "prefix leaves a shorter remainder of the same subject")


def test_the_live_intents_file_if_present_is_not_still_saturated():
    """Real data. Skips rather than passing vacuously when the file is absent."""
    p = HERE / ".recent_intents.json"
    if not p.exists():
        pytest.skip("no live intents file")
    import json
    d = json.loads(p.read_text(encoding="utf-8"))
    if not d:
        pytest.skip("intents file empty")
    bad = {k: (len(v), len(set(v))) for k, v in d.items()
           if isinstance(v, list) and len(v) >= 50 and len(set(v)) < 12}
    assert not bad, ("still saturated (entries, distinct): %s -- the running dungeon predates the "
                     "fix, or the dedup is not reaching disk" % bad)

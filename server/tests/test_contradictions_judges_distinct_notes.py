"""The coherence sweep must spend its calls on notes that could actually disagree.

Measured on the live vault 2026-07-31, before these guards existed:

  * 96 judgements in 24h, of which **59 had `a == b`** -- a note against its own copy re-filed
    under a later date. The vault holds 4,200 files (38%) sharing a title with a sibling, and a
    copy is a near-perfect neighbour, so the top-2 shortlist filled with them.
  * 26 of the 96 were the SAME title pair judged again inside one sweep, because the seen-set was
    read once before the loop and never updated. One pair was judged five times.
  * Of the 120 highest-similarity candidates that survived a title filter, **62% were still copies**
    (39 byte-identical or contained) under an operational prefix -- `backup_`, `pwback_`, `orphan_`,
    `r2_`, `bridge1_` -- worn by 754 files.

Every one of those spent an LLM call to ask whether a document contradicts itself, could not return
CONTRADICT, and banked the guaranteed COMPATIBLE as a decisive coherence verdict. That is what made
this organ read as the busiest in the keep.

These tests hand each guard an input it cannot inspect its way out of.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agora.execution import contradictions as C  # noqa: E402


# --------------------------------------------------------------------------------------------
# the body-level duplicate test, in isolation
# --------------------------------------------------------------------------------------------

def test_identical_and_contained_bodies_are_duplicates():
    assert C._is_duplicate_body("the sky is blue", "the sky is blue")
    assert C._is_duplicate_body("the sky is blue", "the sky is blue and the sea is grey")


def test_a_leading_token_is_not_enough_to_merge_two_notes():
    """The guard this test exists for.

    Stripping a `<prefix>_` by pattern would have been the cheap fix for `backup_X` vs `pwback_X`,
    and it silently merges two REAL notes that differ only by a leading word. The content test must
    keep them apart -- it is the whole reason the check reads bodies instead of filenames.
    """
    a = "decorators wrap a callable in python using the at syntax and functools wraps"
    b = "decorators wrap a callable in rust using attribute macros and the proc macro crate"
    assert not C._is_duplicate_body(a, b)


def test_a_rewritten_note_is_not_a_duplicate():
    a = "memory decay follows a power law over the first week of retention"
    b = "retention collapses exponentially within hours and never recovers afterwards"
    assert not C._is_duplicate_body(a, b)


def test_empty_body_is_never_called_a_duplicate():
    """`"" in anything` is True, so a note the reader failed to load would swallow its partner."""
    assert not C._is_duplicate_body("", "the sky is blue")
    assert not C._is_duplicate_body("the sky is blue", "")


# --------------------------------------------------------------------------------------------
# the same-note (title / basename) test, in isolation
# --------------------------------------------------------------------------------------------

def test_a_redated_copy_is_the_same_note():
    a = {"title": "Phase Transition", "path": "Agents/2026-07-06/phase-transition.md"}
    b = {"title": "Phase Transition", "path": "Agents/2026-07-20/phase-transition.md"}
    assert C._same_note(a, b)


def test_two_different_notes_are_not_the_same_note():
    a = {"title": "Phase Transition", "path": "Agents/2026-07-06/phase-transition.md"}
    b = {"title": "Critical Slowing Down", "path": "Agents/2026-07-06/critical-slowing.md"}
    assert not C._same_note(a, b)


def test_two_untitled_notes_are_not_collapsed_into_one():
    """Both titles missing must not read as 'equal'. The sentinels differ for exactly this input."""
    a = {"path": "Agents/a.md"}
    b = {"path": "Agents/b.md"}
    assert not C._same_note(a, b)


# --------------------------------------------------------------------------------------------
# the sweep end to end, on a fixture index
# --------------------------------------------------------------------------------------------

def _pair_vectors(n_pairs: int, cos: float = 0.95) -> np.ndarray:
    """Block-diagonal unit vectors: partners sit at `cos`, everything across blocks at 0."""
    half = np.arccos(cos) / 2.0
    v = np.zeros((n_pairs * 2, n_pairs * 2))
    for p in range(n_pairs):
        v[2 * p, 2 * p], v[2 * p, 2 * p + 1] = np.cos(half), np.sin(half)
        v[2 * p + 1, 2 * p], v[2 * p + 1, 2 * p + 1] = np.cos(half), -np.sin(half)
    return v


@pytest.fixture()
def swept(tmp_path, monkeypatch):
    """Four candidate pairs, one of each kind the sweep must handle."""
    vault = tmp_path / "vault"
    (vault / "d").mkdir(parents=True)

    notes = [
        # pair 0 -- the SAME note re-filed under a later date, and EDITED so its bodies differ.
        # Only the title/basename guard can catch it; if that guard goes, this pair is judged.
        ("Phase Transition", "d/2026-07-06_phase.md", "the transition is sharp at rho 0.5"),
        ("Phase Transition", "d/2026-07-20_phase.md", "we mapped the boundary across many rho values"),
        # pair 1 -- one note under two operational prefixes. Titles differ; bodies are identical.
        # Only the CONTENT guard can catch it.
        ("backup_Default Mode Network", "d/backup_dmn.md", "the network idles between tasks"),
        ("pwback_Default Mode Network", "d/pwback_dmn.md", "the network idles between tasks"),
        # pair 2 -- a real disagreement. This is the one call the sweep should spend.
        ("Gamma", "d/g1.md", "recall improves monotonically as the store grows larger"),
        ("Delta", "d/d1.md", "recall degrades once the store passes a few thousand records"),
        # pair 3 -- DIFFERENT files, but the same TITLE PAIR as pair 2. Only the in-loop seen-set
        # update can catch it; without that, one sweep judges the same pair twice.
        ("Gamma", "d/g2.md", "a bigger store retrieves strictly better in every regime we tried"),
        ("Delta", "d/d2.md", "beyond a few thousand records retrieval quality falls off steeply"),
    ]
    for _, rel, body in notes:
        (vault / rel).write_text("---\nx: 1\n---\n" + body, encoding="utf-8")

    meta = [{"title": t, "path": p} for t, p, _ in notes]

    class _Index:
        ready = True
        vecs = _pair_vectors(len(notes) // 2)
        def __init__(self): self.meta = meta
        def _is_knowledge(self, m): return True

    import agora.execution.semantic_index as si_mod
    monkeypatch.setattr(si_mod, "SemanticIndex", _Index)
    monkeypatch.setattr(C, "_STORE", tmp_path / "contradictions.json")

    calls: list[tuple] = []

    def _judge(a_title, a_snip, b_title, b_snip):
        calls.append((a_title, b_title))
        return {"claim": "does a larger store help or hurt recall"}

    monkeypatch.setattr(C, "_judge_pair", _judge)

    out = asyncio.run(C.sweep(str(vault), max_judged=8))
    records = json.loads((tmp_path / "contradictions.json").read_text(encoding="utf-8"))
    return out, records, calls


def test_only_the_genuine_disagreement_costs_a_call(swept):
    out, _, calls = swept
    assert out["judged"] == 1, "budget went to something other than the one real pair: %s" % (calls,)
    assert len(calls) == 1
    assert sorted(calls[0]) == ["Delta", "Gamma"]


def test_the_prefixed_copy_is_skipped_without_being_recorded(swept):
    """A duplicate is a fact about filing, not a coherence verdict. It must not enter the ledger."""
    out, records, _ = swept
    assert out["dup_skipped"] == 1
    assert not any("Default Mode Network" in (r["a"] + r["b"]) for r in records)


def test_the_redated_copy_never_reaches_the_reader(swept):
    """Filtered at candidate selection, so it costs neither a call nor a file read."""
    out, records, _ = swept
    assert not any(r["a"] == r["b"] for r in records), "a note was judged against itself"
    assert not any("Phase Transition" in (r["a"] + r["b"]) for r in records)
    assert out["scanned"] == 2, "expected to open only the dup pair and the real pair"


def test_one_title_pair_is_judged_once_per_sweep(swept):
    _, records, calls = swept
    seen = [tuple(sorted((r["a"], r["b"]))) for r in records]
    assert len(seen) == len(set(seen)), "the same title pair was recorded twice in one sweep"
    assert len(calls) == 1


def test_the_record_names_the_two_files_it_judged(swept):
    """Titles alone are not a receipt -- one title in this vault points at up to ten files."""
    _, records, _ = swept
    assert len(records) == 1
    r = records[0]
    assert r["path_a"] and r["path_b"], "verdict cannot be traced back to the documents"
    assert r["path_a"] != r["path_b"]
    assert r["by"] == C.OWNER

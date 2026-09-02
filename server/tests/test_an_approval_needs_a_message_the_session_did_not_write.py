# -*- coding: utf-8 -*-
"""tools/owner_spoke.py: the send path may not treat its own output as consent.

WHY THIS FILE EXISTS. `send_approved.py` binds outbound bytes to a digest, but that digest is
computed, printed and passed back by the same session. An adversarial pass measured what the first
version of this guard was actually worth, and the answer was nothing:

  * The machine/human split was a list of text PREFIXES. Across 20 transcripts and 24,679
    `role: user` records, 229 machine-authored records passed it. Ninety-four of them read
    `Base directory for this skill: ...`, which the harness injects whenever the assistant calls the
    Skill tool, so ONE Skill call satisfied the guard. The harness marks `origin.kind` on every
    record; keyed on that field the same corpus admits all 1,571 humans and rejects all 229 leaks.
  * The anchor was a JSON file this session writes. Backdating one line satisfied the check for
    every hash at once.

So the rules under test are: the anchor comes from the harness's record of `show` printing the hash,
the human test reads `origin.kind`, and neither is a string the session can choose.

Every case below is a FIXTURE transcript, because the point is the cases the live one does not
contain: a machine message after the anchor and nothing else, two drafts in flight, an unparseable
timestamp, a reply that arrives before the hash was shown.
"""
from __future__ import annotations

import io
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import owner_spoke as ow  # noqa: E402

SHA_A = "a" * 64
SHA_B = "b" * 64


def _show(ts, sha):
    return {"timestamp": ts, "toolUseResult": {"stdout": "sha256 : %s\nbytes  : 10\n" % sha}}


def _msg(ts, text, kind):
    return {"timestamp": ts, "origin": {"kind": kind},
            "message": {"role": "user", "content": text}}


def _tree(tmp_path, entries, name="s.jsonl"):
    d = tmp_path / "proj"
    d.mkdir(exist_ok=True)
    with io.open(str(d / name), "w", encoding="utf-8") as fh:
        for e in entries:
            fh.write(json.dumps(e) + "\n")
    return str(d)


def test_a_human_reply_after_the_hash_is_what_lets_it_through(tmp_path):
    d = _tree(tmp_path, [_show("2026-09-02T10:00:00.000Z", SHA_A),
                         _msg("2026-09-02T10:05:00.000Z", "posli", "human")])
    ok, why = ow.check(SHA_A, project_dir=d)
    assert ok, why


def test_a_skill_invocation_is_not_the_owner_speaking(tmp_path):
    """The exact record that defeated version one: 94 of them in this project's transcripts."""
    d = _tree(tmp_path, [
        _show("2026-09-02T10:00:00.000Z", SHA_A),
        _msg("2026-09-02T10:05:00.000Z",
             "Base directory for this skill: C:\\Users\\x\\.claude\\skills\\humanizer", None),
    ])
    ok, why = ow.check(SHA_A, project_dir=d)
    assert not ok, why


def test_a_task_notification_is_not_consent(tmp_path):
    d = _tree(tmp_path, [_show("2026-09-02T10:00:00.000Z", SHA_A),
                         _msg("2026-09-02T10:05:00.000Z", "<task-notification> done",
                              "task-notification")])
    assert not ow.check(SHA_A, project_dir=d)[0]


def test_a_reply_that_arrived_before_the_hash_was_shown_does_not_count(tmp_path):
    d = _tree(tmp_path, [_msg("2026-09-02T09:00:00.000Z", "posli", "human"),
                         _show("2026-09-02T10:00:00.000Z", SHA_A)])
    ok, why = ow.check(SHA_A, project_dir=d)
    assert not ok and "no human message since" in why


def test_a_hash_that_was_never_shown_cannot_have_been_approved(tmp_path):
    d = _tree(tmp_path, [_show("2026-09-02T10:00:00.000Z", SHA_A),
                         _msg("2026-09-02T10:05:00.000Z", "posli", "human")])
    assert not ow.check(SHA_B, project_dir=d)[0]


def test_two_drafts_in_flight_cannot_share_one_reply(tmp_path):
    """One 'ok' after two shows is not an answer about either, and the guard must say which."""
    d = _tree(tmp_path, [_show("2026-09-02T10:00:00.000Z", SHA_A),
                         _show("2026-09-02T10:01:00.000Z", SHA_B),
                         _msg("2026-09-02T10:05:00.000Z", "ok", "human")])
    ok, why = ow.check(SHA_A, project_dir=d)
    assert not ok and "another draft" in why
    # The one shown SECOND is unambiguous: nothing was shown between it and the reply.
    assert ow.check(SHA_B, project_dir=d)[0]


def test_a_local_offset_reply_is_compared_as_a_time_not_as_a_string(tmp_path):
    """`13:00+02:00` is 11:00Z, an hour BEFORE the anchor, and sorts AFTER it as text."""
    d = _tree(tmp_path, [_show("2026-09-02T12:00:00.000Z", SHA_A),
                         _msg("2026-09-02T13:00:00.000+02:00", "posli", "human")])
    assert not ow.check(SHA_A, project_dir=d)[0]


def test_an_unparseable_timestamp_is_dropped_rather_than_trusted(tmp_path):
    d = _tree(tmp_path, [_show("2026-09-02T10:00:00.000Z", SHA_A),
                         _msg("not-a-timestamp", "posli", "human")])
    assert not ow.check(SHA_A, project_dir=d)[0]


def test_a_human_message_in_a_different_session_is_not_an_answer(tmp_path):
    """The show happened in one transcript; the reply must be in that one."""
    d = _tree(tmp_path, [_show("2026-09-02T10:00:00.000Z", SHA_A)], name="a.jsonl")
    _tree(tmp_path, [_msg("2026-09-02T10:05:00.000Z", "posli", "human")], name="b.jsonl")
    assert not ow.check(SHA_A, project_dir=d)[0]


def test_no_transcripts_at_all_fails_closed(tmp_path):
    d = tmp_path / "empty"
    d.mkdir()
    ok, why = ow.check(SHA_A, project_dir=str(d))
    assert not ok and "no session transcript" in why


def _asst(ts, text):
    return {"timestamp": ts, "message": {"role": "assistant",
                                         "content": [{"type": "text", "text": text}]}}


DRAFT = ("The reminder fires when the largest fraction reaches 0.8 and targets 0.7 of the cap.\n"
         "Six of the eight prompts are false-identity pretexts, which is the part that matters.\n")


def test_showing_the_hash_without_the_text_is_not_an_approval(tmp_path):
    """A hash goes to a tool result nobody reads aloud. The draft is what he answers about."""
    f = tmp_path / "d.md"
    f.write_text(DRAFT, encoding="utf-8")
    d = _tree(tmp_path, [_show("2026-09-02T10:00:00.000Z", SHA_A),
                         _msg("2026-09-02T10:05:00.000Z", "posli", "human")])
    ok, why = ow.check(SHA_A, project_dir=d, draft=str(f))
    assert not ok and "never put in front of him" in why


def test_the_text_displayed_before_the_reply_is_what_lets_it_through(tmp_path):
    f = tmp_path / "d.md"
    f.write_text(DRAFT, encoding="utf-8")
    d = _tree(tmp_path, [_show("2026-09-02T10:00:00.000Z", SHA_A),
                         _asst("2026-09-02T10:01:00.000Z", "Here it is:\n\n" + DRAFT),
                         _msg("2026-09-02T10:05:00.000Z", "posli", "human")])
    ok, why = ow.check(SHA_A, project_dir=d, draft=str(f))
    assert ok, why


def test_a_sentence_added_after_the_display_fails(tmp_path):
    """The case measured on a real send: a line appended after the last full paste, approved on a
    hash that covered it, and never displayed."""
    f = tmp_path / "d.md"
    f.write_text(DRAFT + "And a sentence appended afterwards that nobody was ever shown at all.\n",
                 encoding="utf-8")
    d = _tree(tmp_path, [_show("2026-09-02T10:00:00.000Z", SHA_A),
                         _asst("2026-09-02T10:01:00.000Z", DRAFT),
                         _msg("2026-09-02T10:05:00.000Z", "posli", "human")])
    assert not ow.check(SHA_A, project_dir=d, draft=str(f))[0]


def test_the_text_may_be_displayed_across_more_than_one_message(tmp_path):
    """A second round shows what changed, not the whole piece again, so per-message is wrong."""
    a, b = DRAFT.splitlines()
    f = tmp_path / "d.md"
    f.write_text(DRAFT, encoding="utf-8")
    d = _tree(tmp_path, [_asst("2026-09-02T09:50:00.000Z", a),
                         _show("2026-09-02T10:00:00.000Z", SHA_A),
                         _asst("2026-09-02T10:01:00.000Z", "changed one line: " + b),
                         _msg("2026-09-02T10:05:00.000Z", "posli", "human")])
    ok, why = ow.check(SHA_A, project_dir=d, draft=str(f))
    assert ok, why


def test_rewrapping_the_same_text_is_not_a_different_text(tmp_path):
    """A draft is hard-wrapped; a chat paste breaks elsewhere, and inside CJK a break is not even a
    space. Comparing on collapsed whitespace reported three shown lines as never shown."""
    body = "Prve tvrdenie o rozpore je presne toto. A cinsky retazec 8条标签完全一致，但每条都在同一个方向上 patri k nemu."
    f = tmp_path / "d.md"
    f.write_text(body, encoding="utf-8")
    rewrapped = ("Prve tvrdenie o rozpore\nje presne toto. A cinsky retazec 8条标签完全一致，但每条都在同一个\n"
                 "方向上 patri k nemu.")
    d = _tree(tmp_path, [_show("2026-09-02T10:00:00.000Z", SHA_A),
                         _asst("2026-09-02T10:01:00.000Z", rewrapped),
                         _msg("2026-09-02T10:05:00.000Z", "posli", "human")])
    ok, why = ow.check(SHA_A, project_dir=d, draft=str(f))
    assert ok, why


def test_a_short_draft_is_still_checked_rather_than_waved_through(tmp_path):
    """No sentence clears the length floor, and 'nothing to check' must not read as a pass."""
    f = tmp_path / "d.md"
    f.write_text("too short to sample\n", encoding="utf-8")
    d = _tree(tmp_path, [_show("2026-09-02T10:00:00.000Z", SHA_A),
                         _msg("2026-09-02T10:05:00.000Z", "posli", "human")])
    assert not ow.check(SHA_A, project_dir=d, draft=str(f))[0]


def test_the_live_project_is_readable_so_these_fixtures_are_not_the_only_thing_that_runs():
    """CONTROL. Every test above uses a fixture. If the real reader were broken, they would all still
    pass, so assert the module can parse the transcripts it ships against."""
    paths = ow._transcripts()
    if not paths:
        pytest.skip("no transcripts on this machine")
    shows, humans = ow.scan(paths[-1])
    assert isinstance(shows, list) and isinstance(humans, list)
    assert all(x for _, x in humans), "a human message with empty text would be counted"

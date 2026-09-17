# -*- coding: utf-8 -*-
"""tools/skill_ran.py: the transcript fallback must name the directory Claude Code actually writes.

WHY THIS FILE EXISTS. `transcript_path()` falls back to the newest transcript under
`~/.claude/projects/<slug>/` when `CLAUDE_TRANSCRIPT_PATH` is unset. The first slug rule prefixed a
literal `C--` and only removed the colon, so `C:\\Users\\Danculus\\agora` became
`C--C-Users-Danculus-agora`. Claude Code names the directory `C--Users-Danculus-agora`: every
character that is not a letter or a digit becomes a hyphen, including the colon and the first
backslash. The fallback therefore found no directory, and `humanizer_receipt.py record --in-session`
refused every draft with "no session transcript found" (measured 2026-09-17, session 1a4669bc).

The rule is tested on its own, and then on this machine: the slug of the repository root must be a
directory that exists under `~/.claude/projects`, which is the only check that would have caught the
first version.
"""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import skill_ran as sr  # noqa: E402

PROJECTS = os.path.join(os.path.expanduser("~"), ".claude", "projects")


@pytest.mark.skipif(os.name != "nt", reason="a Windows drive path only resolves as one on Windows")
def test_the_drive_letter_stays_and_the_colon_becomes_a_hyphen():
    assert sr.project_slug("C:\\Users\\Danculus\\agora") == "C--Users-Danculus-agora"


def test_every_character_that_is_not_a_letter_or_digit_becomes_a_hyphen():
    slug = sr.project_slug(ROOT)
    assert slug and all(c.isalnum() or c == "-" for c in slug)
    assert "-" in slug  # ROOT has at least one separator, and it must not survive


@pytest.mark.skipif(not os.path.isdir(PROJECTS), reason="no ~/.claude/projects on this machine")
def test_the_slug_of_this_repository_is_a_directory_claude_code_wrote():
    assert os.path.isdir(os.path.join(PROJECTS, sr.project_slug(ROOT)))


@pytest.mark.skipif(not os.path.isdir(PROJECTS), reason="no ~/.claude/projects on this machine")
def test_the_first_rule_named_a_directory_that_does_not_exist():
    # The mutation this file guards against. If the old construction ever resolves, the harness
    # changed its naming and both this test and project_slug() need a second look.
    old = "C--" + os.path.abspath(ROOT).replace(":", "").replace("\\", "-").replace("/", "-").lstrip("-")
    assert not os.path.isdir(os.path.join(PROJECTS, old))

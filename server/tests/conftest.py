# -*- coding: utf-8 -*-
"""A test that writes a runtime ledger into the checkout fails here, not 300 tests later.

WHY THIS FILE EXISTS. On 2026-09-06 box_mark began writing server/.scout.json, and two tests that
redirected only the box left a two-row ledger in every checkout that ran the suite. The failure
surfaced in an unrelated file: a test that skipped when no ledger existed stopped skipping, read
the leaked rows and failed, and CI on main stayed red for eleven days with the wrong test named.

This fixture lists the untracked server/.*.json files before the session and again after. A file
the suite created is a test writing where the live server writes. It fails the session with the
file's name, which is one grep away from the test that wrote it.

Creation only, on purpose. On the owner's machine the live ledgers exist and the brain writes them
while tests run, so a modification check would fire on the server's own writes. Creation is the
signal a fresh checkout, which is what CI is, can see without a false alarm.
"""
from __future__ import annotations

from pathlib import Path

import pytest

SERVER = Path(__file__).resolve().parents[1]


def _runtime_ledgers() -> set[str]:
    return {p.name for p in SERVER.glob(".*.json")}


@pytest.fixture(scope="session", autouse=True)
def no_test_may_create_a_runtime_ledger():
    before = _runtime_ledgers()
    yield
    created = sorted(_runtime_ledgers() - before)
    for name in created:
        try:
            (SERVER / name).unlink()   # leave the checkout as it was found
        except OSError:
            pass
    assert not created, (
        "the suite created %s under server/. A test wrote to a live ledger path instead of a "
        "tmp_path; redirect the module's _STORE/_BOX (grep the fixture rows in the file to find it)."
        % ", ".join(created))

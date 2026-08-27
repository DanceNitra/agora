"""The Crucible's construction gate audits exactly the receipts the page offers the reader.

WHY THIS FILE EXISTS. `entry_code` resolves a receipt three ways — an explicit `code` on the entry,
the durable `_PROBE_BY_LAB` map, or a fallback to the lab script. The gate beside it re-implemented
only the FIRST TWO, under a comment asserting "the resolver here is entry_code()'s own, so the gate
audits exactly the files the page will offer the reader as receipts". It was a copy that had lost a
branch, so every entry whose receipt came from the lab-script fallback was published as a runnable
model and never audited for a result forced by its own construction — which is the one defect
publish_gate exists to catch.

Second defect in the same expression: the resolution test was `(ROOT / p).exists()`, a LOCAL DISK
check, while the link it produces is a `blob/main/<path>` URL that only works for a file in the
pushed repo. `.gitignore` has excluded `agora_output/lab/` since 2026-06-20. Measured 2026-08-14:
2 of 43 published receipt links pointed at untracked files and would 404 for every reader.

Both are the same shape, and it is this repo's most expensive one: a check that never sees its real
target reports SAFE. So the property pinned here is an EQUALITY, not a threshold — the audited set
and the linked set must be the same set, because any gap between them is a receipt nobody checked.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

spec = importlib.util.spec_from_file_location("render_crucible_under_test",
                                              TOOLS / "render_crucible.py")
rc = importlib.util.module_from_spec(spec)
sys.modules["render_crucible_under_test"] = rc
spec.loader.exec_module(rc)


@pytest.fixture(scope="module")
def ledger():
    cur = json.loads((TOOLS / "crucible_curation.json").read_text(encoding="utf-8"))
    reps = rc._dedup_ledger(rc.load(rc.REPS), cur)
    return reps, rc.lab_index(rc.load(rc.LAB))


def test_the_audited_set_equals_the_linked_set(ledger):
    """The invariant. A receipt the page offers and the gate never opened is the whole defect."""
    reps, labs = ledger
    # The receipts are runtime artifacts, not repository contents, so a fresh checkout resolves none
    # of them. The final assertion below is right to refuse an empty set; it simply cannot be
    # reached honestly here. Skip on the absent input, and keep the invariant wherever receipts do
    # exist.
    if not reps:
        pytest.skip("no replication receipts in this environment")
    linked, audited = set(), set()
    for r in reps:
        rel, _ = rc.entry_code_rel(r, labs)
        if rc.entry_code(r, labs):
            linked.add(rel)
        if rel:
            audited.add(rel)
    assert linked == audited, (
        f"the gate and the page disagree — linked-but-unaudited: {sorted(linked - audited)}; "
        f"audited-but-unlinked: {sorted(audited - linked)}")
    assert linked, "no receipts resolved at all — an empty set proves nothing"


def test_every_published_receipt_is_tracked_in_git(ledger):
    """A blob/main URL for an untracked file is a 404 dressed as evidence. Two shipped that way."""
    reps, labs = ledger
    tracked = rc.tracked_files()
    assert tracked, "git ls-files returned nothing — the check would pass vacuously"
    broken = [rel for r in reps if (rel := rc.entry_code_rel(r, labs)[0]) and rel not in tracked]
    assert broken == [], f"receipts linked but not in the repo (they 404): {broken}"


def test_the_gate_block_calls_the_resolver_rather_than_copying_it():
    """Pin the CALL. The defect was a second copy of the resolution logic, and a copy drifts."""
    src = (TOOLS / "render_crucible.py").read_text(encoding="utf-8", errors="replace")
    start = src.index("_gate_paths, _unresolved")
    # search from `start`: the name appears earlier in prose too, and an index() from 0 gives an
    # empty slice that would make every assertion below pass by examining nothing.
    gate = src[start:src.index("publish_gate.enforce(", start)]
    assert gate.strip(), "the gate block could not be located — this test measured nothing"
    assert "entry_code_rel(r, labs)" in gate, "the gate no longer calls the shared resolver"
    assert "_PROBE_BY_LAB" not in gate, "the gate re-derives the receipt path again"


def test_a_declared_but_missing_artifact_is_reported_as_unresolved():
    """publish_gate has an `unresolved=` channel that makes a declared-and-missing artifact a
    REFUSAL. render_crucible used to drop it through an `if p and exists()` filter instead."""
    rel, missing = rc.entry_code_rel({"code": "research/probes/does_not_exist_at_all.py"}, {})
    assert rel is None and missing == "research/probes/does_not_exist_at_all.py"


def test_an_opportunistic_lab_fallback_that_is_missing_is_not_a_refusal():
    """The other half. The lab-script fallback is opportunistic, not declared — an unresolvable one
    yields no link and no refusal, or every entry without a public probe would block the render."""
    labs = {"L1": {"script": "C:/x/agora_output/lab/never_committed.py"}}
    rel, missing = rc.entry_code_rel({"lab_id": "L1"}, labs)
    assert rel is None and missing is None


def test_a_tracked_declared_artifact_resolves(ledger):
    """And the positive control: a real, tracked path must still produce a link, or the two tests
    above would pass against a resolver that had stopped resolving anything."""
    rel, missing = rc.entry_code_rel({"code": "tools/render_crucible.py"}, {})
    assert rel == "tools/render_crucible.py" and missing is None

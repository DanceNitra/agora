"""No organ may reference a name it never bound. `py_compile` does not catch this; a live cycle does.

Measured 2026-08-01. Artificer Rooke's cycle walked five unusable candidates with named reasons, found
its target, ran a REAL Lab (`lab 704014`, ok=True) and produced the verdict it exists to produce:

    VERDICT: NOT_COMPUTABLE -- claimed 0.0480 vs analytic 0.0528 (10.0% apart), but the finite-size
    bias spans 31.1% between N=240 and N=600 and the claim states no system size

and then threw it away, because eighty lines further down the report builder read `fam` and `sim`
while the selection loop had bound `_fam` and `_sim`. A rename had left the read site behind. The
cycle returned `status="error"`, `decisive=False`, `content` 0 chars. From the acceptance gate's
point of view Rooke had produced nothing, and would have gone on producing nothing every cycle
forever, with a working instrument and a real Lab run behind it each time.

`python -m py_compile` passes on that file: an unbound global is a RUNTIME lookup, and the failing
branch only executes after a Lab call succeeds -- the most expensive path in the organ and the last
one any quick check reaches.

So this is a static gate over EVERY organ and the spine, not a test of the one file that broke.
`test_the_scanner_catches_the_bug_it_was_added_for` re-runs the scan against the committed pre-fix
source and requires it to fail there, so a scanner that silently stops working cannot masquerade as
clean code.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
DUNGEON = REPO / "agora-game-server"
ORGANS = sorted((DUNGEON / "organs").glob("*.py"))

pytest.importorskip("pyflakes")


def _undefined(*paths) -> list[str]:
    out = subprocess.run([sys.executable, "-m", "pyflakes", *[str(p) for p in paths]],
                         capture_output=True, text=True, timeout=180)
    return [ln for ln in (out.stdout or "").splitlines()
            if "undefined name" in ln or "local variable" in ln and "referenced before" in ln]


def test_there_are_organs_to_scan():
    """THE CONTROL for the fixture. A glob that stops matching turns this file into a no-op that
    reports every organ clean."""
    assert len(ORGANS) >= 8, "expected 8 organ modules, found %d: %s" % (
        len(ORGANS), [p.name for p in ORGANS])


@pytest.mark.parametrize("organ", ORGANS, ids=lambda p: p.stem)
def test_organ_binds_every_name_it_reads(organ):
    hits = _undefined(organ)
    assert not hits, (
        "%s reads a name it never binds. This does not fail at import; it fails mid-cycle, after the "
        "work is already done, and the organ reports an error while the gate reads it as idle:\n  %s"
        % (organ.name, "\n  ".join(hits)))


def test_the_spine_binds_every_name_it_reads():
    hits = _undefined(DUNGEON / "mcp_server.py")
    assert not hits, "mcp_server.py:\n  %s" % "\n  ".join(hits)


def test_the_scanner_catches_the_bug_it_was_added_for(tmp_path):
    """THE FALSIFICATION CONTROL. Re-runs the scan on the committed pre-fix source. If this stops
    reporting the defect, the scanner has stopped working and every green above means nothing."""
    # encoding is explicit. `text=True` decodes with the locale codec, which on this box is cp1250 and
    # dies on the first non-Latin byte in the source -- the control then SKIPPED, and a skipped
    # falsification control is a control that did not run while looking like a passing suite.
    src = subprocess.run(["git", "show", "3fd38e7:agora-game-server/organs/artificer.py"],
                         capture_output=True, encoding="utf-8", errors="replace",
                         cwd=str(REPO), timeout=60)
    if src.returncode != 0 or not src.stdout:
        pytest.skip("pre-fix revision 3fd38e7 not reachable from this checkout")
    p = tmp_path / "artificer_prefix.py"
    p.write_text(src.stdout, encoding="utf-8")
    hits = _undefined(p)
    assert any("undefined name 'fam'" in h for h in hits), (
        "the scanner no longer flags the NameError that shipped a discarded NOT_COMPUTABLE verdict; "
        "it cannot be trusted to flag the next one. Hits: %s" % hits)

"""No Zenodo publisher mints a DOI on a bare invocation.

WHY THIS EXISTS. A Zenodo DOI is permanent — the service does not delete a published record. Six
tools in `tools/` can mint one, and in all six `SANDBOX = "--sandbox" in sys.argv`, so the safe
target is opt-IN and the default is production. Two of them (crucible, paper) stage a draft and
require a second, explicit `--publish`; the paper one added `--deposition <id>` on 2026-08-10 after
a `--publish` run opened a SECOND deposition and only a Zenodo 504 prevented two DOIs for one paper.

The other four called `actions/publish` as the unconditional last statement of `main()`. So
`python tools/publish_ramr_zenodo.py` — the first line of its own usage docstring — minted a
permanent public record with no confirmation step. The fix existed in the same directory for four
days and had been applied to two of six files.

That is why this test globs rather than listing: the defect was never "these four files are wrong",
it was "the guard lives in whoever remembers it". A publisher added next month is covered here the
moment it exists, and an empty glob is a failure rather than a pass — a check that found nothing to
check has measured nothing.
"""
from __future__ import annotations

from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[2] / "tools"
PUBLISH_CALL = "actions/publish"
GUARD = '"--publish" not in sys.argv'


def _zenodo_publishers() -> list[Path]:
    return sorted(p for p in TOOLS.glob("publish_*_zenodo.py"))


def test_the_scan_actually_finds_publishers():
    """An empty target set is a refusal, not a pass. If a rename ever moves these files out of the
    glob, this fails loudly instead of reporting six silent successes."""
    found = _zenodo_publishers()
    assert len(found) >= 6, f"expected the six known Zenodo publishers, found {[p.name for p in found]}"
    names = {p.name for p in found}
    for known in ("publish_crucible_zenodo.py", "publish_paper_zenodo.py",
                  "publish_ramr_zenodo.py", "publish_folklore_zenodo.py",
                  "publish_agentreceipts_zenodo.py", "publish_inspeximus_zenodo.py"):
        assert known in names, f"{known} is no longer covered by the glob"


@pytest.mark.parametrize("tool", _zenodo_publishers(), ids=lambda p: p.name)
def test_the_mint_sits_behind_an_explicit_publish_flag(tool: Path):
    """The guard must come BEFORE the mint, in the same file. Position matters: a `--publish` check
    after the POST would read as present and prevent nothing."""
    src = tool.read_text(encoding="utf-8", errors="replace")
    mint = src.find(PUBLISH_CALL)
    assert mint != -1, f"{tool.name} no longer calls {PUBLISH_CALL} — retarget this test deliberately"
    guard = src.find(GUARD)
    assert guard != -1, (
        f"{tool.name} mints a DOI with no `{GUARD}` guard. A bare run of it publishes an "
        f"irreversible public record.")
    assert guard < mint, (
        f"{tool.name} has the guard AFTER the mint at offset {mint} — it cannot prevent anything.")


@pytest.mark.parametrize("tool", _zenodo_publishers(), ids=lambda p: p.name)
def test_production_is_still_the_default_and_is_therefore_still_worth_guarding(tool: Path):
    """The control that keeps the test above meaningful.

    If someone later inverts the default so `--production` is opt-in, these guards stop being the
    thing standing between a bare run and a permanent DOI, and this assertion fires to say the
    reasoning above no longer describes the code. A guard test that survives the disappearance of
    the hazard it guards is measuring nothing.
    """
    src = tool.read_text(encoding="utf-8", errors="replace")
    assert 'SANDBOX = "--sandbox" in sys.argv' in src, (
        f"{tool.name} no longer defaults to production; re-read whether the --publish guard is "
        f"still the right shape.")

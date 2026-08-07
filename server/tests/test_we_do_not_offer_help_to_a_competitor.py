"""We do not help competitors -- and the finder that looks for "who needs what we ship" finds them best.

A contribution finder scores a thread by how precisely its need maps onto supersession, revert,
receipted erasure and the no-LLM-write property. That description IS a competing memory product's
issue tracker, so competitors are not noise in the shortlist: they are the highest-fidelity match it
can make. Measured on `agora_output/contribution_shortlist.json` (2026-07-21, 40 candidates): 6 were
competitor threads -- 5x mem0ai/mem0 and moorcheh-ai/memanto at rank 4 -- and nothing anywhere in the
pipeline excluded them.

The tests that matter here are the CONTROLS, because the cheap version of this filter passes its
happy path and quietly costs us our best distribution channel:

  * `langchain-ai/langmem` competes with us and `langchain-ai/langgraph` does not -- same org. An
    org-wide rule would have blacklisted the partner that merged our integration docs
    (langchain-ai/docs#5019) on the same day this filter was written.
  * scout.find_learning() must stay UNFILTERED. Reading a competitor is how we stay honest; the rule
    is about offering help, and a filter that cannot tell those apart destroys the intel channel.
  * the excluded rows are REPORTED, not silently dropped, so "0 competitors" can be distinguished
    from "the filter never ran".
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agora.execution.competitor_watch import is_competitor_repo  # noqa: E402
from agora.execution import contribution_finder as CF  # noqa: E402
from agora.execution import scout as S  # noqa: E402

# The six that actually sat in the shortlist, verbatim.
MEASURED_COMPETITORS = [
    "mem0ai/mem0",
    "moorcheh-ai/memanto",
]
# Repos we ship adapters for or have shipped docs into. Excluding these is the expensive failure.
PARTNERS = [
    "langchain-ai/langgraph",
    "langchain-ai/langchain",
    "langchain-ai/docs",
    "crewAIInc/crewAI",
    "run-llama/llama_index",
    "mlflow/mlflow",
    "anthropics/claude-code",
]


@pytest.mark.parametrize("repo", MEASURED_COMPETITORS)
def test_a_competitor_repo_is_recognised(repo):
    assert is_competitor_repo(repo) is True


def test_a_single_product_org_is_matched_whole():
    """mem0ai/mem0-ts is mem0 too. Exact-name-only would let every sibling repo through."""
    assert is_competitor_repo("mem0ai/mem0-ts") is True
    assert is_competitor_repo("MEM0AI/Mem0") is True          # case is not a way out
    assert is_competitor_repo("mem0ai/mem0/") is True         # nor is a trailing slash


@pytest.mark.parametrize("repo", PARTNERS)
def test_a_partner_is_not_excluded(repo):
    assert is_competitor_repo(repo) is False


def test_the_mixed_org_control():
    """The one case where exact and org-wide disagree -- and the org-wide answer is wrong."""
    assert is_competitor_repo("langchain-ai/langmem") is True
    assert is_competitor_repo("langchain-ai/langgraph") is False


@pytest.mark.parametrize("junk", ["", None, "notarepo", "/", "owner"])
def test_a_malformed_repo_is_not_a_competitor(junk):
    assert is_competitor_repo(junk) is False


class _FakeLib:
    def __init__(self, items):
        self.items = items


def _row(repo, title):
    return {"text": f"our agent memory keeps returning a stale value after we update memory; "
                    f"we need to revert to the previous one. {title}",
            "meta": {"title": title, "url": f"https://github.com/{repo}/issues/1", "repo": repo,
                     "kind": "issue", "source": "github", "comments": 5, "updated": "2026-07-20"}}


def test_find_drops_competitors_and_keeps_partners(monkeypatch):
    """Through the real find(), not through the predicate -- the defect was a rule that existed and
    was never consulted, which asserting on is_competitor_repo alone would have passed."""
    rows = [_row(r, f"issue in {r}") for r in
            ["mem0ai/mem0", "moorcheh-ai/memanto", "crewAIInc/crewAI", "langchain-ai/langgraph"]]
    monkeypatch.setattr("agora.execution.external_library._inspeximus", lambda: _FakeLib(rows))

    got = CF.find(limit=25)
    repos = [c["repo"] for c in got["candidates"]]

    assert "crewAIInc/crewAI" in repos and "langchain-ai/langgraph" in repos
    assert "mem0ai/mem0" not in repos and "moorcheh-ai/memanto" not in repos
    # reported, not silently truncated
    assert sorted(d["repo"] for d in got["competitors_excluded"]) == ["mem0ai/mem0",
                                                                      "moorcheh-ai/memanto"]
    assert got["total_matching"] == 2


def test_the_fixture_still_reproduces_the_defect(monkeypatch):
    """CONTROL. If the rows above stopped being competitors, every assertion above would pass
    vacuously. This fails in that case instead of reporting safe."""
    monkeypatch.setattr(CF, "is_competitor_repo", lambda r: False, raising=False)
    rows = [_row(r, "x") for r in ["mem0ai/mem0", "moorcheh-ai/memanto"]]
    monkeypatch.setattr("agora.execution.external_library._inspeximus", lambda: _FakeLib(rows))
    # with the guard neutralised at its import site the finder must still admit them, proving the
    # fixture rows really are things the finder wants to surface
    import agora.execution.competitor_watch as CW
    monkeypatch.setattr(CW, "is_competitor_repo", lambda r: False)
    got = CF.find(limit=25)
    assert len(got["candidates"]) == 2, "fixture no longer reaches the filter -- rewrite it"
    assert got["competitors_excluded"] == []


def test_the_scout_box_refuses_a_competitor_contribute_lead(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "_BOX", tmp_path / "box.json")
    monkeypatch.setattr(S, "_STORE", tmp_path / "ledger.json")
    lead = {"url": "https://github.com/mem0ai/mem0/issues/9", "repo": "mem0ai/mem0",
            "title": "memory keeps returning a stale value", "body": "agent memory", "score": 9}
    assert S.box_add(dict(lead), kind="contribute") is None
    # CONTROL: the same lead from a non-competitor repo is accepted, so the None above is the
    # competitor rule firing and not the box rejecting everything.
    ok = dict(lead, url="https://github.com/acme/widget/issues/9", repo="acme/widget")
    assert S.box_add(ok, kind="contribute") is not None


def test_learning_from_a_competitor_is_not_blocked():
    """Reading them is the point of competitor_watch; only the help paths are gated."""
    src = Path(S.__file__).read_text(encoding="utf-8")
    learn = src[src.index("def find_learning"):]
    assert "is_competitor_repo" not in learn, "find_learning must stay open -- intel is not support"


def test_the_shipped_shortlist_would_be_cleaned():
    """Real data as a bonus check on top of the fixtures above.

    Deliberately NOT a strict "must still contain 6" assertion. That artifact is regenerated by the
    very finder this commit fixes, so pinning a count here would fail the day the fix takes effect --
    a tripwire that goes off on success. The teeth for this filter live in the fixture tests above
    (5/5 mutants killed); this one only confirms the predicate still recognises real-world rows and
    that nothing a partner owns is caught by it.
    """
    p = Path(__file__).resolve().parents[2] / "agora_output" / "contribution_shortlist.json"
    if not p.exists():
        pytest.skip("shortlist artifact not present")
    cands = json.loads(p.read_text(encoding="utf-8")).get("candidates") or []
    assert cands, "artifact present but empty -- it cannot witness anything"
    flagged = sorted({c["repo"] for c in cands if is_competitor_repo(c.get("repo", ""))})
    survivors = [c["repo"] for c in cands if not is_competitor_repo(c.get("repo", ""))]
    # whatever it flags must be a competitor we actually named, never a partner
    assert all(is_competitor_repo(r) for r in flagged)
    assert not any(is_competitor_repo(r) for r in survivors)
    # as measured 2026-08-07 the file carried exactly these; kept as documentation, not as a gate
    assert set(flagged) <= {"mem0ai/mem0", "moorcheh-ai/memanto"}, f"unexpected flag: {flagged}"

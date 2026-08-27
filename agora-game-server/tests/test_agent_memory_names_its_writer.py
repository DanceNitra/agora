"""An agent's own memories must be attributable to that agent, and a restatement is not a witness.

Measured 2026-07-31 across the eight live dungeon stores in `.agent_memory/`:

    261,673 records    source 0.000%    derived_from 0.000%    taint 0.000%

`slash(scope='source')` is the default scope and the operation the whole accountability argument rests
on. It selects records whose canonical source intersects the caught source. At 0.000% coverage it
matched nothing, on every call, for the entire history of the deployment -- and returned successfully
each time. We were running our own library with its principal mechanism switched off by omission, and
nothing anywhere reported a problem, because a lever that selects on an empty field is indistinguishable
from a lever with nothing to do.

The second consequence is worse than the missing lever. With no source, inspeximus falls back to
`id:<record id>`, so every record is its OWN distinct source. Measured on three restatements of one
claim by one agent: 3 distinct sources before, 1 after. An agent could corroborate itself into semantic
graduation simply by saying the same thing three ways -- the exact echo surface the library exists to
close, left open in the deployment that is supposed to be the proof it works.

Also fixed here: the write truncated at 300 characters, the fourth copy of that defect found in one
day (agent_os at 500, the contribution POST at 500, the seminar bridge at 500). A finding's `Source:`
line and its falsifier sit at the END of the text, so a narrow cut removes precisely the part that
makes the claim testable. The cap is now set by value: findings get room, chatter stays narrow and
decays out as before.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

Inspeximus = pytest.importorskip("inspeximus").Inspeximus

SRC = HERE / "mcp_server.py"


def _write_call() -> str:
    """The remember() call inside the agent-memory write path, as source text."""
    txt = SRC.read_text(encoding="utf-8", errors="replace")
    i = txt.index("_saved_embed = getattr(m, \"embed\", None)")
    return txt[i:i + 1600]


def test_the_write_path_exists_where_this_test_looks(tmp_path):
    """THE CONTROL. If the anchor moves, every assertion below silently stops examining anything."""
    body = _write_call()
    assert "m.remember(" in body, "the agent-memory remember() call is no longer at this anchor"


def test_the_agent_write_names_its_source():
    body = _write_call()
    assert re.search(r'source=\{"doc":\s*"agent:%s"\s*%\s*eid\}', body), (
        "the agent's write does not name the agent, so slash(scope='source') -- the default scope -- "
        "matches nothing on our own deployment")


def test_a_finding_is_not_cut_at_300_chars():
    body = _write_call()
    assert "s[:300]" not in body, "the flat 300-char cut is back; findings lose their falsifier"
    assert "_AGENT_MEM_FINDING_CHARS" in body and "_AGENT_MEM_CHATTER_CHARS" in body, (
        "the width is no longer chosen by value")


def test_the_finding_cap_is_wide_enough_for_a_source_line_and_a_falsifier():
    import mcp_server  # noqa: F401  (import cost is accepted: this asserts the live constant)
    assert mcp_server._AGENT_MEM_FINDING_CHARS >= 1200, (
        "a finding cap of %d still severs the Source: line and the falsifier that follow the claim"
        % mcp_server._AGENT_MEM_FINDING_CHARS)
    assert mcp_server._AGENT_MEM_CHATTER_CHARS <= 600, (
        "chatter was widened too; it decays out anyway and this only inflates a 261k-record store")


def test_one_agent_restating_itself_is_one_source_not_three(tmp_path):
    """The measurement that made this more than tidiness. Before: 3 restatements = 3 distinct sources,
    so an agent corroborated itself. After: 1."""
    st = Inspeximus(path=str(tmp_path / "a.json"), embed=None)
    claims = ["retrieval degrades when the index is stale",
              "a stale index degrades retrieval quality",
              "retrieval quality drops with index staleness"]
    ids = [st.remember(c, tags=["thief"], value=2.5, mtype="semantic",
                       source={"doc": "agent:thief"}) for c in claims]
    by = {r["id"]: r for r in st.items}
    distinct = {tuple(sorted(Inspeximus._rec_sources(by[i]))) for i in ids}
    assert len(distinct) == 1, (
        "three restatements by one agent resolve to %d distinct sources; each can witness the others"
        % len(distinct))


def test_without_a_source_they_would_have_been_three(tmp_path):
    """THE FALSIFICATION CONTROL. If this stops holding, the fix above is closing nothing and the
    test before it passes for free."""
    st = Inspeximus(path=str(tmp_path / "b.json"), embed=None)
    claims = ["retrieval degrades when the index is stale",
              "a stale index degrades retrieval quality",
              "retrieval quality drops with index staleness"]
    ids = [st.remember(c, tags=["thief"], value=2.5, mtype="semantic") for c in claims]
    by = {r["id"]: r for r in st.items}
    distinct = {tuple(sorted(Inspeximus._rec_sources(by[i]))) for i in ids}
    assert len(distinct) == 3, (
        "an unsourced write no longer falls back to a per-record identity, so the self-corroboration "
        "hole this fix closes may not exist any more -- re-measure before trusting the test above")


def test_a_slash_by_agent_now_reaches_that_agent_only(tmp_path):
    st = Inspeximus(path=str(tmp_path / "c.json"), embed=None)
    kael = st.remember("scout: the gap is in retrieval integrity", tags=["thief"], value=2.5,
                       source={"doc": "agent:thief"})
    mira = st.remember("curator: the canon covers retrieval integrity", tags=["scholar"], value=2.5,
                       source={"doc": "agent:scholar"})
    st.credit(kael, True, weight=5.0)
    st.credit(mira, True, weight=5.0)
    res = st.slash([kael], scope="source")
    by = {r["id"]: r for r in st.items}
    assert res["slashed"] == 1, "expected exactly Kael's record, got %d" % res["slashed"]
    assert (by[kael].get("meta") or {}).get("slashed")
    assert not (by[mira].get("meta") or {}).get("slashed"), "the slash crossed into another agent"

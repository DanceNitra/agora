"""A verdict the gate does not recognise makes the work vanish, not fail.

Each ledger is scored against a per-organ vocabulary: `decisive` means the entry CHANGED something,
`inconclusive` means work merely started. A value in neither list is counted as neither -- so the
record is not scored as idle, it is scored as nothing at all, and the agent's row loses it silently.

Found 2026-07-31 by sweeping every ledger's live verdict values against the config, rather than by
reading the config. Three ledgers were writing words the gate had never heard:

  .theory.json        `unmodelable`   -- a PRE-REGISTERED outcome of the theory rule: it fires when
                                         the falsification control reproduces the signature, i.e. the
                                         measurement was never evidence about the mechanism. That
                                         closes the question and forbids the claim, so it is decisive.
  .analogies.json     `shipped (lab)` -- the outcome when an analogy is accepted and written out,
                                         the most decisive thing that organ does.
  .cartography.json   `off-board`     -- a RETIREMENT, not a research outcome. Inconclusive: counting
                                         it decisive would pay an agent for a backlog cleanup.

repair_ledger.py already records what this costs when it happens: "each organ speaks its own
vocabulary, and a ledger that only knows one of them reports the others as idle" -- Wren scored 0 of
80, Orin 10 read as 1, Elara 93 in a day read as 0, and every error fell AGAINST the agent.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
GATE = REPO / "probes" / "swarm_health.py"
SERVER = REPO / "server"


def specs() -> dict:
    src = GATE.read_text(encoding="utf-8", errors="replace")
    out = {}
    for m in re.finditer(r'"(\.[a-z_]+\.json)": dict\((.*?)\n    \),', src, re.S):
        def field(key):
            mm = re.search(key + r"=\(([^)]*)\)", m.group(2))
            return [t.strip().strip("\"'") for t in (mm.group(1).split(",") if mm else []) if t.strip()]
        out[m.group(1)] = dict(verdict_fields=field("verdict_fields"),
                               decisive=field("decisive"), inconclusive=field("inconclusive"))
    return out


def live_verdicts(name: str, spec: dict) -> set:
    p = SERVER / name
    if not p.exists():
        return set()
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return set()
    items = raw if isinstance(raw, list) else next((v for v in raw.values() if isinstance(v, list)), [])
    seen = set()
    for it in items[-200:]:
        if not isinstance(it, dict):
            continue
        for f in spec["verdict_fields"]:
            if it.get(f):
                seen.add(str(it[f]).strip().lower())
                break
    return seen


SPECS = specs()


def test_the_specs_parsed():
    assert len(SPECS) >= 8, "parsed %d ledger specs; the regex has drifted" % len(SPECS)
    for name, s in SPECS.items():
        assert s["decisive"] and s["verdict_fields"], "%s has an empty vocabulary" % name


@pytest.mark.parametrize("ledger", sorted(SPECS))
def test_every_live_verdict_is_classified(ledger):
    spec = SPECS[ledger]
    seen = live_verdicts(ledger, spec)
    if not seen:
        pytest.skip("%s has no records with a verdict yet" % ledger)
    known = [w.lower() for w in spec["decisive"] + spec["inconclusive"]]
    unknown = sorted(v for v in seen if not any(k in v for k in known))
    assert not unknown, (
        "%s writes %d verdict value(s) the gate classifies as neither decisive nor inconclusive, so "
        "those records vanish from the agent's row rather than failing: %s"
        % (ledger, len(unknown), [u[:40] for u in unknown]))


@pytest.mark.parametrize("ledger,word,bucket", [
    (".theory.json", "unmodelable", "decisive"),
    (".analogies.json", "shipped", "decisive"),
    (".cartography.json", "off-board", "inconclusive"),
])
def test_the_three_words_that_were_missing(ledger, word, bucket):
    """Pins each one to the side it belongs on, with the reason in the file docstring."""
    assert word in [w.lower() for w in SPECS[ledger][bucket]], (
        "%s is no longer %s for %s" % (word, bucket, ledger))


def test_a_retirement_is_not_scored_as_research():
    """The control that matters for `off-board`: it must NOT be decisive. 68 charts were retired in
    one batch operation; counting those would have handed the Map-maker a day's credit for a cleanup."""
    assert "off-board" not in [w.lower() for w in SPECS[".cartography.json"]["decisive"]]

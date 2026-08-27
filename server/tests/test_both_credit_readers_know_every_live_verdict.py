"""TWO readers score the same ledgers, and only one of them had a live sweep.

`probes/swarm_health.py` and `agora.execution.repair_ledger` independently classify every organ
store into decisive / inconclusive. swarm_health has had a test that reads the LIVE stores and
asserts every value it finds is known (`test_gate_knows_every_verdict_its_ledgers_write`).
repair_ledger has only ever been tested against HAND-WRITTEN fixtures --
`_is_decisive({"outcome": "REPRODUCED"}, ...)` -- and a fixture cannot contain a word its author
never thought of. So the two readers were guaranteed to drift, and they did.

Measured 2026-08-08. `RETRACTED` was added to `.replications.json` on 08-06, together with both
PUBLIC renderers (`render_crucible.py`, `check_public_counts.py`). Both CREDIT readers were missed.
The single record scored as neither decisive nor inconclusive in BOTH -- not as idle, as nothing --
so Artificer Rooke read 5 rows / 4 decisive, and **withdrawing a wrong verdict cost him the credit
he had while the verdict was still wrong.** Retracting must never pay worse than leaving an error
standing.

Note the near-miss: the retraction note says "the FAILED verdict overstated what it measured", and
`_is_decisive` matches on `_blob(rec)`. It would have been easy to assume the stray "failed" was
quietly rescuing the record. It is not -- `note` is not in `_BLOB_FIELDS`. Measured, not assumed.

This file sweeps the live stores against BOTH readers, so the next verdict word added to any organ
fails here rather than deleting an agent's work in silence.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SERVER = REPO / "server"
GATE = REPO / "probes" / "swarm_health.py"

sys.path.insert(0, str(SERVER))

from agora.execution import repair_ledger as RL  # noqa: E402

#: Stores whose closure signal is structural rather than a word. `.contributions.json` closes on the
#: boolean `verified`, handled explicitly in `_is_decisive`; sweeping it for verdict words is
#: meaningless. Listed, not silently skipped, so the reason is on the record.
_STRUCTURAL = {".contributions.json"}


def live_records(store: str) -> list[dict]:
    """The newest 200 records that carry any closure word at all."""
    p = SERVER / store
    if not p.exists():
        return []
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []
    items = raw if isinstance(raw, list) else next(
        (v for v in raw.values() if isinstance(v, list)), [])
    return [it for it in items[-200:]
            if isinstance(it, dict) and any(it.get(f) for f in RL._CLOSURE_FIELDS)]


def closure_of(rec: dict) -> str:
    for f in RL._CLOSURE_FIELDS:
        if rec.get(f):
            return str(rec[f]).strip().lower()
    return ""


def live_verdicts(store: str) -> set[str]:
    """The distinct closure words the store ACTUALLY writes."""
    return {closure_of(r) for r in live_records(store)} - {""}


def rl_classifies(store: str, rec: dict) -> bool:
    """Ask the REAL reader, on a REAL record.

    Deliberately not a re-implementation of the matching rules. An earlier draft of this file
    compared the closure VALUE against the word lists and reported `.oracle.json` broken over the
    value `1.0` -- but that store writes its call as a number and closes on `status: resolved`,
    which `_is_decisive` sees because it reads `_blob(rec)`, not the closure field alone. A control
    that recomputes the answer tests the re-implementation, not the code that runs.
    """
    if RL._is_decisive(rec, store):
        return True
    value = closure_of(rec)
    return any(value.startswith(w)
               for w in RL._INCONCLUSIVE_ANY + RL._INCONCLUSIVE.get(store, ()))


def gate_vocab(store: str) -> list[str]:
    """The gate's words for one store, parsed from its source (it is a probe, not an import)."""
    src = GATE.read_text(encoding="utf-8", errors="replace")
    m = re.search(re.escape('"%s": dict(' % store) + r"(.*?)\n    \),", src, re.S)
    if not m:
        return []
    words: list[str] = []
    for key in ("decisive", "inconclusive"):
        mm = re.search(key + r"=\(([^)]*)\)", m.group(1))
        if mm:
            words += [t.strip().strip("\"'").lower() for t in mm.group(1).split(",") if t.strip()]
    return words


ORGAN_STORES = sorted(s for s in RL._ORGANS if s not in _STRUCTURAL)


@pytest.mark.parametrize("store", ORGAN_STORES)
def test_repair_ledger_knows_every_live_verdict(store):
    """The sweep this reader never had. Unknown == scored as NOTHING, which is worse than idle."""
    recs = live_records(store)
    if not recs:
        pytest.skip("%s writes no closure word yet" % store)
    unknown = sorted({closure_of(r) for r in recs if not rl_classifies(store, r)})
    assert not unknown, (
        "repair_ledger classifies %d live verdict value(s) of %s as neither decisive nor "
        "inconclusive, so those records vanish from the agent's row: %s"
        % (len(unknown), store, [u[:40] for u in unknown]))


def test_the_two_readers_are_coupled_not_independent():
    """Why there is no 'do the two readers agree' test here, written down so it is not re-added.

    `swarm_health.is_decisive` ends with `return bool(parts["rl_is_decisive"](rec))` -- it consults
    repair_ledger as a repo-wide safety net, so a word added there is honoured by the gate without
    editing the gate. They are one reader with two vocabularies, not two independent ones.

    I drafted the agreement test anyway and it produced TWO false findings before this was checked,
    both from re-implementing the matching instead of calling it: `.oracle.json` writes `outcome:
    1.0` and closes on `status: resolved`, which both readers see and my re-implementation did not.
    The gate's own live sweep is `test_gate_knows_every_verdict_its_ledgers_write`; this file covers
    the other side. Between them both vocabularies are swept, with no re-implementation in either.
    """
    src = GATE.read_text(encoding="utf-8", errors="replace")
    assert "rl_is_decisive" in src, (
        "the gate no longer defers to repair_ledger -- the readers are now genuinely independent "
        "and an agreement test is needed after all")


def test_retracted_is_decisive_and_corrective_in_repair_ledger():
    """Pins the instance. A retraction is a ruling about our own ruling, and it REMOVES a standing
    claim -- the same family as `revised` and `retired`, which are corrective already."""
    rec = {"outcome": "RETRACTED"}
    assert RL._is_decisive(rec, ".replications.json") is True
    assert RL._is_corrective(rec, ".replications.json") is True


def test_retracted_is_decisive_in_the_gate():
    assert "retracted" in gate_vocab(".replications.json")


def test_the_note_is_not_what_rescues_the_record():
    """CONTROL, and the reason this was nearly misdiagnosed. The retraction text contains the word
    FAILED. If `note` were ever added to _BLOB_FIELDS, this record would score decisive for the
    wrong reason and the vocabulary fix would look unnecessary."""
    assert "note" not in RL._BLOB_FIELDS
    noteish = {"outcome": "SOMETHING_UNKNOWN",
               "note": "the FAILED verdict overstated what it measured"}
    assert RL._is_decisive(noteish, ".replications.json") is False


def test_the_live_retraction_now_counts():
    """End-to-end on the real ledger, not a fixture. Skips if the record is ever removed, rather
    than passing vacuously on an empty scope."""
    p = SERVER / ".replications.json"
    if not p.exists():
        pytest.skip("no replications ledger")
    raw = json.loads(p.read_text(encoding="utf-8"))
    items = raw if isinstance(raw, list) else next(
        (v for v in raw.values() if isinstance(v, list)), [])
    recs = [r for r in items
            if isinstance(r, dict) and str(r.get("outcome", "")).lower() == "retracted"]
    if not recs:
        pytest.skip("no RETRACTED record in the live ledger")
    for r in recs:
        assert RL._is_decisive(r, ".replications.json") is True
        assert RL._is_corrective(r, ".replications.json") is True

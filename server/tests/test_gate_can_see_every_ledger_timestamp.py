"""The gate must be able to see every timestamp its ledgers actually write.

This defect has now appeared twice, and both times it failed an agent for work she had done.

`.cartography.json` — the gate read `ts_fields=("ts",)` while `resolve_bridge` deliberately keeps
`ts` as *when the hole was charted* and adds `resolved_ts` for *when it was closed*. Cartographer
Wren's ruling, made 0.9 h before the run, was dated at 1057 h and fell outside the 24 h window. She
read as idle on the cycle she produced her only decisive outcome.

`.contradictions.json` — the same shape, caught here BEFORE the field arrived. `set_status` now
stamps `resolved_ts` (a dispute closed today may have been shortlisted weeks ago), so a gate reading
only `ts` would have repeated the Wren failure on Dame Elara, whose ledger closes ~100 records a day.

A ts field the writer stamps and the reader ignores is a silent window bug: nothing errors, the
record simply ages out of view. So this pins the READER against the WRITERS, not against a list I
maintained by hand.
"""
from __future__ import annotations

import json
import time
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
GATE = REPO / "probes" / "swarm_health.py"
SERVER = REPO / "server"

#: Any numeric field in this range is a unix timestamp (2001-09 .. 2065-01).
TS_LO, TS_HI = 1e9, 3e9


def gate_ts_fields() -> dict:
    src = GATE.read_text(encoding="utf-8", errors="replace")
    out = {}
    for m in re.finditer(r'"(\.[a-z_]+\.json)": dict\((.*?)\n    \),', src, re.S):
        tf = re.search(r"ts_fields=\(([^)]*)\)", m.group(2))
        out[m.group(1)] = [t.strip().strip("\"'") for t in (tf.group(1).split(",") if tf else [])
                           if t.strip()]
    return out


def _records(name: str) -> list:
    p = SERVER / name
    if not p.exists():
        return []
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []
    items = d if isinstance(d, list) else next((v for v in d.values() if isinstance(v, list)), [])
    return items[-200:]


def ledger_ts_fields(name: str) -> set:
    items = _records(name)
    have = set()
    for it in items[-200:]:
        if isinstance(it, dict):
            have |= {k for k, v in it.items() if isinstance(v, (int, float)) and TS_LO < float(v) < TS_HI}
    return have


CONFIG = gate_ts_fields()


def test_the_gate_config_was_parsed():
    """Guards the guard: a regex that matches nothing would make every test below pass vacuously."""
    assert len(CONFIG) >= 8, "parsed only %d ledger configs from the gate: %s" % (len(CONFIG), list(CONFIG))
    assert all(v for v in CONFIG.values()), "a ledger declares no ts_fields at all: %s" % (
        [k for k, v in CONFIG.items() if not v])


def _is_a_schedule(ledger: str, field: str) -> bool:
    """Is this field a DUE DATE rather than an event stamp? Measured, not declared.

    A timestamp field says when something happened; a schedule field says when something is due.
    `.predictions.json` carries `resolve_ts`, the date a forecast is to be scored, which is in the
    FUTURE on every pending record -- so reading it into the window would place every unresolved
    forecast inside any window, forever. That is the mirror of the failure this file guards: one
    ignores work that happened, the other counts work that has not.

    The criterion is the data's own and it is crisp: AN EVENT STAMP CANNOT BE IN THE FUTURE. A first
    cut asked whether values were "predominantly ahead of now" and failed on this very field --
    209 of the 242 forecasts are already resolved, so most `resolve_ts` values are in the past and
    the majority rule classified a due date as an event time. One future value is enough, and it is
    enough for the right reason rather than by tuning a fraction. Nothing is exempted by name.
    """
    now = time.time()
    seen = False
    for it in _records(ledger):
        v = it.get(field) if isinstance(it, dict) else None
        if isinstance(v, (int, float)) and TS_LO < float(v) < TS_HI:
            seen = True
            if float(v) > now + 60:            # 60s of clock skew, not a window
                return True
    return False


@pytest.mark.parametrize("ledger", sorted(CONFIG))
def test_the_gate_reads_every_timestamp_this_ledger_writes(ledger):
    have = ledger_ts_fields(ledger)
    if not have:
        pytest.skip("%s has no records with a timestamp yet" % ledger)
    missed = sorted(f for f in (have - set(CONFIG[ledger])) if not _is_a_schedule(ledger, f))
    assert not missed, (
        "%s records carry %s but the gate reads only %s -- work stamped with a field the reader "
        "ignores ages out of the window silently, which is how Wren read idle on the cycle she "
        "produced her only decisive outcome" % (ledger, missed, CONFIG[ledger]))


@pytest.mark.parametrize("ledger,field", [(".contradictions.json", "resolved_ts"),
                                          (".cartography.json", "resolved_ts"),
                                          (".scout_box.json", "ruled_ts")])
def test_a_close_timestamp_is_read_before_the_creation_one(ledger, field):
    """Order matters, not just presence: the gate takes the FIRST field it finds, and a ruling must
    be dated when it was RULED, not when its subject was first shortlisted."""
    fields = CONFIG.get(ledger) or []
    assert field in fields, "%s does not read %s" % (ledger, field)
    assert fields.index(field) < (fields.index("ts") if "ts" in fields else len(fields)), (
        "%s reads `ts` before `%s`, so a ruling gets dated by when its subject was created"
        % (ledger, field))

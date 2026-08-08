"""A shipped mechanism whose gating field is never populated must be refused, not reported SAFE.

On 2026-08-08 four defects turned out to be one defect wearing four hats:

  * the construction audit was built and tested, and lived in someone's memory instead of the publish path
  * `with_warrant` existed in the library and nowhere in the MCP server, so no agent could obtain it
  * `strict_corroboration` counts distinct verified keys; `attested_key` was populated on 0 of 111,264
  * `credit_requires_warrant` counts warranted credit; `good_warranted > 0` was 0 of 60,077

and before them, `slash(scope='source')` returning ok on 261,673 records because its default scope
resolved on a field no writer ever set.

Every one is "the code is correct and unreached". Our tests prove a mechanism works GIVEN its input.
Nothing asked whether the input ever arrives — and a guard with no input never fires, so it reports
SAFE forever. `tools/mechanism_coverage.py` asks that question against PRODUCTION data.

These tests are paired, because a coverage checker has both failure directions available to it: it can
miss a dead mechanism, and it can cry wolf on a healthy one. The second is what gets it deleted.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools" / "mechanism_coverage.py"


def _load():
    spec = importlib.util.spec_from_file_location("mechanism_coverage", TOOL)
    assert spec and spec.loader, f"cannot load {TOOL}"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mc = _load()


def _store(tmp_path, records):
    p = tmp_path / "store.json"
    p.write_text(json.dumps(records), encoding="utf-8")
    return p


# ------------------------------------------------------------------ must REFUSE a dead mechanism
def test_a_field_no_record_populates_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(mc, "STORES", [_store(tmp_path, [
        {"id": "1", "text": "a", "source": {"doc": "x"}, "key": "k1"},
        {"id": "2", "text": "b", "source": {"doc": "y"}, "key": "k2"},
    ])])
    monkeypatch.setattr(sys, "argv", ["mechanism_coverage.py"])
    assert mc.main() == 1, "a mechanism reading a never-written field must be refused"


def test_the_refusal_names_the_field_and_the_consequence(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(mc, "STORES", [_store(tmp_path, [{"id": "1", "text": "a", "source": "s", "key": "k"}])])
    monkeypatch.setattr(sys, "argv", ["mechanism_coverage.py"])
    mc.main()
    out = capsys.readouterr().out
    assert "attested_key" in out and "UNREACHABLE" in out
    assert "consequence:" in out, "a refusal that does not say what breaks is a number, not a finding"


# ------------------------------------------------------------------- must NOT cry wolf when healthy
def test_a_fully_populated_store_passes(tmp_path, monkeypatch):
    """The other half. A checker that refuses everything would pass both tests above."""
    monkeypatch.setattr(mc, "STORES", [_store(tmp_path, [
        {"id": "1", "text": "a", "source": {"doc": "x"}, "key": "k1",
         "attested_key": "aa" * 32, "good_warranted": 2.0},
    ])])
    monkeypatch.setattr(sys, "argv", ["mechanism_coverage.py"])
    assert mc.main() == 0, "every mechanism has a write path here; refusing is a false alarm"


def test_partial_coverage_is_not_treated_as_zero(tmp_path, monkeypatch):
    """One attested record in a hundred still means the write path EXISTS. The gate asks whether the
    field is reachable, not whether it is universal — conflating those would make it unusable the day
    after a fix ships, which is exactly when it must stay green."""
    recs = [{"id": str(i), "text": "t", "source": "s", "key": "k", "good_warranted": 1.0}
            for i in range(100)]
    recs[0]["attested_key"] = "bb" * 32
    monkeypatch.setattr(mc, "STORES", [_store(tmp_path, recs)])
    monkeypatch.setattr(sys, "argv", ["mechanism_coverage.py"])
    assert mc.main() == 0


def test_a_deliberate_exception_needs_naming_the_field(tmp_path, monkeypatch):
    """An escape hatch that is a blanket --force would be the gate switched off; it is per-field."""
    monkeypatch.setattr(mc, "STORES", [_store(tmp_path, [
        {"id": "1", "text": "a", "source": "s", "key": "k", "good_warranted": 1.0}])])
    monkeypatch.setattr(sys, "argv", ["mechanism_coverage.py", "--allow-zero", "attested_key"])
    assert mc.main() == 0
    monkeypatch.setattr(sys, "argv", ["mechanism_coverage.py", "--allow-zero", "some_other_field"])
    assert mc.main() == 1, "allowing an unrelated field must not excuse the dead one"


# --------------------------------------------------------------- the check must SEE something at all
def test_no_readable_store_is_a_refusal_not_a_pass(monkeypatch):
    """The failure this whole file exists to prevent, applied to the checker itself: reading nothing
    must never report OK."""
    monkeypatch.setattr(mc, "STORES", [Path("does") / "not" / "exist.json"])
    monkeypatch.setattr(sys, "argv", ["mechanism_coverage.py"])
    assert mc.main() == 1


def test_it_runs_as_a_script_against_the_real_stores():
    """Pin the entry point too: a gate that only works when imported is not wired into anything."""
    r = subprocess.run([sys.executable, "-X", "utf8", str(TOOL)],
                       capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode in (0, 1), f"the gate crashed instead of ruling: {r.stderr[-400:]}"
    assert "coverage" in r.stdout, "the gate produced no coverage table"

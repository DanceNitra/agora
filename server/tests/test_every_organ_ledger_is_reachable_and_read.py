"""Every organ's declared ledger must be WRITTEN by its endpoints and READ by the gate.

Two defects of this exact shape were found on 2026-08-01, one after the other:

  * Sage Mira's CANON -- the organ CLAUDE.md calls her primary -- wrote no ledger at all. Her
    curation rulings existed only as prose in a discovery row, so to every instrument that reads
    ledgers they were decisions that never happened.
  * King Aldric's working arm wrote to `.predictions.json` while only `.oracle.json`, the arm behind
    a network filter, was rostered to the gate. The reader was pointed at one of his two stores.

Both are the same failure: a chain of three links -- the organ DECLARES a ledger, its endpoints WRITE
one, the gate READS one -- where nothing checked that the three agree. This closes that.

WRITING THE AUDIT TOOK TWO ROUNDS AND THE MISSES ARE THE INSTRUCTIVE PART. A literal-only scan for
POST targets reported `artificer` and `cartographer` as writing NOWHERE, because they pass a
module-level constant (`_brain_post(ctx, _RECORD_PATH, body)`) rather than a string. Then a store
regex that knew `_STORE` and `_LEDGER` but not `_BOX` flagged Shadow Kael as writing the wrong file,
and taking only the first `from agora.execution.X import` line in an endpoint flagged Sergeant Voss,
whose handler imports two modules and writes through the second. Three false alarms, all from an
extractor that could not see its target -- the very class it was written to find.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
ORGANS = REPO / "agora-game-server" / "organs"
API = (REPO / "server" / "agora" / "api" / "agent_os_api.py").read_text(encoding="utf-8",
                                                                       errors="replace")


def _gate_roster() -> dict:
    import importlib.util
    spec = importlib.util.spec_from_file_location("sh_roster", REPO / "probes" / "swarm_health.py")
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(REPO / "server"))
    spec.loader.exec_module(mod)
    return {eid: files for eid, _n, _o, files in mod.ROSTER}


ROSTER = _gate_roster()
ORGAN_FILES = sorted(p for p in ORGANS.glob("*.py") if p.stem != "__init__")


def _declared(path: Path) -> str:
    m = re.search(r'"ledger":\s*"([^"]+)"', path.read_text(encoding="utf-8", errors="replace"))
    return m.group(1) if m else ""


def _post_paths(path: Path) -> list:
    """Brain paths this organ POSTs to, RESOLVING module-level string constants.

    A literal-only scan misses `_brain_post(ctx, _RECORD_PATH, body)` and reports the organ as
    writing nowhere -- which is how this audit first cleared two organs it had not examined.
    """
    tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    consts = {t.id: n.value.value
              for n in ast.walk(tree) if isinstance(n, ast.Assign)
              and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)
              for t in n.targets if isinstance(t, ast.Name)}
    out = set()
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        fn = n.func
        nm = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
        if "post" not in str(nm).lower():
            continue
        for a in n.args:
            if isinstance(a, ast.Constant):
                v = a.value
            elif isinstance(a, ast.Name):
                v = consts.get(a.id, "")
            elif isinstance(a, ast.BinOp):
                v = "".join(x.value if isinstance(x, ast.Constant) else consts.get(getattr(x, "id", ""), "")
                            for x in (a.left, a.right)
                            if isinstance(x, ast.Constant) or isinstance(x, ast.Name))
            else:
                v = ""
            if isinstance(v, str) and "/brain/" in v:
                out.add(v.split("/brain/")[-1].rstrip("/"))
    return sorted(out)


def _stores_written_by(endpoint: str) -> set:
    """Every `.json` store the handler for `/brain/<endpoint>` can reach, via EVERY module it imports.

    Taking only the first import flagged `belief-revise` as writing nothing: its handler imports
    `belief_revision` for the note stamp and `bounty` for the ledger, and the ledger is the second.
    """
    key = '"/brain/%s"' % endpoint
    if key not in API:
        return set()
    blk = API[API.index(key):][:1400]
    stores = set()
    for mod in re.findall(r"from agora\.execution\.(\w+) import", blk):
        p = REPO / "server" / "agora" / "execution" / (mod + ".py")
        if not p.exists():
            continue
        # any module-level Path constant ending in a .json name, whatever it is called
        stores |= set(re.findall(r'^_[A-Z_]+\s*=\s*[^\n]*?["\'](\.[\w.]+\.json)["\']',
                                 p.read_text(encoding="utf-8", errors="replace"), re.M))
    return stores


def test_there_are_organs_to_audit():
    """THE CONTROL. A glob that stops matching turns every case below into a vacuous pass."""
    assert len(ORGAN_FILES) >= 8, "found %d organ modules: %s" % (
        len(ORGAN_FILES), [p.stem for p in ORGAN_FILES])
    assert all(_declared(p) for p in ORGAN_FILES), "an organ declares no ledger: %s" % (
        [p.stem for p in ORGAN_FILES if not _declared(p)])


@pytest.mark.parametrize("organ", ORGAN_FILES, ids=lambda p: p.stem)
def test_the_gate_reads_the_ledger_the_organ_declares(organ):
    declared, rostered = _declared(organ), ROSTER.get(organ.stem, ())
    assert declared in rostered, (
        "%s declares %s and the gate reads %s -- its work is invisible to the instrument that decides "
        "whether the swarm is producing" % (organ.stem, declared, rostered or "NOTHING"))


# A CHECK I WROTE, MEASURED, AND REMOVED -- recorded because the reason matters more than the code.
#
# `declared in rostered` compares two DECLARATIONS, so it cannot catch a defect they share: with the
# pre-session roster restored this file still passed 25/25, because Sage Mira's ORGAN names
# `.press.json` (her secondary arm) and King Aldric's names `.oracle.json` (the arm behind a network
# filter) -- roster and declaration agreed, and both were wrong together. Exactly the blindness this
# repo already paid for with three copies of a lab-id regex, repeated by me two hours after writing
# the lesson down.
#
# So I added the reverse direction: every store an organ's endpoints REACH must be one the gate
# reads. It produced six failures and every one was a false positive of my own making. The flagged
# stores are side effects, not verdict ledgers: `.replication_vectors.json` is an embedding cache,
# `.academy.json` holds lessons, `.graveyard.json` is where killed beliefs go, `.actions.json` is the
# gated-action queue, `.scout.json` is a log, `.external_library_state.json` is a harvest cursor. The
# check was demanding the gate read a vector cache.
#
# Static analysis cannot separate "the store this organ's VERDICTS land in" from "a file some module
# in the import chain happens to touch", and a control whose every failure is spurious teaches the
# next reader to ignore the file. Removed rather than shipped. What survives below is the direction
# that DOES work -- declared must be among the stores actually reached -- plus the honest admission
# that the roster-vs-declaration check is a weak one.


@pytest.mark.parametrize("organ", ORGAN_FILES, ids=lambda p: p.stem)
def test_the_organ_actually_writes_somewhere(organ):
    assert _post_paths(organ), (
        "%s POSTs to no brain path this audit can resolve -- either it records nothing, or the "
        "extractor cannot see how it does (both have happened)" % organ.stem)


@pytest.mark.parametrize("organ", ORGAN_FILES, ids=lambda p: p.stem)
def test_some_write_path_reaches_the_declared_ledger(organ):
    """The link neither test above covers: an organ can declare a ledger the gate reads and still
    write somewhere else entirely. That is exactly what happened to King Aldric."""
    declared = _declared(organ)
    reached = set()
    for ep in _post_paths(organ):
        reached |= _stores_written_by(ep)
    if not reached:
        pytest.skip("%s: no handler for its POST targets resolves a store (endpoint may be "
                    "elsewhere); the declaration and roster checks still applied" % organ.stem)
    assert declared in reached, (
        "%s declares %s but its endpoints reach %s -- the ledger it is graded on is not the one it "
        "fills" % (organ.stem, declared, sorted(reached)))

"""Two dangerous sinks were deleted rather than hardened, and must not come back.

Both were confirmed UNREACHABLE by an adversarial review on 2026-08-14 — registered or defined,
never invoked. That is the state in which a sink is most likely to be re-enabled by someone who
does not know why it was left alone, so the deletion gets a pin.

  * `pata_executor._generate_code_via_llm` asked the model for {path, content} pairs and wrote each
    with `os.path.join(target_dir, rel_path)` — no normalisation, no containment. os.path.join
    DISCARDS target_dir on an absolute rel_path, and `../` traverses. Both values came from model
    JSON, steered by a quest built verbatim from a paper claim or a GitHub scan. One line in
    action_implement would have made it live. Containment alone would not have sufficed: the
    developer step git-commits its output into server/agora/**, so anything landing inside
    target_dir becomes imported code on the next brain restart.

  * `forge.action_run_script` ran subprocess.run(command, shell=True) behind a five-substring
    denylist ("rm  -rf" and "curl x | sh" walk past it), and `action_build` fed it
    `params["command"] or quest["goal"]` — a research goal, which is prose, never a command.
    RealActionEngine._run_script already provides the same capability correctly: shlex.split,
    shell=False, metacharacter rejection, a 21-command read-only allowlist.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "server"
if str(SERVER) not in sys.path:
    sys.path.insert(0, str(SERVER))

FORGE = ROOT / "server/agora/dungeon_os/actions/forge.py"
PATA = ROOT / "server/agora/dungeon_os/actions/pata_executor.py"
REGISTRY = ROOT / "server/agora/dungeon_os/actions/registry.py"


def _code_of(p: Path) -> str:
    """The file with comment lines removed — so the explanatory notes left in place of the deleted
    functions cannot satisfy a test that is looking for live code."""
    return "\n".join(ln for ln in p.read_text(encoding="utf-8", errors="replace").splitlines()
                     if not ln.lstrip().startswith("#"))


def test_no_shell_true_remains_in_the_forge():
    assert "shell=True" not in _code_of(FORGE), "the shell=True sink is back in forge.py"


@pytest.mark.parametrize("name", ["action_run_script", "action_build"])
def test_the_forge_handlers_are_gone(name):
    assert f"def {name}" not in _code_of(FORGE), f"{name} was re-added to forge.py"


@pytest.mark.parametrize("name", ["_generate_code_via_llm", "_generate_fallback_code"])
def test_the_llm_file_writer_is_gone(name):
    assert f"def {name}" not in _code_of(PATA), f"{name} was re-added to pata_executor.py"


def test_the_registry_does_not_register_them():
    src = _code_of(REGISTRY)
    for skill in ("run_script", "build_station", "store_blueprint"):
        assert f'"{skill}"' not in src, f"forge:{skill} is registered again"


def test_the_live_registry_exposes_no_shell_action():
    """Structural checks pass on a file that is no longer loaded. Build the real registry."""
    from agora.dungeon_os.actions.registry import get_registry
    r = get_registry()
    keys = sorted(getattr(r, "actions", None) or r._actions)
    assert keys, "the registry is empty — this test would pass vacuously"
    assert [k for k in keys if k.startswith("forge:")] == ["forge:request_resources"], \
        f"forge exposes more than the one safe action: {[k for k in keys if k.startswith('forge:')]}"
    assert not [k for k in keys
                if any(s in k for s in ("run_script", "build_station", "store_blueprint"))]


def test_the_wildcard_fallback_still_reaches_nothing_dangerous():
    """registry.execute falls back to `*:<skill>` when the exact pair misses. The only wildcards
    may be inert ones — a `*:run_script` registration would make every unmatched npc reach a shell."""
    from agora.dungeon_os.actions.registry import get_registry
    r = get_registry()
    keys = sorted(getattr(r, "actions", None) or r._actions)
    assert sorted(k for k in keys if k.startswith("*:")) == ["*:move", "*:wait"], \
        f"a new wildcard action appeared: {[k for k in keys if k.startswith('*:')]}"


def test_the_correct_implementation_still_exists():
    """The positive control. These were deleted because the capability lives elsewhere, done right —
    if that one ever goes away, deleting these was the wrong call and this says so."""
    # Through _code_of, like every other check here: the file's own comment explains why a
    # denylist plus shell=True is unsafe, and a raw substring test reads that explanation as the
    # defect it warns against.
    src = _code_of(ROOT / "server/agora/agent_os/real_action_engine.py")
    assert "def _run_script" in src, "the hardened replacement is gone"
    assert "shlex.split" in src, "the replacement no longer splits into argv"
    assert "shell=True" not in src, "the replacement itself now uses a shell"

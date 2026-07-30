"""FORWARDING SHIM — this directory is no longer a copy of inspeximus, it points at the real one.

WHY THIS FILE REPLACED A LIBRARY. `agora/inspeximus_pypi/` stopped being the release source after
0.7.19 (see the header of ../pyproject.toml and tools/publish_inspeximus_pypi.py, which builds from
`../inspeximus-repo`). The copy under this directory nevertheless kept being imported, by ~51 files
across research/probes/ and agora_output/lab/ doing `sys.path.insert(0, .../inspeximus_pypi)`. It drifted
to 1.20.0 while the shipping library reached 1.88.0 — and the drift was not cosmetic:

    forget_subject('hr/alice') over three records sourced hr/alice, hr/bob, hr/carol
      copy 1.20.0      erased 3  (bob and carol too — the whole store)
      canonical 1.88.0 erased 1

MEASURED 2026-07-29, both directions. So every number any lab script produced through this path
described a 1.20.0 artifact with a data-loss bug, not the product — the same defect class as verifying
a claim against the wrong artifact, and `research/probes/audit_lab_import_resolution.py` was already
written to flag it.

WHY A SHIM RATHER THAN EDITING 51 CALL SITES. The consumers' import forms are
`from inspeximus import Inspeximus` plus submodule imports (`inspeximus.core`, `inspeximus._surface`,
`inspeximus.integrations.*`, `inspeximus.deletion_manifest`). Rebinding `__path__` to the canonical
package satisfies all of them at once, so no consumer changes and none can silently resolve to a stale
copy again. Checked before doing it: canonical's public surface is a strict SUPERSET of the copy's
(167 attrs vs 138, zero copy-only names, and zero copy-only names called anywhere in agora), so this
breaks no call site by name. The only behaviour that changes is the behaviour that was wrong.

Note that some agora scripts ALREADY import `inspeximus.core` / `inspeximus._surface`, which never
existed in the copy — part of the tree expected the real library all along.

Override the location with INSPEXIMUS_REPO, the same variable the publish script honours.
"""
import os as _os

_HERE = _os.path.dirname(_os.path.abspath(__file__))
# agora/inspeximus_pypi/inspeximus -> ../../.. == the directory holding both checkouts
_SIBLING = _os.path.abspath(_os.path.join(_HERE, "..", "..", ".."))
_REPO = _os.environ.get("INSPEXIMUS_REPO") or _os.path.join(_SIBLING, "inspeximus-repo")
_PKG = _os.path.join(_REPO, "inspeximus")
_INIT = _os.path.join(_PKG, "__init__.py")

if not _os.path.isfile(_INIT):
    # FAIL LOUD. The whole point of this shim is that a caller can never quietly get a different
    # library than the one that ships; silently falling back to a local copy would rebuild the exact
    # trap this file exists to remove.
    raise ImportError(
        "inspeximus: this path is a forwarding shim to the canonical checkout, and the canonical "
        f"package was not found at {_PKG!r}. Clone https://github.com/DanceNitra/inspeximus.git "
        "next to the agora repo, or set INSPEXIMUS_REPO to its location. Refusing to import a stale "
        "local copy — that copy had a forget_subject() data-loss bug and produced measurements that "
        "described 1.20.0 rather than the shipped library.")

# Rebind the package to the canonical directory BEFORE executing its __init__, so that every relative
# import inside it (`from .core import ...`) and every later submodule import (`inspeximus.core`,
# `inspeximus.integrations.langgraph`, ...) resolves against the real tree.
__path__ = [_PKG]

with open(_INIT, encoding="utf-8") as _f:
    _src = _f.read()
exec(compile(_src, _INIT, "exec"))    # noqa: S102 — re-export the canonical public API verbatim

del _f, _src, _os

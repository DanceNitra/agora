"""Not the library — an alias to it. This directory holds Agora's research probes, not a copy.

It used to contain a full vendored copy of the memory library beside the probes, which drifted a
release behind the real one (1.24.4 against 1.25.0) and shadowed the installed package for anything
running from the Agora repo root. That is the "two mnemo" problem: two implementations, one of them
silently stale.

The library now lives in exactly one place — the installed `inspeximus` distribution
(`pip install inspeximus`). This file makes `import mnemo` from inside the Agora tree resolve to that
one implementation, so the 129 probe scripts here keep running unchanged and every published Crucible
receipt that cites `mnemo/probes/...` keeps pointing at code that still works.

The directory keeps its name deliberately: those probe paths are published in `public/crucible/` and
in several posts as the evidence behind replication verdicts, and a receipt that 404s is worse than an
awkward directory name.
"""
import importlib
import pkgutil
import sys

_TARGET = "inspeximus"

try:
    _pkg = importlib.import_module(_TARGET)
except ImportError as exc:                      # pragma: no cover - install-time misconfiguration
    raise ImportError(
        "Agora's probes need the memory library: pip install inspeximus"
    ) from exc


def _alias_tree(package, old_prefix):
    """Bind each submodule under the old name, pointing at the SAME object (no re-execution)."""
    for info in pkgutil.iter_modules(package.__path__):
        old_name = f"{old_prefix}.{info.name}"
        try:
            module = importlib.import_module(f"{package.__name__}.{info.name}")
        except Exception:
            continue                            # optional integration whose extra isn't installed
        sys.modules[old_name] = module
        if info.ispkg and hasattr(module, "__path__"):
            _alias_tree(module, old_name)


_alias_tree(_pkg, __name__)

globals().update({k: v for k, v in vars(_pkg).items() if not k.startswith("__")})
__all__ = list(getattr(_pkg, "__all__", []))
__version__ = getattr(_pkg, "__version__", None)

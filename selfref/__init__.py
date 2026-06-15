"""selfref — self-reference governor: measure collapse (data-mix) and lock (self-trust) risk
in any system that learns from its own output. Zero-dependency core."""
from .selfref import (
    collapse_risk,
    min_external_anchor,
    lock_fraction,
    lock_risk,
    audit,
)

__all__ = ["collapse_risk", "min_external_anchor", "lock_fraction", "lock_risk", "audit"]

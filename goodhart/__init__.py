"""goodhart — how gameable is your proxy/metric? Measures Goodhart fidelity decay (a measure becomes
a target and stops measuring) and how many independent metrics restore it. Zero-dependency core."""
from .goodhart import fidelity, metrics_needed, audit

__all__ = ["fidelity", "metrics_needed", "audit"]

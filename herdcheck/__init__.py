"""herdcheck — will your multi-agent system / ensemble herd, or stay wiser than its best member?
Measures the wisdom-of-crowds collapse when agents observe each other's verdicts + the fix.
Zero-dependency core."""
from .herdcheck import ensemble_accuracy, herding_threshold, audit

__all__ = ["ensemble_accuracy", "herding_threshold", "audit"]

"""Agora AI Audit — one reliability report for an AI / agent system. Describe your system; it runs
every matching check (nullcheck, goodhart, selfref, herdcheck, idcheck, ragfresh, mnemo) and returns
a prioritized PASS/WARN/FAIL report with fixes. The self-audit, turned on your system."""
from .aiaudit import audit, format_report

__all__ = ["audit", "format_report"]

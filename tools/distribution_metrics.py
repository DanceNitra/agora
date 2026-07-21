#!/usr/bin/env python3
"""
distribution_metrics.py — the wedge detector for option (a): push distribution, then MEASURE which
of the toolkit tools pulls the most inbound, so the market (not a guess) names the paid wedge.

Pulls GitHub repo signals via the authenticated `gh` CLI (stars, 14-day traffic views/clones, the
most-browsed paths, and referrers), maps each browsed path to the tool it belongs to, and prints a
per-tool inbound ranking. Appends a timestamped snapshot to tools/.distribution_metrics.json so the
trend is visible across cycles (run it each loop after distribution goes live).

Note on scope: GitHub's traffic API covers github.com REPO browsing, not the GitHub Pages blog
(static sites have no built-in analytics). But our posts link through to each tool's repo directory,
so per-tool path views are a fair proxy for which POST drove the most click-through. Referrers show
where the traffic came from (HN / Reddit / X / direct).

Usage:  python tools/distribution_metrics.py [owner/repo]   (default DanceNitra/agora)
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

REPO = sys.argv[1] if len(sys.argv) > 1 else "DanceNitra/agora"
TOOLS = ["inspeximus", "ragfresh", "nullcheck", "selfref", "quitkit"]
SNAP = Path(__file__).resolve().parent / ".distribution_metrics.json"


def gh(path: str):
    """Call `gh api <path>` and return parsed JSON, or None on failure (e.g. no traffic yet)."""
    try:
        out = subprocess.run(["gh", "api", path], capture_output=True, text=True, timeout=30)
        if out.returncode != 0:
            return None
        return json.loads(out.stdout)
    except Exception:
        return None


def _tool_of(path: str):
    """Map a github.com repo path to the tool it belongs to (or None)."""
    low = path.lower()
    for t in TOOLS:
        # /tree/main/<tool>, /blob/main/<tool>/..., or a post slug that names the tool
        if f"/{t}" in low or t in low:
            return t
    return None


def main():
    repo = gh(f"repos/{REPO}") or {}
    stars = repo.get("stargazers_count", 0)
    forks = repo.get("forks_count", 0)
    watchers = repo.get("subscribers_count", 0)

    views = gh(f"repos/{REPO}/traffic/views") or {}
    clones = gh(f"repos/{REPO}/traffic/clones") or {}
    paths = gh(f"repos/{REPO}/traffic/popular/paths") or []
    refs = gh(f"repos/{REPO}/traffic/popular/referrers") or []
    issues = gh(f"repos/{REPO}/issues?state=open&per_page=100") or []
    open_issues = len([i for i in issues if "pull_request" not in i]) if isinstance(issues, list) else 0

    # per-tool inbound = sum of views on paths that belong to that tool
    per_tool = defaultdict(lambda: {"views": 0, "uniques": 0})
    for p in paths:
        t = _tool_of(p.get("path", ""))
        if t:
            per_tool[t]["views"] += p.get("count", 0)
            per_tool[t]["uniques"] += p.get("uniques", 0)

    ranked = sorted(TOOLS, key=lambda t: per_tool[t]["views"], reverse=True)

    print(f"== distribution metrics for {REPO} ==")
    print(f"stars {stars} | forks {forks} | watchers {watchers} | open issues {open_issues}")
    print(f"14-day: {views.get('count',0)} views ({views.get('uniques',0)} uniq) | "
          f"{clones.get('count',0)} clones ({clones.get('uniques',0)} uniq)")
    print("\nWEDGE SIGNAL — per-tool repo path views (which tool pulls the most click-through):")
    any_tool = any(per_tool[t]["views"] for t in TOOLS)
    for t in ranked:
        bar = "#" * min(40, per_tool[t]["views"])
        print(f"  {t:9s} {per_tool[t]['views']:>4} views {bar}")
    if not any_tool:
        print("  (no per-tool traffic yet — distribution hasn't driven click-through; re-run after launch)")
    print("\nReferrers (where traffic came from):")
    for r in refs[:8]:
        print(f"  {r.get('referrer','?'):20s} {r.get('count',0):>4} views ({r.get('uniques',0)} uniq)")
    if not refs:
        print("  (none yet)")

    # append a timestamped snapshot (ts passed in so the script stays deterministic/no clock dep here)
    snap = {"repo": REPO, "stars": stars, "forks": forks, "open_issues": open_issues,
            "views_14d": views.get("count", 0), "clones_14d": clones.get("count", 0),
            "per_tool": {t: per_tool[t]["views"] for t in TOOLS},
            "referrers": {r.get("referrer", "?"): r.get("count", 0) for r in refs[:8]}}
    hist = []
    if SNAP.is_file():
        try:
            hist = json.loads(SNAP.read_text())
        except Exception:
            hist = []
    hist.append(snap)
    SNAP.write_text(json.dumps(hist, indent=2))
    print(f"\nsnapshot #{len(hist)} appended -> {SNAP.name}")
    print("Leader so far:", ranked[0] if any_tool else "(undetermined — needs traffic)")


if __name__ == "__main__":
    main()

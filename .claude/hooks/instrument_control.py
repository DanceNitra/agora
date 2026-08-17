"""A NEGATIVE RESULT IS A CLAIM ABOUT YOUR INSTRUMENT UNTIL A CONTROL SAYS OTHERWISE.

Fires on PostToolUse for Bash. Reads the command and its output, and when the pair has the shape of a
finding that has fooled this operator before, prints the specific control that would settle it.

WHY IT EXISTS, and every rule below is a real failure from 2026-08-17 alone -- twelve of them in one
day, every single one caught by a LATER measurement rather than by care:

  * Two receipt links we had published were reported dead on a 404. A positive control on a file known
    to be present 404'd too: GitHub throttles unauthenticated blob URLs. The links were fine.
  * `grep -n "^import re" file | head -8` reported the import missing. It sits at line 466.
  * A flywheel bucket scored "0 of 3 on-priority" because the probe read `question` while the code
    builds its quest from `origin`.
  * A thread checker returned UNKNOWN for everything because `json` was not imported and the NameError
    landed in its own `except`; it reported "0 not open" and looked clean.
  * Two pytest runs with identical outcomes compared unequal, because the summary string carries the
    elapsed time -- so a SURVIVING mutant was reported as killed.
  * `gh issue view` goes through GraphQL, which was 503 all day; two runs minutes apart disagreed about
    a thread whose state was not in doubt.

The rules are deliberately narrow. A reminder that fires on everything is wallpaper, which is the same
defect one level up -- and this repository has already measured that: 1.5 million identical log lines
made a three-day outage invisible. Each rule below must be able to stay silent.

Contract: read the hook payload on stdin, print at most a few lines, ALWAYS exit 0. This must never be
able to break a session; a guard that takes the tool down is worse than the mistake it prevents.
"""
from __future__ import annotations

import json
import re
import sys

MAX_LINES = 3

# (name, does the COMMAND look like this, does the OUTPUT look like this, what to do instead)
RULES = [
    (
        "absence",
        re.compile(r"\b(grep|rg|find|ls)\b(?!.*\|\s*(wc|sort|uniq|head|tail)\b.*\|)", re.I),
        lambda out: _looks_empty(out),
        "an ABSENCE measured by an uncontrolled instrument. Before reporting it, run the SAME command "
        "against something you KNOW is present; if the control also comes back empty, the instrument "
        "is the finding.",
    ),
    (
        "windowed-search",
        re.compile(r"\b(grep|rg)\b[^|]*\|\s*head\s+-\d+", re.I),
        lambda out: True,
        "a search truncated by `head`: the window can hide the hit and the result reads as absence. "
        "`import re` was once declared missing this way while sitting at line 466. Count first "
        "(`grep -c`), or drop the pipe.",
    ),
    (
        "blob-url",
        re.compile(r"curl[^\n]*github\.com/[^\s]+/blob/", re.I),
        lambda out: True,
        "a github.com/blob URL fetched with curl. Unauthenticated blob requests are throttled and "
        "return 404/503, which is indistinguishable from a deleted file. Use "
        "`gh api repos/OWNER/REPO/contents/PATH?ref=REF` -- it is the authoritative reader.",
    ),
    (
        "graphql-flaky",
        re.compile(r"\bgh\s+(issue|pr)\s+(view|list|create|comment)\b", re.I),
        lambda out: True,
        "`gh issue/pr` goes through GraphQL, which returns 503 under load and makes repeated runs "
        "disagree. For a state you intend to ACT on, prefer REST: "
        "`gh api repos/OWNER/REPO/issues/N`.",
    ),
    (
        "timed-compare",
        re.compile(r"(passed|failed)\s+in\s+[\d.]+s|\bpytest\b[^\n]*==|==[^\n]*\bpytest\b", re.I),
        lambda out: True,
        "comparing a pytest summary as a STRING: it ends in an elapsed time, so two identical outcomes "
        "never compare equal and a surviving mutant reads as killed. Compare the COUNTS.",
    ),
]


def _looks_empty(out: str) -> bool:
    """Empty, or a lone zero, or nothing but whitespace/exit noise."""
    s = (out or "").strip()
    if not s:
        return True
    if re.fullmatch(r"0+", s):
        return True
    lines = [ln for ln in s.splitlines() if ln.strip()]
    return len(lines) == 1 and bool(re.fullmatch(r"\s*0\s*", lines[0]))


def _payload() -> dict:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except Exception:                                                  # noqa: BLE001
        return {}


def _text(v) -> str:
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        for k in ("stdout", "output", "content", "result", "text"):
            if isinstance(v.get(k), str):
                return v[k]
        return json.dumps(v)[:4000]
    if isinstance(v, list):
        return " ".join(_text(x) for x in v[:8])
    return ""


def main() -> int:
    d = _payload()
    if (d.get("tool_name") or d.get("tool") or "") not in ("Bash", "PowerShell"):
        return 0
    ti = d.get("tool_input") or {}
    cmd = ti.get("command") if isinstance(ti, dict) else ""
    out = _text(d.get("tool_response") or d.get("tool_result") or "")
    if not isinstance(cmd, str) or not cmd.strip():
        return 0

    hits = []
    for name, cmd_re, out_ok, advice in RULES:
        try:
            if cmd_re.search(cmd) and out_ok(out):
                hits.append((name, advice))
        except Exception:                                              # noqa: BLE001
            continue
    if not hits:
        return 0
    print("[measure] a result of this shape has fooled us before:")
    for name, advice in hits[:MAX_LINES]:
        print("  * %s -- %s" % (name, advice))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:                                                  # noqa: BLE001
        # Never take the session down. A guard that breaks the tool is worse than the mistake.
        raise SystemExit(0)

"""SessionStart hook: put the outbound procedure in front of every session, including after /compact.

A skill body loads only when it is invoked, and a rule that has to be remembered is lost at the next
compaction. This prints about 150 tokens on every start, resume and compact: the rule, the one
command, and which texts are in flight. It never fails the session.
"""
import os
import subprocess
import sys

root = os.environ.get("CLAUDE_PROJECT_DIR") or os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
lines = [
    "[outbound] Any text that leaves Agora: invoke the `outbound` skill and use tools/outbound.py.",
    "[outbound] Mechanics are scripts (0 tokens). No gate model call and no humanizer: the writing",
    "[outbound] model answers for content (author receipt); owner approves 'posli <6 hex>' on the render;",
    "[outbound] never paste the draft into chat. Compact at ~40% context, not 94%.",
]
try:
    r = subprocess.run([sys.executable, os.path.join(root, "tools", "outbound.py"), "status"],
                       cwd=root, capture_output=True, text=True, timeout=20,
                       encoding="utf-8", errors="replace")
    st = [l for l in (r.stdout or "").splitlines() if l.strip() and not l.startswith("no outbound")]
    if st:
        lines.append("[outbound] in flight:")
        lines += ["  " + l for l in st[:8]]
except Exception:
    pass
print("\n".join(lines))

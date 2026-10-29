"""PreToolUse hook: destructive git and delete commands need a person, or are refused.

WHY. A recursive delete or a hard reset cannot be undone, and an agent runs it with the same
confidence as `ls`. Our own records: a subagent ran `rm -rf` on a guessed path (2026-10-02), and a
plain `git add -A` in the vault staged 376 notes as deletions. The rules existed as prose; prose
did not stop either.

TWO OUTCOMES.
  deny  : the command can destroy data outside the project or rewrites shared history.
  ask   : the command destroys data inside the project. A person confirms it in the prompt.

  deny  git push --force / -f (allowed: --force-with-lease), git reset --hard on a protected
        repo, git add -A/./--all on a protected repo, recursive delete whose target is a drive
        root, the home directory, a bare wildcard, or an absolute path outside SAFE_ROOTS.
  ask   git reset --hard, git clean -f, git checkout -- ., git restore ., git branch -D,
        git stash drop/clear, recursive delete of a path inside the working directory.

CONFIG (environment variables, `;`-separated):
  CC_GUARD_SAFE_ROOTS      absolute folders where recursive delete runs without a prompt
                           (default: the system temp folder).
  CC_GUARD_PROTECTED_REPOS absolute repo folders where reset --hard and add -A are refused.

It fails closed: an unreadable payload blocks the call.
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile

TOOLS = ("Bash", "PowerShell")


def _roots(var: str, default: list[str]) -> list[str]:
    raw = os.environ.get(var)
    items = [p for p in (raw.split(";") if raw else default) if p.strip()]
    return [os.path.normcase(os.path.abspath(os.path.expanduser(p.strip()))) for p in items]


SAFE_ROOTS = _roots("CC_GUARD_SAFE_ROOTS", [tempfile.gettempdir()])
PROTECTED = _roots("CC_GUARD_PROTECTED_REPOS", [])

FORCE_PUSH = re.compile(r"\bgit\b[^\n;&|]*\bpush\b(?![^\n;&|]*--force-with-lease)[^\n;&|]*"
                        r"(\s--force\b|\s-f\b|\s\+\S)", re.I)
ASK_GIT = [
    (re.compile(r"\bgit\b[^\n;&|]*\breset\b[^\n;&|]*--hard\b", re.I), "git reset --hard"),
    (re.compile(r"\bgit\b[^\n;&|]*\bclean\b[^\n;&|]*\s-[a-z]*f", re.I), "git clean -f"),
    (re.compile(r"\bgit\b[^\n;&|]*\bcheckout\b\s+(--\s+)?\.(\s|$)", re.I), "git checkout ."),
    (re.compile(r"\bgit\b[^\n;&|]*\brestore\b[^\n;&|]*\s\.(\s|$)", re.I), "git restore ."),
    (re.compile(r"\bgit\b[^\n;&|]*\bbranch\b[^\n;&|]*\s-D\b"), "git branch -D"),
    (re.compile(r"\bgit\b[^\n;&|]*\bstash\s+(drop|clear)\b", re.I), "git stash drop/clear"),
]
ADD_ALL = re.compile(r"\bgit\b[^\n;&|]*\badd\s+(-A\b|--all\b|\.(\s|$))", re.I)
GIT_C = re.compile(r"\bgit\s+-C\s+(\"[^\"]+\"|'[^']+'|\S+)", re.I)
RM_RF = re.compile(r"(^|[\s;&|(])rm\s+(-[a-zA-Z]*[rR][a-zA-Z]*\s+|--recursive\s+)+(?P<t>[^;&|\n]+)")
RM_ITEM = re.compile(r"\b(Remove-Item|rd|rmdir)\b(?=[^;\n|]*(-Recurse\b|/s\b))(?P<t>[^;\n|]+)", re.I)


def _targets(fragment: str) -> list[str]:
    out = []
    # One shell word may mix quoted and bare parts ("$S"/*), so glue them before judging.
    for tok in re.findall(r"(?:\"[^\"]*\"|'[^']*'|[^\s\"'])+", fragment):
        tok = tok.replace("\"", "").replace("'", "")
        if not tok or tok.startswith("-") or tok.lower() in ("/s", "/q"):
            continue
        out.append(tok)
    return out


SHELLS = re.compile(r"(^|[\s;&|(])(bash|sh|zsh|pwsh|powershell)(\.exe)?\b[^\n]*<<", re.I)
HEREDOC = re.compile(r"<<-?\s*(['\"]?)(?P<tag>[A-Za-z_][A-Za-z0-9_]*)\1[^\n]*\n(?P<body>.*?)\n\s*(?P=tag)\s*(\n|$)",
                     re.S)


def strip_heredocs(command: str) -> str:
    """Drop heredoc bodies that are DATA (a commit message, a Python script, a file being
    written). Text inside them is not run by the shell, and matching it caused most false
    positives on 71,941 replayed commands. A heredoc fed to a shell keeps its body."""
    out, pos = [], 0
    for m in HEREDOC.finditer(command):
        line_start = command.rfind("\n", 0, m.start()) + 1
        if SHELLS.search(command[line_start:m.start() + 2]):
            continue
        out.append(command[pos:m.start("body")])
        pos = m.end("body")
    out.append(command[pos:])
    return "".join(out)


SYSTEM_DIRS = [os.path.normcase(p) for p in (
    os.environ.get("SystemRoot", r"C:\Windows"), os.environ.get("ProgramFiles", r"C:\Program Files"),
    os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"), "/etc", "/usr", "/bin", "/var", "/boot")]
ASSIGN = re.compile(r"(^|[\s;&|(])(?:export\s+)?(?P<n>[A-Za-z_][A-Za-z0-9_]*)=(?P<v>\"[^\"]*\"|'[^']*'|\$\([^)]*\)|\S+)")
SEGMENT = re.compile(r"&&|\|\||;|\n")
CD = re.compile(r"^\s*(cd|Set-Location|pushd)\s+(?P<d>\"[^\"]+\"|'[^']+'|\S+)\s*$", re.I)


def _resolve_vars(target: str, env: dict[str, str]) -> str | None:
    """Substitute $NAME / ${NAME} assigned earlier in the same command. None when a variable
    stays unknown, because an unknown target cannot be judged safe."""
    def sub(m):
        return env.get(m.group(1) or m.group(2), "\0")
    t = re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)", sub, target)
    return None if "\0" in t else t


def _inside(path: str, roots: list[str]) -> bool:
    p = os.path.normcase(os.path.abspath(path))
    return any(p == r or p.startswith(r.rstrip("\\/") + os.sep) for r in roots)


def _classify_delete(target: str, cwd: str, env: dict[str, str]) -> tuple[str, str] | None:
    resolved = _resolve_vars(target, env)
    if resolved is None:
        return "ask", "recursive delete of a target set by a variable (%s)" % target
    t = os.path.expanduser(resolved)
    if t.startswith("/") and re.match(r"^/[a-z]/", t):          # Git Bash /c/Users -> C:/Users
        t = t[1].upper() + ":" + t[2:]
    if t in ("/*", "~", "/", "..", "~/*") or re.fullmatch(r"[A-Za-z]:[\\/]?\*?", t):
        return "deny", "recursive delete of a root, home or parent folder (%s)" % target
    if t in ("*", ".", "./*"):
        # A bare wildcard means "everything in the current folder"; judge that folder.
        here = os.path.normcase(os.path.abspath(cwd))
        if here == os.path.normcase(os.path.expanduser("~")) or re.fullmatch(r"[a-z]:\\?", here) \
                or here in ("\\", "/"):
            return "deny", "recursive delete of everything in a root or home folder (%s)" % target
        t = cwd
    if re.match(r"^/(etc|usr|bin|sbin|var|boot|lib|opt|sys|proc)(/|$)", t):
        # Checked on the raw path: on Windows abspath turns /usr into C:\usr and misses it.
        return "deny", "recursive delete in a system folder (%s)" % target
    absolute = os.path.isabs(t) or re.match(r"^[A-Za-z]:", t)
    full = os.path.abspath(t if absolute else os.path.join(cwd, t))
    if _inside(full, SAFE_ROOTS):
        return None
    if os.path.normcase(full) == os.path.normcase(os.path.expanduser("~")):
        return "deny", "recursive delete of the home directory"
    if _inside(full, SYSTEM_DIRS):
        return "deny", "recursive delete in a system folder (%s)" % target
    if not _inside(full, [os.path.normcase(os.path.abspath(cwd))]):
        return "ask", "recursive delete outside the working directory (%s)" % target
    return "ask", "recursive delete inside the project (%s)" % target


def check(command: str, cwd: str) -> tuple[str, str] | None:
    command = strip_heredocs(command)
    m = FORCE_PUSH.search(command)
    if m:
        seg = command[m.start():].split("\n")[0]
        if re.search(r"(\s|:)(main|master|trunk|production|release)\b", seg):
            return "deny", "git push --force to a shared branch rewrites history others build on"
        return "ask", "git push --force overwrites the remote branch; --force-with-lease is safer"
    repo = cwd
    m = GIT_C.search(command)
    if m:
        repo = os.path.join(cwd, m.group(1).strip("\"'"))
    protected = _inside(repo, PROTECTED) if PROTECTED else False
    if ADD_ALL.search(command):
        if protected:
            return "deny", "git add -A/./--all in a protected repo; stage named files only"
    for pat, why in ASK_GIT:
        if pat.search(command):
            if protected and "reset" in why:
                return "deny", why + " in a protected repo"
            return "ask", why + " discards work that cannot be recovered"
    # Walk the command segment by segment so `cd X && rm -rf y` and `T=$(mktemp -d); rm -rf $T`
    # are judged against the folder and the value they actually use.
    worst, here, env = None, cwd, {}
    tmp = tempfile.gettempdir()
    for seg in SEGMENT.split(command):
        for m in ASSIGN.finditer(seg):
            v = m.group("v")
            if v.startswith("$(") and "mktemp" in v:
                env[m.group("n")] = os.path.join(tmp, "mktemp")
            elif not v.startswith("$("):
                env[m.group("n")] = v.strip("\"'")
        c = CD.match(seg)
        if c:
            d = _resolve_vars(c.group("d").strip("\"'"), env)
            if d:
                d = os.path.expanduser(d)
                if re.match(r"^/[a-z]/", d):
                    d = d[1].upper() + ":" + d[2:]
                here = d if (os.path.isabs(d) or re.match(r"^[A-Za-z]:", d)) else os.path.join(here, d)
            continue
        for rx in (RM_RF, RM_ITEM):
            for m in rx.finditer(seg):
                for t in _targets(m.group("t")):
                    verdict = _classify_delete(t, here, env)
                    if verdict and (worst is None or verdict[0] == "deny"):
                        worst = verdict
                        if verdict[0] == "deny":
                            return worst
    return worst


def main() -> int:
    try:
        raw = sys.stdin.read()
        d = json.loads(raw) if raw.strip() else {}
    except Exception as e:  # noqa: BLE001
        sys.stderr.write("destructive_guard: could not read the hook payload (%r); blocking.\n" % (e,))
        return 2
    if d.get("tool_name") not in TOOLS:
        return 0
    cmd = str((d.get("tool_input") or {}).get("command") or "")
    verdict = check(cmd, str(d.get("cwd") or os.getcwd()))
    if not verdict:
        return 0
    kind, why = verdict
    if kind == "deny":
        sys.stderr.write("destructive_guard: BLOCKED. " + why + ".\n")
        return 2
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": "ask",
        "permissionDecisionReason": "destructive_guard: " + why + ". Confirm only if intended."}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""mnemo Claude Code plugin — deterministic, no-LLM auto-capture + recall of coding-agent memory.

The top coding-agent memories (Claude-Mem, agentmemory) auto-capture sessions via lifecycle hooks, but they
LLM-summarize on the write path, which loses facts, leaks on erasure, and goes nondeterministic. mnemo does the
same auto-capture with NO LLM: it writes tool events into a deterministic, keyed store, so a corrected fact
(a changed API signature, a renamed symbol, a moved file) SUPERSEDES the stale one and cannot be resurrected
by an echo. Persistent across sessions, provably erasable, zero-dependency.

Dispatch by the hook event on stdin JSON (Claude Code passes {hook_event_name, tool_name, tool_input,
tool_response, cwd, prompt, ...}):
  PostToolUse       -> capture Edit/Write/MultiEdit/Bash deterministically, keyed by file path.
  UserPromptSubmit  -> recall memories relevant to the prompt, print them (Claude Code injects stdout as context).
  SessionStart      -> print a short "what I remember about this project" digest.

Fail-open: any error exits 0 with no output, so the hook never blocks the agent.

Install: see README.md (a settings.json hooks block + `pip install agora-mnemo`). Store lives at
<project>/.mnemo/coding_memory.json — local, inspectable, deletable.
"""
import sys, os, json, hashlib

def _store(cwd):
    from mnemo import Mnemo
    d = os.path.join(cwd or os.getcwd(), ".mnemo")
    os.makedirs(d, exist_ok=True)
    m = Mnemo(path=os.path.join(d, "coding_memory.json"))
    m.echo_guard = True                         # a re-stated stale value cannot resurrect a correction
    return m

def _rel(p, cwd):
    try: return os.path.relpath(p, cwd) if cwd and p else p
    except Exception: return p

def _excerpt(s, n=180):
    s = (s or "").strip().replace("\n", " ")
    return (s[:n] + "…") if len(s) > n else s

def capture(ev):
    cwd = ev.get("cwd") or os.getcwd()
    tool = ev.get("tool_name", "")
    ti = ev.get("tool_input", {}) or {}
    m = _store(cwd)
    if tool in ("Edit", "MultiEdit", "Write"):
        fp = _rel(ti.get("file_path", ""), cwd)
        if not fp:
            return
        # the current content of a file supersedes the old one -> the agent never resurrects a stale version
        new = ti.get("new_string") or ti.get("content") or ""
        m.remember(f"{fp} :: current state -> {_excerpt(new)}", key=f"file:{fp}", object=_excerpt(new, 80),
                   mtype="semantic", tags=["file", "edit"])
    elif tool == "Bash":
        cmd = _excerpt(ti.get("command", ""), 200)
        if cmd:
            # commands are episodic (what was tried), keyed by a hash so identical repeats dedup
            m.remember(f"ran: {cmd}", key=f"cmd:{hashlib.sha1(cmd.encode()).hexdigest()[:10]}",
                       object=cmd[:60], mtype="episodic", tags=["bash"])
    m._save()

def recall(ev):
    q = ev.get("prompt") or ev.get("user_prompt") or ""
    if not q.strip():
        return
    m = _store(ev.get("cwd") or os.getcwd())
    hits = m.recall(q, k=5)
    if not hits:
        return
    lines = "\n".join(f"- {h['text']}" for h in hits)
    print(f"[mnemo] relevant project memory (deterministic, corrections already applied):\n{lines}")

def session_start(ev):
    m = _store(ev.get("cwd") or os.getcwd())
    files = [it for it in getattr(m, "items", []) if "file" in (it.get("tags") or [])
             and it.get("status") != "superseded"][:8]
    if files:
        lines = "\n".join(f"- {it['text']}" for it in files)
        print(f"[mnemo] this project's current known files (latest state only):\n{lines}")

def main():
    try:
        ev = json.load(sys.stdin)
    except Exception:
        return
    try:
        name = ev.get("hook_event_name", "")
        if name == "PostToolUse":
            capture(ev)
        elif name == "UserPromptSubmit":
            recall(ev)
        elif name == "SessionStart":
            session_start(ev)
    except Exception:
        pass                                     # fail-open: never block the agent

if __name__ == "__main__":
    main()

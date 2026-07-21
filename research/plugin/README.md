# inspeximus for Claude Code — deterministic coding memory that never resurrects a stale fact

Persistent memory for Claude Code (and any agent with lifecycle hooks), with one difference from Claude-Mem,
agentmemory, and the rest: **it puts no LLM on the write path.** It auto-captures your session the same way they
do, but into a deterministic, keyed store, so a corrected fact supersedes the stale one and cannot come back.

- **Corrections stick.** You change an API signature, rename a symbol, move a file. inspeximus keeps only the current
  state, keyed by file. Next session the agent recalls the new signature, never the old one. No "it forgot I
  renamed that" and no stale value creeping back in.
- **No LLM on capture.** Others summarize your session with an LLM, which drops facts, is non-reproducible, and
  cannot prove a value was erased. inspeximus writes deterministically: same session, same memory, every time.
- **Provably erasable.** `inspeximus` can delete a secret from every surface and prove it (hash-chain receipt). The
  LLM-summarizing tools leave the value recoverable in their history/vector stores.
- **Zero dependency.** One pip package, no vector DB, no graph DB, no cloud. The store is a local JSON file at
  `<project>/.inspeximus/coding_memory.json` that you can read, grep, or delete.

## Install

```bash
pip install inspeximus
```

Add to your project's `.claude/settings.json` (see `settings.example.json` in this folder):

```json
{
  "hooks": {
    "PostToolUse":      [{ "hooks": [{ "type": "command", "command": "python /path/to/inspeximus_hooks.py" }] }],
    "UserPromptSubmit": [{ "hooks": [{ "type": "command", "command": "python /path/to/inspeximus_hooks.py" }] }],
    "SessionStart":     [{ "hooks": [{ "type": "command", "command": "python /path/to/inspeximus_hooks.py" }] }]
  }
}
```

That is it. PostToolUse captures your edits and commands; UserPromptSubmit injects the relevant, current-state
memory before Claude answers; SessionStart shows what the project already knows.

## The one demo that shows why it is different

```
# 1. Claude edits auth.py:            def authenticate(token): ...
# 2. Claude corrects it later:        def authenticate(token, scope): ...
# 3. Next prompt: "how do I call authenticate?"
#    inspeximus injects ONLY:  auth.py :: current state -> def authenticate(token, scope): ...
#    The superseded one-arg signature is gone. It will not resurrect even if the old line
#    reappears in a diff or a paste (echo_guard blocks it).
```

Run it yourself with the hook script and three JSON events (see the repo tests). A summarizing memory can hand
the agent back the stale signature; a deterministic keyed store cannot.

## What this is NOT

No LLM fact-extraction, no knowledge graph, no cloud sync, no persona modeling. Those are where the other tools
lose facts, leak on deletion, and go non-deterministic. inspeximus stays the correctable, auditable, zero-dependency
substrate underneath your agent. If you want semantic recall, plug in an embedder (optional); the deterministic
default runs anywhere with nothing installed.

## The receipts

inspeximus's integrity claims are measured against live mem0 and Graphiti, published with the harness next to every
number: fidelity under conflict, verifiable forgetting, echo resistance, determinism. See the Agent-Memory
Integrity Benchmark in the main repo.

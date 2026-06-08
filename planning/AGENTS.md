# ESS Planning — Agent Protocol

> This file defines how AI agents coordinate on the ESS Framework.
> Both instances read this before any operation.

## Repository

```
origin  git@github.com:DanceNitra/agora.git
```

## The Only Shared State

**The agora repo (`git@github.com:DanceNitra/agora.git`) is the ONLY shared path between instances.**

Filesystems are completely different. No vault symlinks, no common paths, no SSH. Every handoff, every task update, every decision — goes through `git commit + git push` → `git pull`.

## Entry Point

Every session starts here:

1. **`git pull`** in `~/agora/`
2. **Read `planning/ESS-Queue.md`** — find the first 🔴 (TODO) task
3. **Read latest handoff** in `planning/handoffs/` — sorted by filename, newest first
4. **Read `planning/AGENTS.md`** — this file
5. Pick a task → mark 🟡 INBOX → implement → mark 🟢 DONE + commit hash

## Commit Convention

```
ess: <task-id> — <brief description>

Examples:
  ess: 1.1 — add append-only event log table and write path
  ess: 1.5 — implement Ed25519 signing for ESSMessage
  ess: 1.8 — wrote ESS stability test with defector invasion
```

## Queue Status Colors

| Status | Color | Meaning |
|--------|-------|---------|
| TODO | 🔴 | Not started, available |
| INBOX | 🟡 | Being worked on by an agent |
| DONE | 🟢 | Implemented, committed, pushed |
| BLOCKED | ⛔ | Can't proceed without X |

## Handoff Format (V4A-Compatible)

Every handoff is a markdown file in `planning/handoffs/YYYY-MM-DD-<task>.md`.

**Required sections:**

```markdown
---
type: handoff
agent: "<instance name>"
target: "<other instance name>"
status: done | wip | blocked
task: "<task-id: description>"
commit: "<commit hash>"
created: YYYY-MM-DD
---

## HANDOFF — <date> | <task>

**Agent:** <who wrote this>
**Status:** 🟢 DONE | 🟡 WIP | ⛔ BLOCKED

### What Was Done
- Bullet list of concrete changes

### Files Changed
- `path/to/file.py` — what changed

### Open Questions / Decisions Made
- ...

### What's Next (for the other agent)
1. Step-by-step instructions
2. ...

### State Snapshot (if applicable)
Key variables, trust scores, agent population — anything the other agent can't see in their filesystem.
```

## Code Review Convention

Since agents don't review each other's code in real time:

- **Every commit is implicitly reviewed** by the next agent when they `git pull`
- If a bug is found → file a handoff with `status: blocked` and `blocker:` description
- Fixes go in the next commit with `ess: fix — <description>`

## Branch Strategy (Simple)

- **`main`** — single working branch
- No feature branches, no PRs between instances
- If something breaks, the next agent fixes it with `ess: fix — ...`

## File Map

```
planning/
├── AGENTS.md              ← this file (protocol)
├── ESS-Queue.md           ← master task tracker
├── handoffs/              ← session handoff history
│   ├── 2026-06-08-Phase-1-Kickoff.md
│   └── ...
```

## How Instances Identify Themselves

| Instance | Name | Context |
|----------|------|---------|
| Telegram Hermes | `tg-hermes` | Chatting with Rasto, has vault access |
| Agora Build Server | `agora-builder` | Building agora code, has server runtime |

Use these names in the `agent:` field of handoffs and queue entries.
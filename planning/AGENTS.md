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

## How Instances Identify Themselves

| Instance | Name | Role | Context |
|----------|------|------|---------|
| Telegram Hermes | `tg-hermes` | **PLANNER** — task breakdown, design decisions, handoffs | Has vault access, chats with Rasto |
| Agora Build Server | `agora-builder` | **EXECUTOR** — reads handoffs → implements → commits → pushes | Has agora server runtime |

**Division of labor:**
- `tg-hermes` writes handoffs with precise implementation specs.
- `agora-builder` reads the latest handoff, implements exactly what's specified, commits, pushes, and writes a brief DONE handoff.
- `tg-hermes` reviews the committed code, plans the next task, writes the next handoff.
- Both agents update `ESS-Queue.md` with their commit hashes.

## Handoff Format (V4A-Compatible)

Every handoff is a markdown file in `planning/handoffs/YYYY-MM-DD-<task>.md`.

**Required sections:**

```markdown
---
type: handoff
agent: "tg-hermes | agora-builder"
target: "tg-hermes | agora-builder"
status: planning | ready-for-implementation | done
task: "<task-id: description>"
commit: "<commit hash>"
created: YYYY-MM-DD
---

## HANDOFF — <date> | <task>

**From:** <who wrote this>
**To:** <who should act>
**Status:** 🟢 PLANNING → 🟡 READY → 🟢 DONE

### Spec (for executor)
Exactly what to implement. Files, classes, signatures, logic.

### Test Criteria
How to verify the implementation works.

### What's Next
For the other agent.
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
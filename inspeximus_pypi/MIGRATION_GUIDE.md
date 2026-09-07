# Migrating from mem0 to inspeximus

**Goal:** Move your agent memory from mem0 to inspeximus in under 10 minutes.

## Why migrate?

| | mem0 | inspeximus |
|---|---|---|
| Correction | LLM-based, non-deterministic | Deterministic supersession key |
| Revert | No revert operation | `revert(key)` restores previous value |
| Erasure | Delete, no proof | `forget()` + tamper-evident erasure certificate |
| Poison defense | None | `influence_only=True` corroboration gate |
| Dependencies | LLM + vector DB required | Zero-dependency, one file |
| EU AI Act | No receipts | Tamper-evident write receipts + governance report |

## Step 1: Install

```bash
pip install inspeximus
```

## Step 2: Replace the client

**Before (mem0):**

```python
from mem0 import Memory

m = Memory()
m.add("The sky is blue.", user_id="alice")
result = m.search("what color is the sky?", user_id="alice")
```

**After (inspeximus):**

```python
from inspeximus import Inspeximus

m = Inspeximus("memory.json")
m.remember("The sky is blue.", key="sky", user_id="alice")
result = m.recall("what color is the sky?", where={"user_id": "alice"})
```

## Step 3: Correction

**Before (mem0):** Add a new fact. The old one may still surface.

```python
m.add("The sky is now green.", user_id="alice")
# Old "blue" may still be retrieved
```

**After (inspeximus):** The old value is deterministically retired.

```python
m.remember("The sky is now green.", key="sky", user_id="alice")
# Old "blue" is superseded. Recall returns "green".
```

## Step 4: Revert

**Before (mem0):** No revert operation exists.

**After (inspeximus):**

```python
m.revert("sky")
# Returns to "blue" — the previous value
```

## Step 5: Erasure

**Before (mem0):** Delete without proof.

**After (inspeximus):**

```python
m.forget(ids=["..."])
# Hard-deletes + scrubs from all links + caches
# erasure_certificate() produces a verifiable proof
```

## Step 6: MCP server

**Before (mem0):** Requires hosted API or complex setup.

**After (inspeximus):**

```bash
pip install "mcp[cli]"
curl -O https://raw.githubusercontent.com/DanceNitra/agora/main/inspeximus/inspeximus.py
curl -O https://raw.githubusercontent.com/DanceNitra/agora/main/inspeximus/mcp.py
INSPEXIMUS_PATH=./agent_memory.json python mcp.py
```

Register in Claude Code (`.mcp.json`):

```json
{
  "mcpServers": {
    "inspeximus": {
      "command": "python",
      "args": ["/abs/path/to/inspeximus/mcp.py"],
      "env": { "INSPEXIMUS_PATH": "/abs/path/to/agent_memory.json" }
    }
  }
}
```

## Step 7: Verify

```python
m.verify_writes()  # tamper-evident chain intact
m.governance_report()  # erasure/retention posture
```

## What stays the same

- Your data stays local (JSON file)
- Your agent workflow stays the same
- Your prompts stay the same

## What changes

- Corrections are deterministic, not LLM coin-flips
- You can revert on command
- You can prove erasure
- You can defend against memory poisoning
- You have EU AI Act evidence

## Need help?

Open an issue on [GitHub](https://github.com/DanceNitra/inspeximus) or ask in the [Agora repo](https://github.com/DanceNitra/agora).

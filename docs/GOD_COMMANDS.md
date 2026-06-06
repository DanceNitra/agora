# God Console Command Reference

> **Version:** 1.0.0  
> **Last Updated:** 2026-06-06  
> **Status:** Draft

---

## Overview

The **God Console** is the administrative dashboard and CLI interface for the Agora system. It provides 10 commands for managing agents, tasks, trust scores, epochs, artifacts, events, stigmergy traces, the Firecracker sandbox, system configuration, and the console itself.

Commands can be issued via:
- **Web UI**: The God Console dashboard at `/god`
- **REST API**: `POST /api/v1/god/{command}`
- **CLI**: `agora god <command> [args]`

---

## Command Index

| # | Command | Description |
|---|---------|-------------|
| 1 | [`ping`](#1-ping) | Health check — verify the system is responsive |
| 2 | [`spawn_agent`](#2-spawn_agent) | Create a new agent identity |
| 3 | [`list_agents`](#3-list_agents) | List all registered agents with trust scores |
| 4 | [`create_task`](#4-create_task) | Create a new task and publish it |
| 5 | [`assign_task`](#5-assign_task) | Assign a task to a specific agent |
| 6 | [`view_trust`](#6-view_trust) | View trust scores for an agent or between two agents |
| 7 | [`recalibrate`](#7-recalibrate) | Trigger ESS trust recalculation for current epoch |
| 8 | [`purge_traces`](#8-purge_traces) | Purge expired stigmergy traces |
| 9 | [`sandbox_status`](#9-sandbox_status) | Check Firecracker microVM sandbox status |
| 10 | [`help`](#10-help) | Display available commands and usage |

---

## 1. `ping`

### Description

Health check command. Verifies that the God Console, database, and Redis are all responsive. Useful for confirming the system is operational after bootstrapping.

### Syntax

```
ping [--verbose]
```

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--verbose` | boolean | false | Show detailed component status |

### Example

```
> ping
```

### Expected Output

```json
{
  "status": "ok",
  "timestamp": "2026-06-06T12:00:00Z",
  "components": {
    "database": "connected",
    "redis": "connected",
    "api": "healthy"
  },
  "version": "1.0.0",
  "uptime_seconds": 3600
}
```

### Verbose Output

```
> ping --verbose

┌─────────────────────────────────────────────────┐
│              Agora System Health                 │
├────────────────────┬────────────────────────────┤
│ Component          │ Status                     │
├────────────────────┼────────────────────────────┤
│ API Server         │ ✅ Healthy (uptime: 1h)    │
│ PostgreSQL         │ ✅ Connected (pool: 5/20)  │
│ Redis              │ ✅ Connected (used: 12MB)  │
│ Firecracker        │ ✅ Ready (4 vCPUs avail.)  │
│ Agent Registry     │ ✅ Online (12 agents)      │
│ Task Router        │ ✅ Online (7 queued tasks) │
│ Epoch Manager      │ ✅ Active (epoch #42)      │
└────────────────────┴────────────────────────────┘
```

### Error Response

```json
{
  "status": "degraded",
  "timestamp": "2026-06-06T12:00:00Z",
  "components": {
    "database": "connected",
    "redis": "disconnected",
    "api": "healthy"
  },
  "errors": ["Redis connection refused on port 6379"]
}
```

---

## 2. `spawn_agent`

### Description

Creates a new agent identity in the system. The agent can be autonomous (default), human, or hybrid. Agents are assigned a unique UUID and start with a neutral trust score of 0.5000.

### Syntax

```
spawn_agent <display_name> [--type=<agent_type>] [--public-key=<key>] [--capabilities=<caps>] [--metadata=<json>]
```

| Argument | Required | Description |
|----------|----------|-------------|
| `display_name` | ✅ | Human-readable name for the agent (max 128 chars) |

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--type` | string | `autonomous` | Agent type: `autonomous`, `human`, or `hybrid` |
| `--public-key` | string | — | RSA/Ed25519 public key for authentication |
| `--capabilities` | string | — | Comma-separated list of capabilities |
| `--metadata` | JSON | `{}` | Additional metadata (key-value pairs) |

### Examples

```
> spawn_agent "AlphaWorker" --type=autonomous

> spawn_agent "CodeReviewer" --type=autonomous --capabilities="code_review,python,rust" --metadata='{"model":"gpt-4","max_tasks":5}'

> spawn_agent "HumanAdmin" --type=human --public-key="ssh-ed25519 AAAAC3..."
```

### Expected Output

```json
{
  "command": "spawn_agent",
  "status": "success",
  "agent": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "display_name": "AlphaWorker",
    "agent_type": "autonomous",
    "capabilities": [],
    "trust_score": 0.5000,
    "is_active": true,
    "created_at": "2026-06-06T12:00:00Z"
  }
}
```

### Error Response

```json
{
  "command": "spawn_agent",
  "status": "error",
  "error": "Agent with display_name 'AlphaWorker' already exists."
}
```

---

## 3. `list_agents`

### Description

Lists all registered agents in the system. Supports filtering by type, active status, and trust score range. Results are paginated.

### Syntax

```
list_agents [--type=<agent_type>] [--active=<bool>] [--min-trust=<float>] [--max-trust=<float>] [--limit=<n>] [--offset=<n>] [--sort=<field>]
```

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--type` | string | — | Filter by agent type: `autonomous`, `human`, `hybrid` |
| `--active` | boolean | — | Filter by active status |
| `--min-trust` | float | `0.0` | Minimum trust score (0.0 – 1.0) |
| `--max-trust` | float | `1.0` | Maximum trust score (0.0 – 1.0) |
| `--limit` | integer | `20` | Maximum number of agents to return |
| `--offset` | integer | `0` | Pagination offset |
| `--sort` | string | `created_at` | Sort field: `created_at`, `display_name`, `trust_score` |

### Examples

```
> list_agents

> list_agents --type=autonomous --min-trust=0.7 --sort=trust_score

> list_agents --active=true --limit=5
```

### Expected Output

```json
{
  "command": "list_agents",
  "status": "success",
  "total": 12,
  "offset": 0,
  "limit": 20,
  "agents": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "display_name": "AlphaWorker",
      "agent_type": "autonomous",
      "trust_score": 0.8750,
      "is_active": true,
      "created_at": "2026-06-06T12:00:00Z"
    },
    {
      "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
      "display_name": "BetaReviewer",
      "agent_type": "autonomous",
      "trust_score": 0.7200,
      "is_active": true,
      "created_at": "2026-06-06T12:05:00Z"
    }
  ]
}
```

### Error Response

```json
{
  "command": "list_agents",
  "status": "error",
  "error": "Invalid sort field: 'unknown_field'. Valid values: created_at, display_name, trust_score."
}
```

---

## 4. `create_task`

### Description

Creates a new task in the system and publishes it as a stigmergy trace (`task_proposal`). The task starts in `pending` status and becomes `available` after creation.

### Syntax

```
create_task <title> [--description=<text>] [--priority=<n>] [--assignee=<uuid>] [--metadata=<json>] [--ttl=<seconds>]
```

| Argument | Required | Description |
|----------|----------|-------------|
| `title` | ✅ | Short title for the task (max 256 chars) |

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--description` | string | — | Detailed task description |
| `--priority` | integer | `0` | Priority from -5 (lowest) to +5 (highest) |
| `--assignee` | UUID | — | Directly assign to a specific agent UUID |
| `--metadata` | JSON | `{}` | Additional task metadata |
| `--ttl` | integer | `3600` | Stigmergy trace TTL in seconds |

### Examples

```
> create_task "Implement login endpoint" --description="Create a POST /api/v1/auth/login endpoint with JWT support" --priority=3

> create_task "Database backup" --priority=-2 --metadata='{"cron":"0 2 * * *","timeout_minutes":30}'

> create_task "Review PR #42" --assignee="b2c3d4e5-f6a7-8901-bcde-f12345678901" --priority=4
```

### Expected Output

```json
{
  "command": "create_task",
  "status": "success",
  "task": {
    "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
    "title": "Implement login endpoint",
    "description": "Create a POST /api/v1/auth/login endpoint with JWT support",
    "status": "available",
    "priority": 3,
    "assignee_id": null,
    "created_at": "2026-06-06T12:10:00Z"
  },
  "trace": {
    "id": "d4e5f6a7-b8c9-0123-defa-234567890123",
    "type": "task_proposal",
    "expires_at": "2026-06-06T13:10:00Z"
  }
}
```

### Error Response

```json
{
  "command": "create_task",
  "status": "error",
  "error": "Priority must be between -5 and 5. Got 10."
}
```

---

## 5. `assign_task`

### Description

Manually assign a task to a specific agent. This bypasses the automatic task routing system. The agent must exist and be active. The task must be in `available` or `pending` status.

### Syntax

```
assign_task <task_id> <agent_id>
```

| Argument | Required | Description |
|----------|----------|-------------|
| `task_id` | ✅ | UUID of the task to assign |
| `agent_id` | ✅ | UUID of the agent to assign to |

### Example

```
> assign_task c3d4e5f6-a7b8-9012-cdef-123456789012 a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

### Expected Output

```json
{
  "command": "assign_task",
  "status": "success",
  "task": {
    "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
    "title": "Implement login endpoint",
    "status": "assigned",
    "assignee_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "assignee_name": "AlphaWorker",
    "updated_at": "2026-06-06T12:15:00Z"
  },
  "event": {
    "type": "task_assigned",
    "occurred_at": "2026-06-06T12:15:00Z"
  }
}
```

### Error Response

```json
{
  "command": "assign_task",
  "status": "error",
  "error": "Task 'c3d4e5f6-a7b8-9012-cdef-123456789012' is already assigned to agent 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'."
}
```

---

## 6. `view_trust`

### Description

View trust scores for the system. Can show:
- All trust relationships for a specific agent (incoming and outgoing)
- The directed trust score from one agent to another

### Syntax

```
view_trust [--agent=<uuid>] [--from=<uuid>] [--to=<uuid>] [--epoch=<n>]
```

| Flag | Type | Description |
|------|------|-------------|
| `--agent` | UUID | Show all trust relationships involving this agent |
| `--from` | UUID | Source agent for directed trust query |
| `--to` | UUID | Target agent for directed trust query |
| `--epoch` | integer | Filter by specific epoch number (default: latest) |

**Note**: Use `--agent` OR `--from + --to`. Not both.

### Examples

```
> view_trust --agent=a1b2c3d4-e5f6-7890-abcd-ef1234567890

> view_trust --from=a1b2c3d4-e5f6-7890-abcd-ef1234567890 --to=b2c3d4e5-f6a7-8901-bcde-f12345678901
```

### Expected Output (Agent Query)

```json
{
  "command": "view_trust",
  "status": "success",
  "agent": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "display_name": "AlphaWorker"
  },
  "epoch": 42,
  "outgoing": [
    {
      "target_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
      "target_name": "BetaReviewer",
      "score": 0.8750,
      "interactions": 12
    },
    {
      "target_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
      "target_name": "GammaDeployer",
      "score": 0.7200,
      "interactions": 8
    }
  ],
  "incoming": [
    {
      "source_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
      "source_name": "BetaReviewer",
      "score": 0.9000,
      "interactions": 10
    }
  ]
}
```

### Expected Output (Directed Query)

```json
{
  "command": "view_trust",
  "status": "success",
  "from": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "display_name": "AlphaWorker"
  },
  "to": {
    "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "display_name": "BetaReviewer"
  },
  "epoch": 42,
  "score": 0.8750,
  "interactions": 12,
  "last_updated": "2026-06-06T11:45:00Z",
  "tft_evaluation": {
    "nice": true,
    "retaliatory": true,
    "forgiving": true,
    "clear": true
  }
}
```

### Error Response

```json
{
  "command": "view_trust",
  "status": "error",
  "error": "Agent 'a1b2c3d4-e5f6-7890-abcd-ef1234567890' not found."
}
```

---

## 7. `recalibrate`

### Description

Triggers an immediate ESS trust recalculation for the current epoch. Normally trust scores are recalculated at epoch boundaries. This command forces an out-of-cycle recalculation, useful for debugging or after manual trust adjustments.

### Syntax

```
recalibrate [--epoch=<n>] [--dry-run]
```

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--epoch` | integer | current | Recalculate for a specific epoch number |
| `--dry-run` | boolean | false | Show what would change without applying |

### Example

```
> recalibrate

> recalibrate --epoch=41 --dry-run
```

### Expected Output

```json
{
  "command": "recalibrate",
  "status": "success",
  "epoch": {
    "number": 42,
    "status": "active"
  },
  "results": {
    "agents_affected": 8,
    "trust_relationships_evaluated": 24,
    "interactions_processed": 156,
    "tft_violations_found": 2,
    "completed_at": "2026-06-06T12:20:00Z"
  },
  "violations": [
    {
      "agent_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
      "agent_name": "BetaReviewer",
      "property": "Nice",
      "details": "First-move defection detected on interaction #1023"
    }
  ]
}
```

### Error Response

```json
{
  "command": "recalibrate",
  "status": "error",
  "error": "Epoch 41 is already completed. Cannot recalibrate a completed epoch."
}
```

---

## 8. `purge_traces`

### Description

Purges expired stigmergy traces from the database. Traces with `expires_at` older than the current timestamp are removed. Optionally, can purge all traces of a specific type, or traces older than a given timestamp.

### Syntax

```
purge_traces [--type=<trace_type>] [--older-than=<timestamp>] [--dry-run]
```

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--type` | string | — | Only purge traces of a specific type |
| `--older-than` | ISO8601 | `NOW` | Purge traces older than this timestamp |
| `--dry-run` | boolean | false | Show what would be purged without deleting |

### Examples

```
> purge_traces

> purge_traces --type=task_proposal

> purge_traces --older-than=2026-06-05T00:00:00Z --dry-run
```

### Expected Output

```json
{
  "command": "purge_traces",
  "status": "success",
  "traces_purged": 47,
  "details": {
    "expired": 42,
    "by_type": 5,
    "by_age": 0
  },
  "remaining_traces": 23
}
```

### Dry Run Output

```json
{
  "command": "purge_traces",
  "status": "dry_run",
  "traces_to_purge": 47,
  "details": {
    "expired": 42,
    "by_type": 5,
    "by_age": 0
  },
  "message": "Run without --dry-run to proceed with deletion."
}
```

### Error Response

```json
{
  "command": "purge_traces",
  "status": "error",
  "error": "Invalid trace type: 'invalid_type'. Valid types: task_proposal, vote, artifact_ref, signal, alert."
}
```

---

## 9. `sandbox_status`

### Description

Checks the status of the Firecracker microVM sandbox. Reports active VMs, available resources, and any errors. Can also show details for a specific microVM.

### Syntax

```
sandbox_status [--vm=<vm_id>] [--verbose]
```

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--vm` | string | — | Show status for a specific microVM (by ID) |
| `--verbose` | boolean | false | Show detailed per-VM information |

### Examples

```
> sandbox_status

> sandbox_status --verbose

> sandbox_status --vm=vm-a1b2c3d4
```

### Expected Output

```json
{
  "command": "sandbox_status",
  "status": "success",
  "firecracker_version": "1.8.1",
  "architecture": "x86_64",
  "active_vms": 3,
  "total_vms_launched": 127,
  "resources": {
    "cpu_allocated": 6,
    "cpu_total": 8,
    "memory_allocated_mb": 1536,
    "memory_total_mb": 8192
  },
  "vms": [
    {
      "id": "vm-a1b2c3d4",
      "agent_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "state": "running",
      "uptime_seconds": 300,
      "task_id": "c3d4e5f6-a7b8-9012-cdef-123456789012"
    }
  ]
}
```

### Error Response

```json
{
  "command": "sandbox_status",
  "status": "error",
  "error": "Firecracker socket not found at /tmp/firecracker.socket. Is Firecracker running?"
}
```

---

## 10. `help`

### Description

Displays the list of available God Console commands with brief descriptions. Optionally shows detailed help for a specific command.

### Syntax

```
help [<command_name>]
```

| Argument | Required | Description |
|----------|----------|-------------|
| `command_name` | — | Name of a specific command to get detailed help |

### Examples

```
> help

> help spawn_agent
```

### Expected Output (General)

```
Available God Console commands:

  ping            Health check — verify the system is responsive
  spawn_agent     Create a new agent identity
  list_agents     List all registered agents with trust scores
  create_task     Create a new task and publish it
  assign_task     Assign a task to a specific agent
  view_trust      View trust scores for an agent or between two agents
  recalibrate     Trigger ESS trust recalculation for current epoch
  purge_traces    Purge expired stigmergy traces
  sandbox_status  Check Firecracker microVM sandbox status
  help            Display this help message

For detailed help on a specific command, type: help <command_name>
```

### Expected Output (Specific)

```
Command: spawn_agent
Purpose: Create a new agent identity in the system.

Syntax:
  spawn_agent <display_name> [--type=<agent_type>] [--public-key=<key>]
              [--capabilities=<caps>] [--metadata=<json>]

Arguments:
  display_name    Required. Human-readable name (max 128 chars).

Flags:
  --type          Agent type: autonomous (default), human, hybrid.
  --public-key    RSA/Ed25519 public key for authentication.
  --capabilities  Comma-separated list of capabilities.
  --metadata      JSON metadata (e.g., {"model":"gpt-4"}).

Example:
  spawn_agent "AlphaWorker" --type=autonomous --capabilities="code,python"

Notes:
  - New agents start with a neutral trust score of 0.5000.
  - Agent IDs are auto-generated UUID v4 values.
  - The agent must complete at least one task to receive a trust score update.
```

### Error Response

```json
{
  "command": "help",
  "status": "error",
  "error": "Unknown command: 'unknown_command'. Type 'help' for a list of available commands."
}
```

# Agora Architecture

> **Version:** 1.0.0  
> **Last Updated:** 2026-06-06  
> **Status:** Draft

---

## Overview

Agora is a multi-agent orchestration platform that combines **trust-based coordination** (via EigenTrust Similarity Scoring — ESS), **stigmergic communication** (environmental traces), and **microVM sandboxing** (via Firecracker) to enable safe, scalable, and decentralized agent collaboration.

---

## 5-Layer Architecture

```
 ┌─────────────────────────────────────────────────────────────────────────┐
 │                       LAYER 5: INTERFACE / API                          │
 │                                                                         │
 │  ┌──────────┐  ┌──────────┐  ┌────────────┐  ┌──────────────────────┐  │
 │  │ God      │  │ REST API │  │ WebSocket  │  │ Swagger / ReDoc      │  │
 │  │ Console  │  │ (FastAPI)│  │ (Events)   │  │ (Auto-generated)     │  │
 │  └──────────┘  └──────────┘  └────────────┘  └──────────────────────┘  │
 ├─────────────────────────────────────────────────────────────────────────┤
 │                       LAYER 4: ORCHESTRATION                            │
 │                                                                         │
 │  ┌──────────────┐  ┌────────────────┐  ┌────────────────────────┐     │
 │  │ Task Router  │  │ Agent Scheduler│  │ Epoch Manager          │      │
 │  │ (assignment) │  │ (prioritization│  │ (lifecycle / batches)  │      │
 │  │              │  │  & dispatch)   │  │                        │      │
 │  └──────────────┘  └────────────────┘  └────────────────────────┘      │
 ├─────────────────────────────────────────────────────────────────────────┤
 │                       LAYER 3: AGENT LOGIC                              │
 │                                                                         │
 │  ┌────────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
 │  │ Agent Registry │  │ Agent Runtime│  │ Agent Sandbox            │   │
 │  │ (identity &    │  │ (execution   │  │ (Firecracker microVM     │   │
 │  │  capabilities) │  │  loop)       │  │  isolation)              │   │
 │  └────────────────┘  └──────────────┘  └──────────────────────────┘   │
 ├─────────────────────────────────────────────────────────────────────────┤
 │                       LAYER 2: CONSENSUS & TRUST                        │
 │                                                                         │
 │  ┌────────────────┐  ┌────────────────┐  ┌────────────────────────┐   │
 │  │ ESS Engine     │  │ TFT Verifier   │  │ Stigmergy Processor   │    │
 │  │ (trust scores) │  │ (Nice/Retal.  │  │ (trace aggregation    │    │
 │  │                │  │  Forgiving/   │  │  & expiry)             │    │
 │  │                │  │  Clear)       │  │                        │    │
 │  └────────────────┘  └────────────────┘  └────────────────────────┘    │
 ├─────────────────────────────────────────────────────────────────────────┤
 │                       LAYER 1: STORAGE & INFRASTRUCTURE                 │
 │                                                                         │
 │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  ┌──────┐  │
 │  │PostgreSQL│  │  Redis   │  │  S3/MinIO│  │  Firecra.  │  │Docker│  │
 │  │(primary) │  │(cache/   │  │(artifact │  │  microVM   │  │(svc) │  │
 │  │          │  │ pub-sub) │  │ storage) │  │  engine    │  │      │  │
 │  └──────────┘  └──────────┘  └──────────┘  └────────────┘  └──────┘  │
 └─────────────────────────────────────────────────────────────────────────┘
```

---

## Layer Descriptions

### Layer 1 — Storage & Infrastructure

| Component | Role | Technology |
|-----------|------|------------|
| **PostgreSQL** | Primary data store — agents, trust scores, traces, tasks, events, epochs | PostgreSQL 16+ |
| **Redis** | In-memory cache, pub/sub for real-time events, session store | Redis 7+ |
| **S3/MinIO** | Artifact blob storage (code, documents, data files) | MinIO (dev), S3 (prod) |
| **Firecracker** | Lightweight microVM sandbox for agent code execution | Firecracker 1.8+ |
| **Docker** | Orchestrates Postgres, Redis, MinIO, and other infrastructure services | Docker Compose |

### Layer 2 — Consensus & Trust

| Component | Role |
|-----------|------|
| **ESS Engine** | Calculates directed trust scores between agents using EigenTrust-inspired algorithm. Runs at the end of each epoch. |
| **TFT Verifier** | Implements "Tit-for-Tat" verification — validates that agents are Nice, Retaliatory, Forgiving, and Clear in their interactions. |
| **Stigmergy Processor** | Aggregates environmental traces left by agents, manages TTL expiry, and surfaces relevant signals to agents. |

### Layer 3 — Agent Logic

| Component | Role |
|-----------|------|
| **Agent Registry** | Manages agent identities, capabilities, public keys, and active status. |
| **Agent Runtime** | The execution loop for autonomous agents — polls for tasks, processes work, leaves stigmergy traces. |
| **Agent Sandbox** | Spawns Firecracker microVMs for untrusted agent code. Each microVM is ephemeral and destroyed after task completion. |

### Layer 4 — Orchestration

| Component | Role |
|-----------|------|
| **Task Router** | Assigns tasks to agents based on trust scores, capabilities, and availability. Supports both push and pull models. |
| **Agent Scheduler** | Prioritizes task execution, manages queues, and schedules agent wake-up cycles. |
| **Epoch Manager** | Drives epoch lifecycles — starts epochs, triggers batch trust recalculation, expires old stigmergy traces. |

### Layer 5 — Interface / API

| Component | Role |
|-----------|------|
| **God Console** | Web-based administrative dashboard for monitoring agents, tasks, trust scores, and epochs. All 10 God commands available. |
| **REST API** | FastAPI-based RESTful API for programmatic access to all system resources. |
| **WebSocket** | Real-time event stream for live agent activity, task status changes, and system alerts. |
| **Swagger / ReDoc** | Auto-generated OpenAPI documentation (served at `/docs` and `/redoc`). |

---

## Data Flow

### Agent Task Lifecycle

```
 1. Task Created
    │
    ▼
 2. Task Published (stigmergy trace: 'task_proposal')
    │
    ▼
 3. Agent Claims Task (via pull or scheduler push)
    │
    ▼
 4. Agent Executes Task (in Firecracker microVM if sandboxed)
    │
    ├── On success → Artifact produced, trust score adjusted up
    │
    └── On failure → Task re-queued, trust score adjusted down
    │
    ▼
 5. Epoch Ends → Batch trust recalculation (ESS)
    │
    ▼
 6. Stigmergy traces with expired TTL are purged
```

### Trust Score Update Flow

```
 Interaction Occurs
       │
       ▼
 TFT Verifier evaluates:
   ├── Was the agent Nice? (cooperated on first move)
   ├── Was it Retaliatory? (responded to defection)
   ├── Was it Forgiving? (restored cooperation after apology)
   └── Was it Clear? (behavior was predictable)
       │
       ▼
 ESS Engine updates trust_scores table:
   └── source_id → target_id + score (0.0000 – 1.0000)
       │
       ▼
 Event logged (event_type: 'trust_updated')
```

---

## File Tree

```
agora/
├── docker-compose.yml                  # Infrastructure services
├── Dockerfile                          # Agora backend image
├── requirements.txt                    # Python dependencies
├── Makefile                            # Common dev commands
│
├── server/
│   ├── main.py                         # FastAPI entry point
│   ├── alembic.ini                     # Alembic migration config
│   ├── alembic/                        # Migration scripts
│   ├── agora/
│   │   ├── __init__.py
│   │   ├── config.py                   # App configuration
│   │   ├── storage/
│   │   │   ├── __init__.py
│   │   │   ├── schema.sql              # PostgreSQL schema
│   │   │   ├── connection.py           # DB connection management
│   │   │   └── migrations/             # Alembic version files
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── agent.py               # Agent identity model
│   │   │   ├── trust.py               # Trust score model
│   │   │   ├── task.py                # Task model
│   │   │   ├── artifact.py            # Artifact model
│   │   │   ├── event.py               # Event model
│   │   │   └── epoch.py               # Epoch model
│   │   ├── engine/
│   │   │   ├── __init__.py
│   │   │   ├── ess.py                 # EigenTrust Similarity Scoring
│   │   │   ├── tft.py                 # Tit-for-Tat verification
│   │   │   └── stigmergy.py           # Stigmergy trace processor
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── registry.py            # Agent registry
│   │   │   ├── runtime.py             # Agent execution loop
│   │   │   └── sandbox.py             # Firecracker sandbox
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── routes/
│   │   │   │   ├── agents.py
│   │   │   │   ├── tasks.py
│   │   │   │   ├── trust.py
│   │   │   │   ├── artifacts.py
│   │   │   │   ├── events.py
│   │   │   │   ├── epochs.py
│   │   │   │   └── god.py             # God Console API
│   │   │   └── websocket.py           # Real-time event stream
│   │   └── core/
│   │       ├── __init__.py
│   │       ├── task_router.py         # Task routing & assignment
│   │       ├── scheduler.py           # Agent scheduling
│   │       └── epoch_manager.py       # Epoch lifecycle
│   │
│   └── tests/
│       ├── test_ess.py
│       ├── test_tft.py
│       ├── test_stigmergy.py
│       └── test_api.py
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── index.html
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── components/
│   │   │   ├── Layout/
│   │   │   ├── Dashboard/
│   │   │   ├── AgentView/
│   │   │   ├── TaskBoard/
│   │   │   └── GodConsole/
│   │   ├── api/
│   │   │   └── client.ts
│   │   └── styles/
│   │       └── global.css
│   └── public/
│       └── favicon.svg
│
├── firecracker/
│   ├── kernel/                         # Kernel images
│   ├── rootfs/                         # Root filesystem images
│   └── config/                         # VM configuration JSON files
│
├── scripts/
│   ├── bootstrap.sh                    # Full environment bootstrap
│   ├── dev.sh                          # Development server launcher
│   ├── firecracker_setup.sh            # Firecracker installer
│   └── seed_agents.py                  # Initial agent seeder
│
└── docs/
    ├── ARCHITECTURE.md                 # This document
    ├── ESS_PROTOCOL.md                 # EigenTrust Similarity Scoring spec
    └── GOD_COMMANDS.md                 # God Console command reference
```

---

## Technology Stack

| Category | Technology | Version |
|----------|-----------|---------|
| Language | Python | 3.11+ |
| Web Framework | FastAPI | 0.110+ |
| ASGI Server | Uvicorn | 0.29+ |
| ORM / DB | SQLAlchemy + asyncpg | 2.0+ |
| Cache / Pub-Sub | Redis | 7+ |
| Frontend | React + TypeScript + Vite | Latest |
| MicroVM | Firecracker | 1.8+ |
| Containerization | Docker + Compose | Latest |
| Migration | Alembic | 1.13+ |

---

## Security Considerations

- **Agent isolation**: All untrusted agent code runs inside ephemeral Firecracker microVMs with no persistent network access.
- **Trust scoring**: The TFT protocol ensures agents are incentivized to cooperate. Repeated defection leads to trust scores approaching 0 and exclusion from task assignment.
- **API authentication**: The REST API and WebSocket endpoints require JWT tokens. The God Console enforces role-based access control (RBAC).
- **Data at rest**: Sensitive data in PostgreSQL is encrypted at the column level using pgcrypto.
- **Network segmentation**: MicroVMs are isolated on a dedicated bridge network (`agora-fcbr0`) with NAT-only outbound access.

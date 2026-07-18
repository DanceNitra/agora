# mnemo gap → build plan: dominate every top-10 agent-memory product

> From a feature-gap analysis (2026-07-18) of the top-10 star-ranked systems in Awesome-Agent-Memory
> (1 Claude-Mem · 2 Mem0 · 3 Zep/Graphiti · 4 Cognee · 5 gbrain · 6 agentmemory · 7 Letta · 8 Context Mode ·
> 9 Hindsight · 10 Second Me), each compared to mnemo. Goal: build the CONVENIENCE features they have, while
> keeping mnemo's unique moat (deterministic corrections, verifiable forgetting, poisoning defense, zero-dep,
> auditability) that NONE of them have. Result = the only memory that is BOTH as convenient AND has the integrity moat.

## The convergent gaps (what the leaders have, mnemo lacks) — compatible with our principles

| gap | who has it | compatible with mnemo (zero-dep / deterministic / no-LLM-on-write)? | priority |
|---|---|---|---|
| **Automatic lifecycle-hook capture** (no manual `remember()`) | **Claude-Mem #1, agentmemory #6** (both top coding-agent memories) | ✅ hooks call mnemo's deterministic write API, no LLM | **1 (the wedge)** |
| **First-class hybrid recall** (semantic + BM25 + RRF + proximity/fuzzy) | ALL of them (Claude-Mem, Context-Mode, gbrain, agentmemory, Hindsight) | ✅ BM25/RRF is pure-algorithmic zero-dep; promote the embedder hook to first-class | **2** |
| **Zero-LLM entity-link / lightweight graph + multi-hop** | **gbrain #5** (self-wiring, ZERO-LLM extraction), agentmemory, Hindsight | ✅ gbrain proves a deterministic no-LLM graph is possible; mnemo already has bitemporal as_of | **3** |
| **Read-only local viewer dashboard** | Claude-Mem, agentmemory (:3113), gbrain | ✅ single static file over the store, read-only | **4** |
| **REST wrapper + broad integration matrix** | agentmemory (20+), Context-Mode (17 IDEs) | ✅ thin wrapper; distribution not architecture | **4** |
| **Published LongMemEval / LoCoMo recall number** | Hindsight (SOTA, Virginia-Tech-verified), agentmemory (95% recall@5) | ✅ once hybrid recall is first-class, publish honestly | **3** |
| **Pre-compaction snapshot hook** | Context-Mode | ✅ deterministic state-save | 4 |

## DECLINE (would break the moat — off-path optional at most)
- **LLM summarization / fact-extraction on the write path** (Claude-Mem, Hindsight, Cognee, mem0). This is the exact
  thing that makes them lose facts + leak on erasure + go nondeterministic (see DOMINATION_MATRIX). Never on the
  correction path; only as an OPTIONAL off-path async add-on.
- **Persona modeling / per-user fine-tuning / P2P network / consumer UI** (Second Me #10). Different product
  category, inherently LLM-heavy and non-deterministic. Do not chase.
- **Hosted SaaS / cloud sync** — defer to the paid tier; keep the core local.

## The build sequence

**Phase 1 — the coding-agent wedge (dominates Claude-Mem #1 + agentmemory #6 where it matters).**
Ship an mnemo Claude-Code plugin: lifecycle hooks (SessionStart / PostToolUse / Stop / SessionEnd) that
auto-capture tool events into mnemo's deterministic store, `claude mcp add` one-liner, `<private>` redaction.
mnemo then matches their convenience AND adds what they cannot: corrections that stick, verifiable forgetting,
poisoning defense, zero-dep. This is the killer positioning: "the coding-agent memory that never resurrects a
stale API signature and can prove a secret was erased."

**Phase 2 — recall parity (removes their only real edge).**
Promote the embedder to first-class HYBRID recall (semantic + BM25 + RRF + proximity + fuzzy), all deterministic,
zero-dep default. Then publish an honest LongMemEval/LoCoMo number. This closes the one axis where they beat us
(recall quality) while we keep the integrity axes where they lose.

**Phase 3 — UX + graph + reach.**
Read-only local viewer (single HTML over the store), a zero-LLM entity-link layer for multi-hop (gbrain's proof
that this needs no LLM), a thin REST wrapper, and the broad install matrix.

## The domination thesis (one line)
mnemo builds every convenience the top-10 have (auto-capture, hybrid recall, viewer, graph) using ONLY
zero-dep/deterministic/no-LLM-on-write methods, so it ends up the single system that is as easy as Claude-Mem
AND the only one that passes the integrity benchmark (corrections stick, verifiable erasure, poisoning defense,
determinism) — the axes every one of them fails. Convenience parity + an integrity moat nobody else can match.

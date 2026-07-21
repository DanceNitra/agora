# inspeximus build plan — what to build next (evidence-backed)

> Fixed 2026-07-17 from a 4-lens research gate (benchmark landscape · competitor features · market demand ·
> adjacent opportunities), each with web/brave search, + our own archive/GitHub. Metric-triggered, not dated.

## The one finding all four lenses agree on

**The market has re-framed agent memory AWAY from retrieval, TOWARD integrity / forgetting / provenance —
inspeximus's exact lane.** Zep, Oracle, OWASP, and multiple 2026 papers all say "RAG/save-everything is the wrong
default; forgetting and correctness are the frontier." Independent academic validation of our thesis:
**arXiv:2606.01435 "Don't Ask the LLM to Track Freshness: A Deterministic Recipe for Memory Conflict
Resolution."** The loudest production complaint is literally inspeximus's center: *corrections don't stick / stale
values resurrect* ("vegetarian-vegan problem", "100% relapse when corrected in-chat"). The risk is not demand —
it's that MemGuard/mguard (detection) and Zep/Graphiti (bitemporal) are racing into the same gap. inspeximus's edge:
**correction-integrity + tamper-evident governance in one zero-dependency, MCP-native, auditable file.**

Archive note: the two apparent "gaps" (semantic recall, fact extraction) are HALF-BUILT — `embed=` and
`store.extractor` hooks already exist in the core; and we have a large probe library (locomo_*, membench_*,
integrity_bench_*, forget_verification_bench, memorygraft_defense_probe, agentpoison_influence_gate) that is the
raw material for the harnesses below.

## DO NOT BUILD (all four lenses agree — don't become a worse mem0)

- **LLM fact extraction from raw conversation** — hot-path LLM, breaks zero-dependency; mem0/Supermemory own it.
- **Temporal knowledge graph / entity-relationship memory** — Zep/Graphiti/Cognee's server-backed moat.
- **Hosted/managed SaaS with SOC2/HIPAA** — scale/servers/audits we can't staff solo (owner already parked).
- **Test-time / procedural / skill memory** — hot but high-effort, wrong architecture for a single MIT file.

## THE PLAN — three pillars, sequenced by credibility-per-effort

### PILLAR 1 — Ship numbers where incumbents score single digits (credibility → distribution)
The field competes on public benchmark numbers; inspeximus has none. These are boards where everyone FAILS on OUR axis.

1. **MemoryAgentBench Conflict Resolution — official-harness number vs the published leaderboard.** (LOW effort,
   HIGHEST ROI.) On FactConsolidation: mem0 **18%**, Zep/Graphiti **7%**, multi-hop ALL **<7%**; inspeximus's
   deterministic key-supersession wins single-hop by construction. We already built the probe
   (`bench/memoryagentbench_cr.py`); the earlier stress-claim gate KILLED the naive-vs-inspeximus framing as
   textbook + pool-size-confounded — the FIX is to run inspeximus through the OFFICIAL MAB harness (their gpt-4o
   judge, their task) and report inspeximus's CR score NEXT TO the published incumbent numbers. No naive strawman =
   the confound the gate flagged is gone. → gated flagship post ("inspeximus N% where mem0 18% / Zep 7%").
2. **Memory-poisoning defense number.** (LOW effort — mostly a harness.) OWASP added **ASI06: Memory Poisoning**
   to the 2026 Agentic Top 10; ">90% of tested agents vulnerable", "existing defenses largely ineffective". Run
   inspeximus's warrant-gate + Ed25519 corroboration as a DEFENSE on an ASB/MemEvoBench-style attack and report
   ASR-reduction. We have `memorygraft_defense_probe.py` + `agentpoison_influence_gate.py`. Pure integrity
   story, our moat, a rare strong number on a board where defenders lose.

### PILLAR 2 — The coding-agent wedge (fastest distribution; we already have the mechanism)
3. **Correction-integrity memory MCP server for Claude Code / Cursor / Cline.** (LOW-MED effort.) Claude Code
   issue #14227 ("every session starts from zero", CLAUDE.md goes stale) was closed **"not planned"** → a large,
   paying, frustrated, vendor-abandoned audience filling the gap with third-party MCP servers. We SHIP an MCP
   server. The unserved need that capture-and-retrieve tools (claude-mem, CodeMem, agentmemory) ALL miss: *"the
   refactor superseded the old API signature — don't resurrect it."* Deterministic supersession + echo_guard =
   exactly this, and a coder trusts a rule, not a probability. Smallest move: wrap `mcp.py` as a
   coding-memory server + a demo README ("agent refactors an API; inspeximus blocks the stale signature from coming
   back") + the 60-second `claude mcp add` path we already ship.

### PILLAR 3 — The governance / Article-12 layer (best margin, deadline-forced, underserved — the monetization seed)
4. **"Agent Memory Article-12 / right-to-be-forgotten" conformance layer.** (LOW-MED effort; this IS the $29
   inspeximus-pro governance module from the branding roadmap, now market-validated.) EU AI Act **Article 12**
   record-keeping enforces **2 Aug 2026** (fines to 7% revenue); "GDPR says delete, EU AI Act says keep";
   tamper-evidence "strongly advisable"; NO vendor sells an agent-memory-specific Article-12 + erasure layer.
   inspeximus ALREADY has the primitives: tamper-evident hash-chain receipts, provable cross-store erasure,
   bitemporal audit — deterministic (auditable, unlike LLM-judge detectors like MemGuard). Smallest move: a
   one-page "Agent Memory Article-12 conformance" mapping + a runnable demo (inspeximus emits the tamper-evident
   event log and executes a provable `forget(subject)` across stores), positioned as the audit/erasure layer
   UNDER any memory system (Mem0, Letta, LangGraph). Ties directly to [[inspeximus-branding-roadmap]] Stage-1 revenue.

### PILLAR-adjacent (MEDIUM effort; finish the half-built hooks, then more boards open)
5. **Wire a real optional embedder recipe + semantic dedup/consolidation** (the `embed=` hook exists; upgrade
   consolidation from lexical to semantic near-duplicate merge — stays zero-dep-core). THEN LongMemEval/LoCoMo
   numbers (the market-standard board where Hindsight got 91.4% PR) become postable.
6. **Multi-hop supersession resolver** — FactConsolidation multi-hop, where ALL SOTA <7% (an open scoreboard).

## Recommended immediate order
**1 → 2 → 3** (all low-effort, all "where incumbents fail", all our moat), then **4** as the monetization move
once a first inbound lands, then **5/6**. Every item reuses shipped inspeximus mechanisms or existing probes; none is
a from-scratch product. Each gated (validate→storm→audit→verify) before any number/post goes out. Sources: the
4 lens transcripts (this session, 2026-07-17).

# Fresh web scan — 2026-06-28 (Tavily + Brave + HF + Crossref + Reddit)

Sources firing: HF papers (5/q), Crossref (5/q), Tavily (5/q), Brave (4-5/q), Reddit (5/q). Wikipedia SSL-fail + S2 429 (fail-soft, ignored). ~24-25 deduped hits/query.

## A. Agent-memory benchmark space is CROWDING (RAMR competitive landscape)
- **MemoryArena** (HF 2602.16313) — agent memory in interdependent multi-session tasks.
- **AMA-Bench** (2602.22769) — long-horizon memory for agentic apps.
- **MEMTRACK** (2510.01353) — long-term memory + state tracking, multi-platform.
- **Anatomy of Agentic Memory: Taxonomy + Empirical Analysis** (2602.19320) — survey of eval/system LIMITATIONS (read this — maps the field, may cite RAMR-adjacent gaps).
- **Memory for Autonomous LLM Agents** survey (2603.07670).
- => RAMR's edge holds (contamination-resistant + 9 mechanism-isolating metrics), but we should position against these explicitly. ACTION: read "Anatomy of Agentic Memory" for the gap RAMR uniquely fills.

## B. Crucible-fit leads (FAILED is a live possibility — engage our RAG-dead post)
- **"When Context Overwhelms: Long-Context vs Retrieval-Based QA Under Noise"** (Crossref 2026, doi 10.33774/coe-2026-tvxc6) — directly on our turf.
- **"Does RAG Really Perform Bad For Long-Context Processing?"** (HF 2502.11444) — CONTRARIAN to our context-rot finding; replication/comparison = Crucible gold.
- **SuperLocalMemory: Bayesian Trust Defense Against Memory Poisoning** (SSRN 6273819) — direct neighbor to mnemo's corroboration gate; cite or replicate.
- **Temporal Dynamics of Memory Poisoning** (IEEE Access 2026) + **A-MemGuard** (2510.02373) + **AgentSys** (2602.07398) — the poisoning-defense conversation mnemo lives in.

## C. FLAGSHIP prior-art check — "conservatism is normative under meta-uncertainty"
**RESULT: the abstract decision-theory framing is TEXTBOOK — re-derivation trap.**
- Crossref surfaced **Maxmin Expected Utility** (Gilboa-Schmeidler 1989) directly. The claim "under model/parameter uncertainty (ambiguity), the normative choice is the worst-case-robust / conservative one" IS maxmin EU + ambiguity aversion + Hansen-Sargent robust control. Known since 1989. Per CLAUDE.md rule 10, do NOT ship this as a discovery.

**BUT there is a FRESH, severe-testable, on-frontier-models lane (Feb 2026 cluster):**
- **Agentic Uncertainty Reveals Agentic Overconfidence** (2602.06948) — can agents predict their own success? (they're overconfident).
- **The Confidence Dichotomy: Miscalibration in Tool-Use Agents** (2601.07264).
- **Agentic Confidence Calibration** (2601.15778).
- **Kalshibench: do LLMs know what they don't know** (2512.16030).

### Recommended flagship reframe (original + falsifiable + on real systems)
Not the theorem (known). Instead the EMPIRICAL question the field is circling but hasn't pinned with a runnable normative test:
> **"The overconfidence tax": do real frontier agents systematically UNDER-apply conservatism, and how much outcome do they lose by it?**
Measure, on a real agentic task with a verifiable outcome: (1) each agent's optimal abstain/hedge threshold under its OWN self-estimated success probability (the maxmin-EU-rational policy), (2) the policy the agent actually follows, (3) the utility gap. Falsifier: if agents already hedge at ~the rational threshold (gap ~0), the "overconfidence tax" is folklore. Ties directly to mnemo (corroboration gate = conservatism over an uncertain fact), RAMR's ABSTENTION metric, and the Grounding Meter (confident-wrongness). Lab baseline measurable in-cycle (severe-test rule satisfiable).

## GitHub scout: stale (last scan 2026-06-23). Web scan above is the fresh discovery surface this cycle.

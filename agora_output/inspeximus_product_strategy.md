# inspeximus → #1 agent-memory product — capability & strategy sketch

> Drafted 2026-07-17 from a 5-lens market scan (competitive teardown · product/cyber security threat model ·
> branding/category · distribution · monetization), cross-referenced against inspeximus's actual shipped API surface
> and the MemoryAgentBench Conflict-Resolution diagnostic. Goal (owner): be the best product on the market on
> EVERY axis, then let the income pillars sit on top. This is an internal build map, not an outward post.
> Every number here is gated (validate→storm→audit→verify) before it goes outward.

---

## 0. North Star

**Category we lead: "the memory-integrity layer for AI agents." Tagline verb: "self-correcting."**
One line: *inspeximus — the self-correcting memory layer for AI agents. Memory your agent can audit.*

The whole field is architecturally split and **nobody owns correctness**: mem0 = preference recall, Zep =
temporal graph, Letta = runtime, Cognee = ontology, Supermemory = multimodal API. Every one of them resolves
conflicts with an LLM coin-flip (the public mem0-vs-Zep LoCoMo war — 84% → 58.44% → 75.14% — is proof the
field's numbers are non-reproducible). inspeximus's edge is the axis they all fake: **deterministic, auditable,
attack-resistant correctness**, in one zero-dependency MCP-native file.

---

## 1. Where the whole field slacks (the ownable gaps)

Feature matrix from the teardown (H=has, ~=partial, —=none):

| Capability | mem0 | Zep | Letta | Cognee | Supermem | Redis | **inspeximus** |
|---|---|---|---|---|---|---|---|
| Deterministic correction | — | ~ | — | — | — | — | **H** |
| Bitemporal / as_of | — | H | — | ~ | — | — | **H** |
| Safe forget + verify erasure | — | ~ | — | — | — | ~ | **H** |
| Built-in poisoning defense | — | — | — | — | — | — | **H** |
| Signed provenance (Ed25519) | — | — | — | — | — | — | **H** |
| Tamper-evident receipts | — | — | — | — | — | — | **H** |
| Fail-closed multi-tenant | ~ | ~ | ~ | — | ~ | ~ | **H** |
| Zero-dependency | — | — | — | — | — | — | **H** |
| MCP-native | ~ | ~ | ~ | — | ~ | H | **H** |
| Graph / multi-hop reasoning | ~($) | H | ~ | H | H | ~ | **—** |

**Top-5 ownable gaps** (underserved × inspeximus-fit): (1) deterministic reproducible correction, (2) built-in
poisoning/integrity defense (field ships ZERO; MINJA >70% ASR unaddressed), (3) verifiable forgetting +
tamper-evident audit (EU-AI-Act/GDPR), (4) fail-closed multi-tenant isolation, (5) zero-dependency (everyone
else drags Neo4j/Postgres/Redis/vector-DB + LLM-on-ingest).
**The one thing we LACK:** temporal-KG / multi-hop entity reasoning (Zep/Cognee) + multimodal ingest
(Supermemory). Per the build plan we do NOT chase KG/LLM-extraction; a thin entity-link recall booster + honest
LongMemEval/LoCoMo numbers close the one comparison procurement teams actually run.

**Diagnostic that keeps us honest (MAB Conflict-Resolution, FC-SH 6k, same deepseek answerer, n=100):**
long-context 100 · inspeximus 97 · naive-verbatim 96 · **mem0 88** · random-drop 67. CRITICAL: mem0 scored **88%**
on our clean per-fact harness, NOT its published 18% (that number is a default-pipeline/raw-conversation
artifact). So the CR-accuracy gap is REAL but MODEST — inspeximus 97 vs mem0 88 = 9pt, the measured cost of mem0's
LLM-nondeterministic consolidation vs deterministic supersession. Publishing "97 vs 18" would have been a
credibility-killer (any reader re-running mem0 cleanly gets ~88). Do NOT hang the product on a CR number; the
honest reading is verbatim fidelity + keyed forgetting that never drops a needed fact (random forgetting of
equal volume costs 29 points), and the moat is the integrity/security/determinism axes below.

---

## 2. Capability roadmap — three tiers, mapped to the real API

### TIER A — where we're already #1: HARDEN + PROVE (package what exists, don't build new)
The methods exist; the work is proof, packaging, and a benchmark that stands.
- **Deterministic correction** — `remember(key=…)` supersession, `supersession_report`, `contradictions`,
  `check_conflict`, `as_of`, `history`. → Ship a reproducible integrity benchmark (fixed seeds, runnable
  harness, show where we lose) that isolates *determinism* vs incumbents' LLM coin-flip. This is the flagship
  proof, not a marketing number.
- **Built-in poisoning defense** — `echo_guard`, warrant-gate (`credit`, `credit_requires_warrant`,
  `influence_gate_report`, `ratify`, `slash`, `monitor`), identity-gated supersession. → Publish a threat model
  + a reproducible attack benchmark (MINJA/AgentPoison/echo) reporting ASR-reduction. The field has NO defense;
  this is the differentiated moat.
- **Verifiable forgetting** — `forget`, `forget_subject`, `erasure_report`, `apply_retention`, `sleep`,
  cross-store erasure. → A "prove the value is behaviorally gone across every surface" demo.
- **Signed provenance + tamper-evidence** — `attest`, `sign_revert`, `sign_erasure`, `verify_writes`,
  `verify_attribution`, `verify_consistency`, `anchor`, `rederive` (Ed25519 + hash-chain). → Already a moat;
  needs a one-page explainer + a `verify` CLI anyone can run on their store.

### TIER B — table-stakes security hygiene the product itself needs: BUILD
These are the layer-1 gaps that block a credible "most secure" claim (details in §3).
- Supply-chain: PyPI **Trusted Publishing (OIDC)** + **Sigstore attestations** + **CycloneDX SBOM** + `pip-audit`
  in CI. (Zero-dependency already removes transitive risk — lean on it.)
- MCP server: **bind localhost only**, authenticate even the local server, **per-client/per-operation authz
  enforced server-side every request** (confused-deputy fix, cf. CVE-2025-49596 / CVE-2025-6514), **static-
  validate tool descriptions** (tool-poisoning / Unicode-TAG concealment).
- Data-at-rest: **secret-scrubbing write filter** + optional **encryption-at-rest**.
- Keep fail-closed tenant scoping on every cross-record op (already shipped 1.6.0).

### TIER C — the governance / Article-12 layer: BUILD (this is the monetization moat)
- **Article-12 tamper-evident audit chain with redaction-at-write** (reconciles EU-AI-Act "retain" vs GDPR
  "erase" via pseudonymisation/crypto-shred at log time). Raw material exists (`governance_report`,
  `erasure_report`, receipts). → A written mapping inspeximus-receipts → Article 12(2) clauses + a runnable
  erasure/retention demo = the sellable "conformance-ready evidence" pack.

### TIER D — the one real capability gap (optional, bounded)
- **Thin entity-link recall booster** (NOT a temporal KG, NOT LLM-on-ingest) so multi-hop-ish queries stop
  being a blank cell, + honest LongMemEval/LoCoMo numbers. Bounded so it never breaks zero-dependency-core.

---

## 3. Security posture — checklist to credibly claim "most secure agent memory"

**Table-stakes (must ship):**
- [ ] Trusted Publishing + Sigstore provenance + SBOM at build · `pip-audit` gate
- [ ] MCP: localhost-bind · authn · per-op authz every request · tool-description static validation
- [ ] Secret-scrubbing write filter · optional encryption-at-rest
- [ ] Fail-closed multi-tenant scoping *(covered 1.6.0)* · provenance on every record *(covered)*

**Differentiators (rivals weak/absent):**
- [x] MINJA warrant-gate *(1.9.1)* · AgentPoison/echo guards *(shipped)*
- [x] Identity-gated supersession / anti-resurrection *(1.9.0)* · credit-requires-warrant *(shipped)*
- [ ] Article-12 tamper-evident chain + redaction-at-write **(biggest governance moat — build)**
- [ ] Published threat model + reproducible attack benchmark **(the credibility proof — publish, gated)**

**Bottom line:** we already LEAD layer-2 (defending the agent's memory) where competitors ship nothing. The gap
is layer-1 hygiene + the Article-12 chain. Close those and "most secure agent-memory" is a defensible, sourced
claim — the security posture itself becomes a selling point.

---

## 4. Branding & category

- **Brand = `inspeximus`. Canonical install slug = `inspeximus`, always shown identically everywhere** (PyPI has no
  namespaces; the split is fine if the snippet is canonical). Keep `import inspeximus` / `inspeximus` CLI as the pretty name.
- **Secure `inspeximus.ai` / `getinspeximus.com`**, 301 to docs (Pinecone/Turso pattern); a live `inspeximus.dev` we don't own
  is a mild SEO tax, not fatal — consistency of org+PyPI+docs matters more.
- **Category noun everywhere, verbatim** (repo description, homepage H1, PyPI summary): *"the memory-integrity
  layer for AI agents,"* verb *"self-correcting."*
- **Homepage at Resend/Turso caliber:** category claim + copyable 60-second quickstart + an **honest benchmark
  table with a cell where we lose** + quiet social proof. Design restraint (hairline borders, mono code, no
  gradients-as-personality) — the integrity benchmark IS the hero asset.
- **Founder brand:** the owner authors the benchmark posts / write-ups under his real name (technical authority);
  the **product noun stays impersonal** (naming a project after a person caps its scale). Add a real
  CONTRIBUTING + a one-line governance note to de-risk BDFL perception.

---

## 5. Distribution / GTM (bottleneck = distribution, not credibility)

**Channels ranked (solo team):** (1) **MCP registries/directories — ~78% of installs originate here**
(official MCP Registry, mcp.so, smithery, glama) — highest leverage, near-zero cost; (2) **awesome-* PRs**
(punkpeye/awesome-mcp-servers, awesome-ai-agents) — gated-outreach-friendly; (3) **integration examples**;
(4) GitHub SEO (topics `mcp`/`agent-memory`/`ai-agents`, benchmark-forward README); (5) benchmark posts;
(6) targeted subreddits (owner-posted, English: r/LocalLLaMA, r/LLMDevs, r/mcp, r/AI_Agents); (7) X build-in-
public. **Avoid:** HN self-posts (account shadowbanned — let others submit), your own Discord before you have
users, directory-spam.

**Benchmark-as-marketing (our moat, done honestly):** every incumbent grew on one contested number; the field
distrusts leaderboards. We win by publishing a **runnable, fixed-seed, denominator-shown harness that reports
where inspeximus loses**, on the **integrity dimension** incumbents fake. Lead with LongMemEval/MemoryAgentBench.

**Minimum integration set:** MCP (done) + **LangGraph example** + **mem0-compatible migration shim**. (Note:
the shim as a *migration on-ramp* is distribution; keep it OUT of the flagship's identity — the owner correctly
rejected coupling our product story to a competitor. A migration guide ≠ a co-branded benchmark.)

**Launch sequence (milestone-gated, not dated):** Phase 1 foundation (README + one honest chart + GitHub topics
+ list on all MCP registries + awesome-* PR; gate: live on registries + reproducible harness in-repo). Phase 2
proof (reproducible integrity post on dev.to + owner Reddit; LangGraph + CrewAI examples; gate: ≥1 external
repro/issue). Phase 3 compounding (mem0 migration shim + guide; n8n node; comparison SEO; gate: unprompted
inbound). **Metrics that matter:** MCP registry adds, **star velocity** (not total), PyPI downloads, inbound
issues/claim-submissions/repro-forks. Ignore raw stars / X impressions as goals.

---

## 6. Monetization (income pillars ON TOP of the best product)

**Open-core boundary (no rug-pull):** free/MIT core = recall + consolidation + MCP + single-node receipts +
local erasure + warrant-gate (this is the funnel — never take it away; publish a "these stay free" pledge).
Paid = operational scale + org-need (multi-tenant control plane, hosted API, dashboards, SSO/RBAC, fleet erasure
proofs, signed conformance). Any non-compete only ever on a *hosted-server* component (FSL), never the core.
HashiCorp-BSL and dbt-Fusion both got forked within weeks — the boundary must sit on a different axis than what
devs already use.

**Sequencing (fastest first-dollar, least trust risk):**
1. **$29 one-time pro license** now — proven price point (sub-$5 dies, $29 clears), zero ops, zero trust risk;
   pro = dashboards, fleet erasure, signed-receipts export. Validates that people pay at all.
2. **Article-12 conformance pack ($99–$499/yr)** timed to the **2 Aug 2026** enforcement wave — signed logs,
   erasure proofs, retention config; sell "conformance-ready evidence" (no finalized standard yet, so not
   "certified"). Durable annual stream; can OEM into OneTrust/Drata/Credo rather than compete.
3. **Hosted usage-based API** later, only on proven inbound demand — highest ops load for a solo founder; the
   market clears $19–$249/mo (mem0/Zep) so it's validated upside, not the opening move.

---

## 7. What's MISSING — to fill (owner input / access / tools)

- **Domains:** decision + purchase of `inspeximus.ai` / `getinspeximus.com` (owner action).
- **PyPI Trusted Publishing / Sigstore:** needs the PyPI project configured for OIDC + a GitHub Actions release
  workflow (I can build the workflow; owner confirms PyPI project settings/2FA).
- **OpenAI $5** (offered): only needed to reproduce mem0's *published* gpt-4o-mini config as a cross-check —
  the Ollama-Cloud mem0 run (in progress) already gives the diagnostic for free.
- **A benchmark-hosting surface** for the reproducible harness (the storefront/Crucible already exists — reuse).
- **Skills we have and will use:** storm-research (multi-lens briefing), stress-claim (adversarial gate),
  verify-claims, seo, humanizer, design (restraint). **Skills/tools we DON'T have and may want:** (a) a
  **security-audit skill** (SBOM/pip-audit/Sigstore/MCP-authn checklist runner) — worth authoring; (b) a
  **domain/DNS + landing-page deploy** path; (c) a **PyPI release-automation** workflow with attestations;
  (d) analytics wiring (pypistats/star-history/ossinsight dashboards). Say the word and I'll draft any of these.

---

## 8. Recommended immediate order

1. **Tier-A proof first** (harden + reproducible integrity + poisoning benchmarks) — it's the credibility that
   feeds distribution and is our clearest #1.
2. **Tier-B security hygiene** (Trusted Publishing + MCP authn + secret-scrub) — unlocks the "most secure" claim
   and protects the product/users.
3. **Tier-C Article-12 pack** — the durable income moat, timed to Aug 2026.
4. Distribution (MCP registries + awesome-* + LangGraph) runs in parallel from Phase 1.
Every outward artifact gated (validate→storm→audit→verify). Sources: 5-lens scan transcripts (this session).

# ORGAN REDESIGN — the implementation plan

**Status: DRAFT, research phase. Not yet gated. Do not implement past Phase 0 until Phase 1 lands.**
Owner directive 2026-07-29: every organ gets a REASSIGNED role, each in a DIFFERENT domain, each with
content set so it pushes the organization AND the products forward. World scan + Gate required first.

This file exists because I lose the thread across context resets. Anything not written here did not
happen. Update it in place; do not start a second plan file.

---

## 0. What today's measurements ESTABLISHED (verified, safe to build on)

| Finding | Evidence | Status |
|---|---|---|
| Only ~2 agents produced by note count; 4 read as zero | 138 notes/14d, `author:` field | measured |
| That instrument was WRONG | repair ledger: Rooke 58 repairs / 33 decisive, top of the org | **corrected** |
| Wren: 80 repairs, 0 decisive | repair ledger 60d | open defect |
| Bounty/Graveyard dead 42d because verdicts were never posted | 3 challenge tasks `done`, `result` empty | root cause |
| `_task_already_pending` had no expiry — one stuck task shut an organ | Rooke blocked 4 days, ~200 sweeps | **FIXED** `1d2109e` |
| 6 of 8 organs have a LIVE work source | endpoint sweep, corrected instrument | measured |
| Elara (contradictions) and Kael (scout leads) are genuinely DRY | same sweep | open |
| Gate passes 36/69 (52%) of canon; its tokens are generic English | falsifier | open defect |

### REFUTED today — do not rebuild on these
- "Two relevance filters disagree, the head wedges" — gate passes 8/8 including the head.
- "The gate over-rejects" — it accepts 52%.
- "`loop_n` resets on restart so organs never fire" — dungeon had 30h unbroken uptime.
- Ringelmann / social loafing as an explanatory frame — category error, LLM agents have no effort
  function to withhold. Retracted.

### External evidence already verified against primary sources
- **MAST** (Cemri et al., NeurIPS 2025 D&B, 1642 traces, κ=0.88): FM-1.3 "Step Repetition" **15.7%**;
  **44.2%** of failures are System Design. Abstract: gains "often minimal."
- **Apache** (Mockus/Fielding/Herbsleb, ACM TOSEM 11(3) 2002): top 15 = >83% of MRs but only **66% of
  fixes**; 26 devs/100 fixes vs 4/100 submissions. Tail concentrates in **defect repair**, NOT
  "verification" (that 83% is Mozilla's Bugzilla number — do not conflate). Mozilla: 113 people filed
  half the problem reports, **46 wrote no code at all**.
- **Anthropic multi-agent** (vendor blog, not peer-reviewed): ~15× tokens vs chat; token usage explains
  80% of variance **on BrowseComp, in their own config sweep**; 90.2% outperformance on a **private**
  eval. Their caveat: domains with "many dependencies between agents are not a good fit."
- **Blumofe & Leiserson** (JACM 1999): work-stealing `T1/P + O(T∞)` **for fully strict computations**.
- **DO NOT ASSERT**: contract-net "30-60% faster / 90% less overhead" — FALSE as attributed; traces to
  Hoeing et al. AAMAS 2007, a single 18-robot simulation, not the Springer survey.

---

## 1. THE DESIGN CONSTRAINT the owner set

> Each agent works in a **different domain**, and each job's content must be set so it advances **the
> organization and the products**.

Two hard consequences, both from verified evidence:

1. **Equal contribution is the wrong target.** Creation concentrates everywhere it has been measured;
   the tail is real in repair. Forcing equal output = a quota, and a quota is met by lowering the gate.
   The right target is: *every agent has a live queue and is measured by the artifact its own work
   produces.*
2. **Dependency chains are the documented anti-pattern.** Our Graveyard←Bounty and Rooke←others chains
   are exactly what Anthropic's own guidance says not to build. Each organ needs a source that does not
   depend on another agent having produced first.

---

## 2. PHASE 1 — world scan (IN FLIGHT)

Question: how do real organizations assign non-overlapping domains so every member has substantive
work, and what makes such an assignment produce compounding output rather than busywork?

Must return: named mechanisms with evidence, how domains are partitioned without starving anyone, and
how output quality is held while coverage is spread. Then **stress-claim** (adversarial) and
**verify-claims** (every number vs primary source) before any code.

## 3. PHASE 2 — reassign the eight organs (BLOCKED on Phase 1)

Table to be filled from Phase 1. Each row must specify: domain (distinct), renewable INPUT source that
does not depend on another agent, the ARTIFACT produced, the LEDGER it writes to, and the failure
signal when it starves. Empty on purpose — filling it from intuition is what this plan exists to stop.

**THE PARTITION RULE (academic lens, 2026-07-29):**

> Duplication and starvation are the SAME axis. Agents sharing one input pool duplicate (that is
> exactly MAST's FM-1.3 Step Repetition, our 15.7%); agents coupled sequentially starve (that is
> Graveyard←Bounty). **Only separating the INPUT CHANNEL — a distinct corpus/tool/data source per
> agent — buys you both at once.** Keep interdependence *pooled* at the work stage and defer
> integration to a single merge step.

- Malone & Crowston (ACM Comp. Surveys 26(1), 1994): coordination is *dependency management*. Remove
  the dependency by partition; do not add a protocol to manage it.
- Thompson (1967) + Van de Ven, Delbecq & Koenig (ASR 41(2), 1976): as interdependence moves
  pooled→sequential→reciprocal, cheap standardized coordination gives way to costly mutual adjustment.
  This is the mechanism under Anthropic's "many inter-agent dependencies = poor fit."
- Becker & Murphy (QJE 107(4), 1992): division of labour is bounded by coordination cost, so there is
  an **interior optimum** on the number of specialists. 8 is not automatically right; neither is 2.
- arXiv:2602.03794 (**preprint**): 2 *diverse* agents match/exceed 16 homogeneous ones; diversity means
  different models/prompts/**tools**. Suggestive of domain separation, not proof.

**CONWAY'S LAW READ BACKWARDS — this is how the owner's product requirement gets satisfied:** the
partition of agents *becomes* the partition of the output. So choose the decomposition we want the
PRODUCTS to have (inspeximus surfaces; Crucible ledger sections) and let the roles follow from it.
Do not choose personas first and hunt for work to fit them — that is the current design.

**HONESTY CONSTRAINT:** MAST's 44.2% and Apache's repair-tail are both *observational*; neither
randomizes the partition. **Any partition we ship is a hypothesis, not a finding.** The honest test is
a within-org A/B: same 8 agents, same token budget, shared-corpus arm vs disjoint-corpus arm,
duplication rate pre-registered as the primary endpoint.

**DO NOT USE:** Hackman & Oldham's Job Characteristics Model (skill variety / autonomy) to justify
agent role design. Those are motivational mediators in humans — the same category error already
retracted once today. Hong & Page (PNAS 2004) is formally contested; intuition only.

---

**THE ADMISSION TEST (skeptic lens, 2026-07-29) — apply BEFORE filling any row:**

> A domain is not an organ; a **consumer** is. The test for keeping an agent is not "does it have a
> domain and an input source" — inputs are cheap — but **"name the artifact that breaks if it stops."**

Our own evidence for this: the dedup guard blocked the system for days and *nobody downstream
noticed*. Replication and curation kept producing precisely because their output has a consumer that
would miss it (the Crucible ledger, the vault). Wren produces 80 outputs with 0 decisive ones because
nothing consumes a chart.

**RULE: any row whose CONSUMER column cannot be filled with a specific artifact does not get built.
That agent is deleted or demoted to a function the others call.** Filling a domain and an input for a
role with no consumer is how we got here.

**THE THIRD-PARTY RULE (product lens, 2026-07-29):** every role's output must carry a **named external
system** in its title. That is the filter separating Jepsen (vendors pay for and republish the
analyses) from ReScience C (~17 articles in two years, never took). Evidence in our own market: Zep
re-ran Mem0's own LoCoMo eval, found three named implementation defects, reported J=75.14% vs the
65.99% Mem0 had published — one adversarial replication rode a 51k-star competitor's audience.
Corollary: **pick claims by the claimant's audience, not by tractability.** A FAILED verdict is only
news if the target has readers.

### THE ASSIGNMENT (v1 — a hypothesis to be A/B tested, not a finding)

Partitioned by EXTERNAL INPUT SOURCE, per the convergent finding of all four lenses. Boundaries are
stated **negatively** in each brief ("do not work X, that is another agent's source") — Anthropic's own
fix for the duplication failure.

| Agent | External source (its beat) | Artifact it produces | CONSUMER — what breaks without it | Ledger | Starving when |
|---|---|---|---|---|---|
| **Shadow Kael** | Competitor release notes & changelogs (mem0, Zep, Letta, Cognee, LangGraph) | An extracted, **testable** claim with the vendor named | Rooke's bench — no claims in, no ledger entries out | scout box | 0 claims extracted in 72h |
| **Artificer Rooke** | Kael's claim queue + claims in published papers | Crucible entry: REPRODUCED / FAILED / NOT_COMPUTABLE + minimal model | `public/crucible/` + `crucible.json` — the public ledger stops growing | `.replications.json` | 0 entries in 72h |
| **Sergeant Voss** | **Our own** canon and published numbers (inward adversary) | A verdict that retires or revises one of OUR beliefs | The bounty ledger and the canon — without it we publish unverified numbers | `.bounty.json` | 0 verdicts in 72h |
| **Dame Elara** | Framework repos that already have users (LangGraph, ADK, Haystack, CrewAI, llama_index) | A drop-in adapter + a conformance run against THEIR own suite | inspeximus CI parity jobs — the "drop-in" claim goes untested | CI job status | any parity job unrun 7d |
| **Cartographer Wren** | Published results of named memory systems | A **leaderboard ROW** with a reproducible metric | The public integrity leaderboard — it goes stale | leaderboard file | 0 rows added in 7d |
| **High Priest Orin** | The gap between what benchmarks measure and what integrity requires | A new measurable AXIS + a runnable harness | Wren's leaderboard needs columns — else we only measure what others already measure | `.analogies.json` → axis registry | 0 new axes in 14d |
| **Sage Mira** | Rooke's FAILED entries + Voss's kills (**the single merge step**) | The public disclosure writeup / post | Distribution — findings never leave the repo | vault + `public/` | a FAILED entry unwritten 7d |
| **King Aldric** | Our own roster + ledger health | Audit keeping us **referee, not contestant**; the starvation report | Our credibility — a scorer that scores itself is not a referee | `starvation_report()` | any organ starving >72h unreported |

**Known coupling, accepted deliberately:** Kael→Rooke and (Rooke,Voss)→Mira are sequential. The academic
lens permits exactly this shape — pooled interdependence at the work stage with integration deferred to
**one** merge step. Mira IS that merge step. Every other pair is disjoint by source. The old design's
sin was many coupling points (Graveyard←Bounty, Rooke←collective), not the existence of any.

**Aldric is deliberately not given a research beat.** Per the product lens, our position is referee, not
contestant, and the referee cannot also compete for rows on the board he keeps.

**Sequencing consequence:** fix CONSUMPTION before adding sources. Every new renewable input is a new
firehose, and we have already shipped that failure once today (the Library read 202 off-mission papers
in full because a fallback source pointed at a vault word). If 3 organs saturate the owner's review
capacity, there is no argument for 8 — that is an empirical question about review throughput, and it
must be answered before the roster size is decided.

**Skeptic's counter-evidence to weigh in Phase 1 (verify before use):** Leahey/Beckman/Stanko (ASQ
2017, ~900 scientists) — interdisciplinary span raises citations but LOWERS productivity; Ridgway (ASQ
1956) — single-criterion performance measures reliably produce dysfunctional volume-maximizing
behaviour, i.e. our per-agent ledgers and starvation alarms are themselves a quota risk; Segment and
Prime Video re-consolidating over-decomposed services.

## 4. PHASE 3 — implement, one organ per commit

Rule: one organ, one commit, measured before and after. No organ ships without its starvation signal
wired to `starvation_report()`.

## 5. OPEN DEFECTS carried into this plan

1. **Wren: 80 repairs, 0 decisive.** Charts and never concludes. Volume without value — the exact thing
   the skeptic warned a quota produces.
2. **Elara DRY** — contradiction detector returns 0 against 80 beliefs. Detector likely not running.
3. **Kael DRY** — scout box empty; GitHub scan fires less than its documented cadence.
4. **Gate tokens are generic English** ('bed', 'better', 'answer', 'buyer'). It passes 52% of canon and
   filters almost nothing. Fixing it will *tighten* supply — sequence it AFTER the sources are live.
5. **I am the execution bottleneck.** Organs queue; execution runs through my inbox. Bounty sat 42 days
   because I closed 3 challenge tasks without posting verdicts. `owed` (`0212060`) now surfaces it.

## 6. COMMITS SO FAR (this workstream)

- `4639e0c` arXiv AND-join at the single choke point
- `8e948d8` Library loop drains the reading list; prune stale frontier queue
- `2c03274` walk the candidate list *(kept, but did NOT fix the outage — see refuted list)*
- `d437989` repair ledger + starvation report — the instrument that called Rooke idle was wrong
- `0212060` `owed` guard on inbox close + three retractions
- `1d2109e` **pending-guard expiry — the real unblock, covers all 26 organs**

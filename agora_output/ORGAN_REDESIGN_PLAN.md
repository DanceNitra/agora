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

## 3a. GATE RESULT — CITATION VERIFICATION. Most of the distribution evidence did not survive.

**THE CENTRAL CASE HAS A REVERSAL I DID NOT HAVE.** Mem0 *did* publicly rebut Zep
([getzep/zep-papers#5](https://github.com/getzep/zep-papers/issues/5), Deshraj Yadav, 2025-05-08):
Zep counted Category-5 adversarial answers in the numerator while excluding them from the
denominator, inflating its figure by ~25.6pp — correct value **58.44% ±0.20**, not 75.14%. Zep quietly
revised its headline from a 24% win to ~10% and never answered the issue.

So the adversarial replicator **was itself successfully counter-replicated.** This is BLOCKER 1
happening in reality, in our own market, to the exact play we were about to copy. It remains a valid
*distribution* case study (the attack drew a response) but it is **not** a credibility exemplar, and
citing it as "adversarial replication works" cuts both ways.

| claim | verdict |
|---|---|
| Zep 75.14 vs 65.99, three named defects | numbers and direction CONFIRMED — but see the reversal above |
| mem0 has ~51k stars | **FALSE** — 62,016 (GitHub API, 2026-07-29) |
| Jepsen: "~26 systems with violations" | **UNVERIFIED, do not use.** Page says "over two dozen analyzed"; actually 38 systems / ~50 reports. No per-system violation count is published |
| Jepsen: MongoDB, Cassandra, etcd all pay | **PARTLY FALSE** — Cassandra (2013) and etcd (2014) were independent. Say "vendors including MongoDB commission and republish" |
| HF leaderboard 2M+ visitors / 300k monthly | CONFIRMED verbatim (window ~Aug 2023–Jun 2024). The "200+ community leaderboards" is on a DIFFERENT page — cite both |
| ReScience C: ~17 articles in 2 years, never scaled | **FALSE ON BOTH HALVES, AND IT INVERTS THE ARGUMENT.** 8 articles in the first two years; and it DID scale — Vol 8 (2022) = 54, Vol 9 = 51, largely because MLRC fed it |
| MLRC: 8 years to an official NeurIPS track (2026) | CONFIRMED verbatim |

**Consequence for the plan:** I was using ReScience as evidence that neutral replication venues starve
without a named target. It is evidence of the *opposite*. The "name a third party or you get no
distribution" argument loses its strongest support and must be re-argued or dropped.

## 3b. GATE RESULT — RED TEAM VERDICT: **REFRAME** (2026-07-29). Blocking changes below.

**BLOCKER 0 — SHIP THE COMPLETION-INTEGRITY GATE FIRST.** The last outage was three tasks closed
without their verdicts posted, *by the executor*. The plan adds seven more producers upstream of that
same unguarded sink. A partition of inputs cannot fix a defect in the sink. **"No close without a
posted, linked artifact" must land BEFORE any beat is reassigned**, or the redesign multiplies the
failure it exists to prevent. (`owed` in `0212060` warns; it does not enforce.)

**BLOCKER 1 — responsible disclosure on FAILED.** A FAILED verdict on mem0/Zep/Letta is a public claim
about a commercial product whose authors can produce a refuting config in a day; we cannot re-verify at
that speed with one executor and a backlog. The first refuted FAILED permanently inverts the ledger's
premise from "we check" to "they publish sloppy takedowns."
→ REPRODUCED and NOT_COMPUTABLE publish freely. **Every FAILED goes to the vendor first** with the
runnable artifact, held until they respond or a stated window elapses. Mira's writeups lead with the
harness, never a vendor name in the title.

**BLOCKER 2 — "names an external system" is Goodhart-shaped.** It rewards *touching* something
external, not *changing* anything. Keep the intent (external anchoring, anti-recycling) but the
acceptance test becomes: **"could a named external party act on this?"** — not "does a proper noun
appear in the title."

**BLOCKER 3 — RESOLVED, and my first answer was wrong.** The red team called Aldric-as-referee
structurally conflicted while inspeximus is scored on our own board, and I proposed excluding
inspeximus from the leaderboard. The owner rejected that, correctly: it throws away the ability to
demonstrate we are the best in order to dodge a problem instead of solving it.

**The conflict is not that we are ON the board. It is that the numbers come from us and must be
trusted.** Remove the need for trust and the conflict dissolves:

- The harness is **public and runnable by anyone**; every row carries the exact command that
  reproduces it.
- Numbers are **not produced on our machine** — the leaderboard runs in CI on neutral infrastructure,
  so we have nothing to reach into.
- Competitors may **submit their own configuration** and challenge any row, ours included.
- **Our row goes through the same procedure as everyone else's**, and when someone refutes it, the
  refutation stays on the record permanently.

Jepsen is the proof: Kingsbury is *paid by vendors* and remains the most trusted name in the field,
because the tests are published and re-runnable. Credibility there comes from reproducibility, not
from disinterest. And reproducibility is exactly inspeximus's moat — so a leaderboard built on
re-runnability is not a concession, it is a product demonstration.

**Aldric's beat therefore changes:** not "audit our referee-hood" (a conflict wearing a badge) but
**own the reproducibility guarantee** — every row re-runnable on neutral infra, challenge procedure
open, refutations recorded. That is a real job with a real consumer (the board's credibility) and it
is falsifiable: pick any row at random, re-run it, and the number must match.

**ACCEPTED LIMITATION — no throughput gain.** Every artifact still executes through one Claude
instance; partitioning inputs changes queue *composition*, not service rate. The real gain is queue
diversity, which is what kills the 80-outputs-zero-decisive failure. **Budget beats by execution cost,
not by symmetry — eight equal beats will starve six.**

## 3c. CADENCE DEFECT found while gating (2026-07-29) — fix before Phase 3

Organ triggers are `loop_n % N == M`. Measured from the live dungeon: **a full roster pass takes ~1.3
minutes**, not the ~0.85s the code comments assume. Real first-fire times versus documented:

| organ | trigger tick | REAL first fire | code comment says |
|---|---|---|---|
| Replication (Rooke) | 600 | **12.8 h** | ~28 min |
| Analogy Forge | 900 | **19.3 h** | ~50 min |
| Belief revision | 1200 | **25.7 h** | ~47 min |
| Cartography (Wren) | 1700 | **36.4 h** | ~43 min |

Off by ~25x, and `loop_n` resets on every dungeon restart — so Cartography effectively never fires
unless the process runs 36h+ uninterrupted. **The death ordering matches the trigger ordering exactly**
(replication survived longest, cartography died first), which is the corroboration.

CAVEAT ON MY OWN NUMBER: this assumes **one `loop_n` per roster pass**. Not verified. Verify the
increment site before acting on these figures.

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

## 5b. OPEN MEASUREMENT — world-model-mcp (queued 2026-07-29, inbox `56360c`)

A peer project, `SaravananJaichandar/world-model-mcp`, ships the full provenance/trust axis:
`asserted_by`, `confirmer`, `confirmation_state`, `evidence_type`, `last_decay_at`,
`influence_state`, `expires_at`, with evidence-type half-lives. MIT, MCP-native, pip-installable,
Zenodo DOI 10.5281/zenodo.20834508, 20 stars.

**It PREDATES us.** Repo created 2026-01-10; releases running continuously since at least v0.6.1
(2026-05-05). The openclaw issue #7707 where the exchange happened was filed 2026-02-03 by
`LumenLantern` — it is not ours, we only commented on it. I initially told the owner this was "our
issue" and that the axis had been taken from us. Both were wrong, and the timeline is the reason to
state it plainly: nothing was copied. He was there first and has been shipping for six months.

This matters because provenance is the #1 external demand signal we measured (84 project mentions vs
correction 69, revert 10) — and someone shipped the schema for it before us.

**The open question is NOT the schema — it is enforcement.** He states outright what he does not
ship: citation polarity, and self-verifying claims via replay recipe ("needs a probe executor").
Enforced erasure appears nowhere; `expires_at` is a timestamp, i.e. a declaration. Our own lesson
`declared-fields-read-zero` says a declared field is not a guarantee, and our conformance suite exists
because two erasure defects shipped past 1600 library tests.

So the measurement, not the argument: run our erasure cell with a world-model-mcp adapter beside the
mem0 one. (1) After `expires_at` passes, is the VALUE still on disk or only filtered from retrieval?
(2) Does `influence_state='blocked'` remove or merely hide? (3) Is there any delete equivalent to
`forget_subject`? Controls first: `erasure_works_at_all` (a no-op adapter must score 0), and re-run
our own cell in the same cycle so both ends of the delta are measured. My mem0 adapter once scored
0.00 purely because I called a rejected API inside a bare `except` — I nearly published a false
accusation. **Assume our adapter is wrong before assuming the competitor is.**

Outcome is REPRODUCED (they enforce it too — then our erasure moat claim is dead and we record that
plainly), FAILED (declared but not enforced — a real measured gap), or NOT_COMPUTABLE. Gated: a
FAILED goes to HIM first with the runnable artifact, per BLOCKER 1.

## 6. COMMITS SO FAR (this workstream)

- `4639e0c` arXiv AND-join at the single choke point
- `8e948d8` Library loop drains the reading list; prune stale frontier queue
- `2c03274` walk the candidate list *(kept, but did NOT fix the outage — see refuted list)*
- `d437989` repair ledger + starvation report — the instrument that called Rooke idle was wrong
- `0212060` `owed` guard on inbox close + three retractions
- `1d2109e` **pending-guard expiry — the real unblock, covers all 26 organs**

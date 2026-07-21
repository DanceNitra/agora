# Ten upgrades, ranked by measured external demand

Built from evidence gathered overnight 2026-07-20/21, not from taste. Three independent instruments
agreed, which is why the ranking below inverts what we have been saying in public:

- **Cartographer's external map** — 312 harvested GitHub issues/PRs + Reddit threads, bucketed by need
  and counted by DISTINCT projects raising them.
- **Contribution finder** — 113 of those threads where something we have SHIPPED answers the question.
- **MemOps pilot** — the measured null: on answer accuracy nothing separates us from a keep-everything
  store; only write cost separates, by an order of magnitude.

| need | distinct projects | mentions | threads we could answer |
|---|---|---|---|
| provenance / trust | 84 | 134 | 22 |
| correction / update | 69 | 105 | 30 |
| retrieval quality | 28 | 82 | — |
| dedup / conflict | 22 | 31 | — |
| forget / erasure | 18 | 28 | 6 |
| determinism / cost | 17 | 25 | 25 |
| poisoning / safety | 15 | 22 | 22 |
| **revert / undo** | **10** | **10** | **6** |
| drop-in store for a framework | — | — | **39** |

**The uncomfortable headline: `revert` is last.** It is the feature we advertise as "nobody else has
this", and of 312 threads about agent memory, ten mention wanting it. Meanwhile 84 projects are asking
about provenance and trust — where we have real, tested material we barely mention.

That does not make revert worthless. It makes it a *proof*, not a *pitch*: evidence that the store has
a real state model, cited in support of the correction story, rather than the headline it is now.

---

## 1. Make the drop-in story real and findable — 39 threads, the single loudest ask

`InspeximusStore` already passes an operation-by-operation parity audit against LangGraph's own
`InMemoryStore` (`store_audit.py`, in CI). Nobody knows it exists: it is in no LangChain integrations
page, and `awesome-LangGraph#88` still sits unmerged.

Do: a `langchain-inspeximus` package + the docs PR (LangChain now requires third-party integrations to be
your own package), the LlamaIndex `BaseMemoryBlock`, and Google ADK's `BaseMemoryService` — ADK runs an
integrations catalogue with little competition. Effort: ~1 day each. This is distribution, not code.

## 2. `inspeximus install` — one command, MCP + hooks configured

claude-mem has **87,990 stars** on an `npx` install and no benchmark; we have three audit harnesses and
4 stars. Installability is the variable. `uvx inspeximus install --ide claude|cursor|codex` writing the MCP
config, plus a `.claude-plugin/marketplace.json` so it is one click from a marketplace.

## 3. Lead with provenance — 84 projects, our loudest unclaimed need

We ship attestation, `trusted_only` (fails closed), and — more valuable — the *honest limit*:
`trust_is_not_truth.py` proves a provenance gate is authorization, not correctness. Nobody else
publishes that. Turn it into a documented feature page with the runnable demo, and answer the threads.

## 4. Promote correction to the headline — 69 projects, 30 answerable threads

Supersession + `echo_guard` + the read-time resolver is our second-strongest asset and the second
loudest need, currently buried under revert. Reframe the README around "corrections that stick" with
revert as the proof underneath.

## 5. Retrieval quality — 28 projects, and our weakest measured axis

MemOps showed turn-level keyed retrieval recovers 0.142 of evidence sentences against session-level
0.305 — we win on answers but carry a 2.1x coverage deficit. Ship a session/segment ingest mode and
let the caller choose granularity, then re-measure. This is the one item where the honest verdict is
"we are behind", and it is measurable.

## 6. Name and expose dedup / conflict resolution — 22 projects

Consolidation and the read-time conflict resolver exist and are unnamed in the docs. A feature page
plus `inspeximus contradictions` in the CLI costs hours.

## 7. REST server + OpenAPI + a published image

Every competitor has one; we do not. "Can my Node/Go service call it?" is a procurement question, and
it unlocks the TypeScript client without porting the core (the OSS TS memory SDKs are all vestigial —
porting would be a trap).

## 8. `inspeximus import --from mem0|zep` — nobody has it

Anti-lock-in is the loudest unanswered complaint in the competitive field, and a migration path is
simultaneously a feature and an outreach story. Two days.

## 9. Turn the benchmarks into a product — 33 threads ask how to measure

`benchmarks/memops` (pre-registered, published with its null), RAMR, `claims_audit.py` and
`governance_audit.py` already exist. Package them as "run this against YOUR store": a cross-vendor
harness is the one benchmark slot nobody owns, and vendors running their own leaderboards is the
field's open sore.

## 10. Async API + OpenTelemetry hooks

Cheap, procurement-visible, and blocking for anyone inside FastAPI. `async def` wrappers plus an
optional `tracer=` argument with a no-op default.

---

## What NOT to build

- **A TypeScript rewrite of the core.** Those large npm numbers are cloud clients; every open-source TS
  memory SDK is under 100 downloads/week.
- **A hosted dashboard.** Cognee gives its full UI away; months of work to reach parity on a non-moat.
- **Graph/entity extraction or anything with an LLM on the write path.** That is the tax we win by not
  paying.
- **LOCOMO leaderboard chasing.** Vendor-run harnesses with unreproducible numbers; ship the
  cross-vendor harness instead.

## The strategic correction

We have been selling the rarest feature instead of the most wanted one. The evidence says lead with
**correction and provenance**, prove them with **revert and receipted erasure**, and make the whole
thing **installable in one command** — because the project with 88k stars beat us on installability,
not on rigour.

---

# Addendum, 02:30 — how the big repos actually got their stars, and the number that says we have no users

## The download figure is us

`inspeximus` on PyPI, mirrors excluded, 29 days:

| | days | mean downloads/day |
|---|---|---|
| days we published a release | 20 | **555** |
| days we did not | 9 | **9** |

Correlation between our releases and our downloads: **r = 0.977**, across 97 releases in 29 days. The
weekly download figure is CI and mirror traffic responding to our own publishing. On a day when we ship
nothing, **nine** people install inspeximus. That is the honest adoption signal, and it must never appear in
a pitch as evidence of traction — anyone competent will run this same query.

Nothing public currently cites the number, checked across the README, docs and the site. Keep it that
way until the non-release baseline moves.

## What actually produced the star counts

Star forensics on the leaders (GH Archive `WatchEvent` mirror; see the caveat at the end):

- **claude-mem, 88k stars: four discrete waves, not one viral moment.** Each wave follows a major
  version bump and rides **GitHub Trending** — first #1 on 2025-12-10. Hacker News presence: **2 points,
  lifetime.** No launch post. It is in `claude-plugins-community` as 1 of 2,249 entries, *not* in the
  official directory. What it did do: **297 releases in 10.5 months** and annexed every new agent host
  as it shipped — Cursor, OpenClaw, Codex, Antigravity CLI. Each expansion is a fresh audience and a
  fresh Trending run.
- **mem0: the driver was the `embedchain` → `mem0` rename-relaunch** (July 2024): ~5 stars/day to 1,998
  at peak. The $24M Series A moved nothing measurable — 558 stars in October, 562 in November.
- **Papers do not buy stars.** Graphiti's arXiv month was its *worst* month. mem0's LoCoMo paper
  produced 93 and 158 stars on the following two days. MemGPT's paper worked once and never compounded.
  Publish for citations, collaborators and legitimacy — not for distribution.

**Do not copy claude-mem's amplifier:** it brands a `$CMEM` memecoin with a ~9,000-member community on
the repo. GitHub bans token-incentivised starring. The wave shapes look organic, but a financially
motivated non-technical constituency is not a mechanism we would want even if it were allowed.

## What that changes in the list above

1. **Item 2 (`inspeximus install`) is now the best-evidenced item, and it grows a second half:** make the
   repo *its own plugin marketplace* (`.claude-plugin/marketplace.json`), so `/plugin marketplace add
   DanceNitra/inspeximus` makes every install a repo visit. Then **annex each new agent host as it launches**
   — that is the repeatable move behind the 88k, and it costs a day per host.
2. **Freeze the release cadence** until someone is watching. 97 releases into an audience of 19 unique
   visitors and 0 watchers buys no Trending eligibility and manufactures the fake download number above.
   Resume later as deliberate major bumps timed to host expansions.
3. **The rename decision deserves an explicit re-decision.** The standing call was "no rename, anchor on
   `inspeximus`". The single highest-leverage move observed anywhere in this dataset was a
   rename-relaunch, and we carry an eight-way name collision. That is now a quantified cost, not a
   preference — owner's call, but it should be made again rather than inherited.

## Marketing or capability?

Neither, exactly. **The capability is real and unfindable.** Three audit harnesses, a parity-tested
LangGraph store, a published null and signed provenance — and nine installs on a quiet day. Nothing in
the evidence says build more; everything says be installable where people already are, and be present
in the threads where the need is voiced.

## Caveat on the star numbers

The `/stargazers` timestamped endpoint 404s from this environment, so there is no independent
cross-check. The GH Archive mirror captured only ~21% of claude-mem's lifetime stars, so the absolute
daily figures are undercounts — **only the relative timing and the shape of the spikes are reliable**.
The specific trigger of claude-mem's February 2026 wave is pinned by date but the causing artifact is
unverified.

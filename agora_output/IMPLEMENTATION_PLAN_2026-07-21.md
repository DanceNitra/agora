# Implementation plan — from the 21 July briefing

One item at a time, in build order. Each item states **why it is here** (the measured evidence), **what
exactly to build**, **which files**, **how we know it is done** (an acceptance test, not an opinion),
and **what it costs**. Nothing outward-facing ships without the standing gate: validate → storm →
audit → verify.

**The ordering principle.** The briefing's own evidence says the bottleneck is not capability. Three
audit harnesses, a parity-tested LangGraph store, a published null, signed provenance — and **nine
installs on a day we do not publish a release**. So the plan front-loads *findability* and *installability*,
which are cheap, then the *story*, which is free, and only then new capability. The one exception is
item 5: it is the single axis where the honest verdict is "we are behind", and it is measurable.

Current state assumed: `inspeximus` **1.24.4**, CLI subcommands `browse consolidate contradictions
decision distill forget governance list recall reembed remember revert stats why`, integrations already
written for langchain, langgraph, llamaindex, google_adk, crewai, autogen, openai_agents, pydantic_ai.

---

## Phase 0 — make what already exists reachable (target: today + tomorrow)

### 0.1 `inspeximus install` — one command configures the host
*Briefing item 2. Why: claude-mem has 88k stars on an `npx` install and no benchmark; we have three
audit harnesses and 4 stars. Installability is the variable that differed.*

Build `inspeximus install --ide claude|cursor|codex|windsurf|cline` that writes the MCP server block into
that host's own config file and prints what it wrote.

- Files: `inspeximus/cli.py` (new subcommand), new `inspeximus/install.py` (per-host config paths + writers).
- Must handle that **Codex uses TOML, not JSON** — the briefing flagged this as an untested claim we
  refused to put in the README. Writing it in code and testing it is how that claim becomes true.
- Idempotent: running twice leaves one server block, not two. Never clobber an unrelated key.
- **Acceptance:** on this machine, `inspeximus install --ide claude` produces a config Claude Code actually
  loads (verified by the server appearing in `/mcp`), and a dry-run mode prints the exact diff for the
  four hosts we cannot test here. A host we cannot verify prints "unverified" rather than claiming
  success.
- Cost: ~1 day. **Blocks 0.2** (a listing that installs in one line needs the one line to exist).

### 0.2 Package and list the drop-in store
*Briefing item 1. Why: 39 threads — the single loudest ask — and `InspeximusStore` already passes an
operation-by-operation parity audit against LangGraph's own `InMemoryStore` (`store_audit.py`, in CI).
It appears on no integrations page.*

Three separate deliverables, in this order (cheapest proof of demand first):

1. **`langchain-inspeximus` package** — LangChain now requires third-party integrations to live in your own
   package. Thin wrapper re-exporting `inspeximus.integrations.langgraph`, its own PyPI name, its own CI.
2. **LangChain docs PR** — the integrations page entry. Outward → standing gate.
3. **LlamaIndex `BaseMemoryBlock`** and **Google ADK `BaseMemoryService`** — ADK's catalogue has little
   competition. `inspeximus/integrations/llamaindex.py` and `google_adk.py` exist; the work is conforming to
   each framework's registration contract and getting listed.

- **Acceptance:** a clean machine can run `pip install langchain-inspeximus`, paste six lines from the
  target framework's own docs page, and get a working store — tested from a fresh venv, not asserted.
- Cost: ~1 day each. `awesome-LangGraph#88` stays untouched: eight PRs are queued behind a maintainer
  who last merged on 10 July. Do not nudge.

---

## Phase 1 — say the true thing (target: this week, mostly writing)

### 1.1 Reframe the README around correction, with revert as the proof
*Briefing items 4 and 3. Why: correction is asked for by 69 distinct projects and provenance by 84;
`revert`, which we currently headline as "nobody else has this", is asked for by **ten**.*

Revert is a *proof* that the store has a real state model. It moves under correction; it does not lead.
New top-of-README order: **corrections that stick → provenance you can check → receipted erasure →
revert as the evidence underneath.**

- Files: `README.md` (sections at lines 89 and 313 are the load-bearing ones), `docs/`.
- **Acceptance:** a reader who knows nothing about us can answer "what problem does this solve?" from
  the first screen, and every claim on that screen names the script that checks it (the existing
  "every claim below is checked by a script you can run" section is the pattern — keep it).
- Outward → standing gate before publish. Cost: half a day.

### 1.2 A provenance feature page with the honest limit
*Briefing item 3. Why: 84 projects, our loudest unclaimed need, and we hold something nobody else
publishes.*

We ship attestation, `trusted_only` (fails closed), and `examples/trust_is_not_truth.py` — a runnable
proof that **a provenance gate is authorization, not correctness**. Publishing our own limit is the
credible move, and no competitor does it.

- **Acceptance:** the page's every claim re-runs from the repo in one command, including the limit.
- Cost: half a day. Then answer the 22 threads (each one gated individually).

### 1.3 Name dedup / conflict resolution in the docs
*Briefing item 6. Why: 22 projects, and the capability already exists — `inspeximus contradictions` is in
the CLI right now and is documented nowhere.*

Cost: hours. Pure documentation debt.

---

## Phase 2 — close the one gap where we are genuinely behind

### 2.1 Session/segment ingest granularity, then re-measure
*Briefing item 5. Why: MemOps measured turn-level keyed retrieval recovering **0.142** of evidence
sentences against session-level **0.305** — we win on answers but carry a 2.1× coverage deficit. This
is the only item where the honest verdict is "we are behind".*

Let the caller choose ingest granularity (turn / segment / session) instead of hard-coding turns, then
re-run the pre-registered harness.

- Files: `inspeximus/inspeximus.py` ingest path, `benchmarks/memops/`.
- **Acceptance:** the coverage number moves *measurably* on the same pre-registered harness with the
  same budget parity, and the result is recorded **whichever way it goes** — including if it does not
  move. A null here is publishable and, given three prior nulls on supersession, expected until shown
  otherwise.
- Cost: 2–3 days. **Do not claim an improvement before the re-measure. This is the severe-test rule.**

---

## Phase 3 — surface area that procurement asks about

### 3.1 REST server + OpenAPI + a published image (item 7)
Every competitor has one. Unlocks "can my Node/Go service call it?" without porting the core — and the
core must stay zero-dependency, so this is a separate optional extra. ~2 days.

### 3.2 `inspeximus import --from mem0|zep` (item 8)
Anti-lock-in is the loudest unanswered complaint in the field, and nobody ships a migration path. It is
a feature and an outreach story at once. ~2 days.

### 3.3 Async API + OpenTelemetry hooks (item 10)
`async def` wrappers plus an optional `tracer=` with a no-op default. Blocking for anyone inside
FastAPI, cheap, procurement-visible. ~1 day.

---

## Phase 4 — the moat play

### 4.1 The cross-vendor benchmark harness (item 9)
*Why: 33 threads ask how to measure. `benchmarks/memops` (pre-registered, published with its null),
RAMR, `claims_audit.py` and `governance_audit.py` all exist. Vendors running their own leaderboards is
the field's open sore, and the cross-vendor slot is the one nobody owns.*

Package them as **"run this against YOUR store"**: a store-agnostic adapter interface, our arms as
reference implementations, and a result format that carries its own provenance.

- **Acceptance:** a third party runs it against a store we have never seen and gets a result we did not
  hand-tune. Until that happens it is not a product, it is our test suite with a nicer name.
- Cost: ~1 week. Highest ceiling, and the only item that compounds.

---

## Explicitly NOT building (from the briefing, with the reason)

- **A TypeScript rewrite of the core** — the large npm numbers are cloud clients; every open-source TS
  memory SDK is under 100 downloads/week.
- **A hosted dashboard** — Cognee gives its full UI away. Months of work for parity on a non-moat.
- **Graph/entity extraction, or anything with an LLM on the write path** — that is precisely the tax we
  win by not paying (MemOps: 12 minutes of write cost versus 0 seconds).
- **LOCOMO leaderboard chasing** — vendor-run harnesses with unreproducible numbers. Ship 4.1 instead.

---

## Owner decisions this plan waits on

1. **Rename** — the single highest-leverage move in the star dataset was `embedchain` → `mem0`
   (5 → 1,998 stars/day), and we carry an eight-way name collision. Standing call is "no rename". If it
   is going to change, it should change **before** Phase 0 ships, because 0.1 and 0.2 both bake the name
   into install commands and package registries. **This is the one decision that gates the plan.**
2. **Elara's vault links** — 551 links across 121 notes. Keep, or strip.
3. **Reddit / EDRN / Marat** — unchanged from the briefing; not on this plan's critical path.

---

## How we work through it

One item at a time, each with its own small reversible commit and its acceptance test run before the
next begins. Anything outward — a docs PR, a listing, a feature page, a benchmark result — goes through
validate → storm → audit → verify first, no exceptions. If an acceptance test fails, the item is not
done, and we say so rather than moving on.

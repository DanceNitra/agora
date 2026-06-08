# AGORA 2.0 — The Epistemic Engine

*A breakthrough plan to upgrade the Agentic OS + vault + agents — from a research-content
generator into a self-improving engine that builds a reasoned model of knowledge.*

---

## 1. Where we honestly are

We built a self-sustaining research OS: grounded cross-field research (OpenAlex/arXiv), a semantic
vault (3090 embeddings, gaps, bridges), pairwise collaboration + an orchestrated pipeline,
verification, a quality gate, and a two-way Telegram channel that controls both the agents and Claude
Code. Impressive machinery.

**But the honest signal is low:** only ~1 in 6 agent findings survives fact-checking. The pipeline
produces *plausible syntheses that over-reach*. The system **generates** a lot but **knows** little
more than before — findings are one-off, nothing compounds, and the vault grows as a pile of text,
not as understanding. Verification protects the vault, but it is filtering a low-grade stream.

**So the breakthrough is NOT more features (more sources, more agents, faster, prettier).**
The breakthrough is to raise the *epistemic quality* and make knowledge *compound*. Three shifts:

| From | To |
|---|---|
| synthesize the literature | **test hypotheses against evidence** (agents as scientists) |
| a pile of searchable notes | **a reasoned knowledge graph** (a vault that thinks) |
| one-off generation | **compounding research programs** (an OS that gets smarter) |

This is exactly the vault's own thesis — *Consilience*, *Map–Territory*, *Epistemic Dependency
Graph*, *Vault Theory of AGI*. AGORA 2.0 **builds the user's own theory**, it doesn't bolt features on.

---

## 2. The vision: realize the Epistemic Dependency Graph

> The second brain stops being a place where text is stored and becomes a **model of what is known,
> how strongly, on what evidence, and where it is uncertain or self-contradictory** — which the
> agents extend by doing science, and which the user can interrogate from their phone.

Three pillars + one capability.

### Pillar 1 — The vault that thinks (structured knowledge graph)
Today the semantic index finds *similar* notes. It cannot tell you what the vault *claims*, or where
claims *conflict*. Pillar 1 extracts structure:
- **`claim_extractor`** — an LLM distills each substantive note into atomic CLAIMS:
  `(subject, relation, object, confidence, source_note)`. Stored as a graph (SQLite + the embeddings).
- **`graph_reasoner`** — over that graph: surface **contradictions** (A vs ¬A across notes),
  **inferable edges** (A→B, B→C ⇒ test A→C), and **uncertain frontiers** (low-confidence / unsourced
  claims). These are the real research targets.
- **Interrogation** (Telegram/endpoint): *"what does my vault believe about X?"*, *"what does it
  contradict itself on?"*, *"what's the weakest load-bearing claim?"*
- **Why breakthrough:** the vault becomes a **world-model**, not a search box. Gaps/bridges stop being
  embedding-distance heuristics and become *epistemic* (a contradiction to resolve, a missing
  inference to make). This is the Epistemic Dependency Graph, literally.

### Pillar 2 — Agents as scientists (hypothesis → test → evidence)
Today an agent "states a finding grounded in a paper." That's book-reporting. Pillar 2:
- An agent generates a **testable hypothesis** from the graph (a missing edge, a contradiction, an
  uncertain claim) — *"A is isomorphic to B", "X causally precedes Y"*.
- It **tests** it on four fronts: (a) internal consistency with the graph, (b) semantic evidence in
  the vault, (c) real-paper support / refutation (OpenAlex), (d) reasoning or light computation.
- Output is a finding with **evidence, a confidence score, and an explicit falsifier** ("this is wrong
  if…") — not a citation. Voss verifies *the test*, not just the sentence.
- **Why breakthrough:** this is the jump from "summarize" to "discover," and it directly fixes the 1/6
  signal — findings now carry evidence, so far more survive (and the ones that don't are *informative*
  — a refuted hypothesis is real knowledge).

### Pillar 3 — The OS that learns (compounding)
Today nothing is learned from verification. Pillar 3 closes the recursive loop the project was always
reaching for:
- **Feedback:** verification verdicts become a training signal — which gap-types, source patterns, and
  agent approaches actually yield VERIFIED findings. Agents prefer fruitful patterns; standing/trust
  reflects *verified* output, not activity.
- **Research programs:** a topic the user cares about gets a **sustained multi-cycle thread** —
  hypothesis → finding → the next sharper question → … — accumulating into one deep, coherent vault
  document instead of scattered notes.
- **Metrics:** graph growth (claims, resolved contradictions, mean confidence) and verified-rate over
  time — the OS is *measurably* getting smarter. That trend line is the product.
- **Why breakthrough:** the system improves itself. That is the difference between a tool and an engine.

### Capability — Deep Reports (knowledge → deliverable)
From Telegram: *"deep report on X"* → the OS marshals the graph + verified findings + a fresh
hypothesis-test pass → a real, sourced, structured **report** (a deliverable, not a chat reply). The OS
stops only *knowing* and starts *producing*.

---

## 3. Phased plan (sequenced so each phase pays off alone)

- **Phase 1 — Knowledge graph (foundation).** `claim_extractor` over the vault → claims graph;
  `graph_reasoner` (contradictions / inferable edges / uncertain frontiers); `GET /brain/graph-*`
  endpoints + Telegram `believe <topic>` / `contradictions`. *Payoff alone:* the user can finally ask
  the vault what it actually knows and where it conflicts.
- **Phase 2 — Hypothesis-test loop.** Agents draw hypotheses from the graph's frontiers, run the
  four-front test, emit evidence+confidence+falsifier; Voss grades the test. Pipeline rewired around
  this. *Payoff:* verification pass-rate jumps; findings become trustworthy.
- **Phase 3 — Compounding.** Verification→behavior feedback; verified-weighted standing; sustained
  research programs; the growth dashboard. *Payoff:* the OS visibly improves week over week.
- **Capability — Deep Reports** can ship after Phase 2 (it just needs the graph + verified findings).

---

## 4. Recommendation

**Lead with Phase 1 (the knowledge graph).** It is the substrate Pillars 2–3 stand on, it is the
single most direct realization of the user's *Epistemic Dependency Graph*, and it pays off immediately
on its own (interrogate the vault, find its contradictions). First concrete build:
`claim_extractor` over the current ~5.6k notes (local 3090 for embeddings, deepseek for extraction),
a claims table, and a `contradictions` + `believe <topic>` Telegram command.

> One line: **stop generating content, start building a mind.**

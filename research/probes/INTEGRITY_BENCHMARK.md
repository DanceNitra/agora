# Agent-memory integrity benchmark (open, cross-system, run-it-yourself)

Recall benchmarks (LoCoMo, LongMemEval, MemoryAgentBench) ask *did the store retrieve the right fact*. This
one asks a different question the recall evals skip: **integrity** — which version of a fact wins, whether a
corrected value can be undone on command, whether a restatement resurrects a retired value. It runs the same
adversarial fixture through several memory systems in their **native config** and publishes the matrix
whichever way it falls. If a number here is wrong, the harness is right next to it — run it, or add your system.

This exists because a sharp r/RAG reviewer made the fair point that self-scoring on home fixtures is
unfalsifiable. So: native configs, a shared judge that never sees ground truth, and results published even
where mnemo does **not** win.

### What this benchmark does and does NOT claim (read first)

- It measures **integrity** (which version wins, can you undo it, can you prove erasure), **not recall quality**.
  We do **not** claim mnemo retrieves better than mem0/Zep; on the one recall-adjacent cell here (conflict
  fidelity) mnemo *ties* a naive verbatim baseline. A fair recall-accuracy comparison (LoCoMo / LongMemEval,
  equal budget) is the **open frontier column** — until it is filled, treat "integrity" as one axis among
  several, not an overall ranking.
- The real, hard-to-copy property underneath every cell is **no LLM on the write path → determinism**. Revert
  and cross-surface erasure are *operations* a competitor could add in a sprint; determinism they cannot add
  without abandoning their extraction architecture. That mechanism, not any single number, is the through-line.
- The individual properties are **not new** — deterministic supersession/revert is belief revision (AGM 1985)
  and truth-maintenance (Doyle 1979); provable erasure is the machine-unlearning / GDPR-Art.17 verification
  literature; the poison/re-injection attack is the MINJA line. What is fresh here is the **cross-system
  measurement** on today's shipping libraries, not the mechanisms. We credit the prior art in each cell.

## Methodology (the same for every system)

- **Native config, no tuning in our favor.** mem0 runs on its recommended stack (gpt-4o-mini +
  text-embedding-3-small); Graphiti runs against a live neo4j with its own LLM pipeline; mnemo runs local.
- **Shared judge.** One OpenAI model reads each system's **full memory state** (`get_all` / all valid facts,
  not just top-k search) and extracts the current value. It never sees the ground truth beyond the two
  candidate tokens, so it can also answer "unclear". Feeding the full state isolates the *integrity* question
  (did the operation change the state) from *retrieval quality* (a different axis we do not test here).
- **Honest reading.** A store that keeps the corrected value when told "go back" is **not wrong** — it simply
  lacks that operation. We report a **capability** difference, never "system X is bad".
- Small n (OpenAI cost). Directional, not a leaderboard. Re-run with a larger `--n` if you want tighter CIs.

## Cell 1 — value-obscuring revert  (`integrity_bench_revert.py`)

Store a value, correct it, then issue an **unmarked** revert that names no value ("go back to what we had",
"roll back the change", "undo it"). Does the current answer return to the OLD value?

    add   "the {entity} is {A}."
    add   "correction: the {entity} is now {B}."
    revert "{unmarked revert, no value}"
    ask   "what is the current {entity}?"   ->   A = revert honored, B = revert ignored

**Symmetric instrument (fairness fix 2026-07-11).** An earlier version scored mnemo *mechanically* from its own
ledger while mem0/Graphiti went through the LLM judge — an asymmetric instrument a pre-publication red-team
caught. Now **every system is read by the same ground-truth-blind LLM judge on its own native retrieval
surface**. The fix dropped mnemo's headline from a flattering 1.00 to 0.75.

| system | revert success (n=20) | 95% CI | what happens |
|---|---|---|---|
| **mnemo** (route/revert) | **0.75** | [0.53, 0.89] | intent router restores the predecessor from the version ledger; 5/20 of mnemo's own recall surface still reads ambiguous to the neutral judge |
| mem0 2.0.11 (native) | 0.20 | [0.08, 0.42] | no revert operation — the "go back" utterance mostly isn't even stored as a fact, so the corrected value is retained (A=4, B=11, 5 unclear) |
| Graphiti (native, live) | 0.00 | [0.00, 0.16] | no revert operation — keeps the corrected value; bitemporal invalidation fires on named contradictions, not on an unnamed "go back" (A=0, B=11, 9 unclear) |

Reading: value-obscuring revert (undoing a correction from a natural-language command that names no value) is a
capability only mnemo exposes here. mem0 and Graphiti correctly retain the corrected value; they just have no
channel to undo it on command. Under a fair instrument even the system built for it clears only 0.75, not 1.00 —
and the CIs on mnemo [0.53, 0.89] and mem0 [0.08, 0.42] do not overlap, so the capability gap survives at n=20.

**Prior art (this is a known-hard property, not a new axis).** Undo-and-consistency-under-update is belief
revision (AGM, 1985), truth-maintenance systems (Doyle, 1979), and bitemporal databases (Snodgrass → SQL:2011).
The 2026 agent-memory benchmark wave — MemConflict (2605.20926), BEAM (2510.27246), TOKI (2606.06240),
STALE (2605.06527), Supersede (2606.27472), plus MemoryAgentBench (2507.05257) and LongMemEval (2410.10813) —
tests *which of two conflicting facts wins*. None tests an **unmarked revert command** or an **adversarial
echo-resurrection**; that narrow, adversarial, command-driven cut is what this harness measures.

The benchmark also improved mnemo: it surfaced that `route()` missed "roll back" (mnemo was 0.80) — fixed in
0.7.11.

## Run it / add your system

    # free, local only:
    python research/probes/integrity_bench_revert.py --systems mnemo

    # includes paid backends (needs OPENAI_API_KEY in server/.env; Graphiti needs a neo4j at bolt://localhost:7687):
    python research/probes/integrity_bench_revert.py --systems mnemo,mem0,graphiti --n 20

Adding a system = one adapter function with the interface `(reset, add(text), revert(text), full memory state
for the judge)`. PRs welcome; we publish whatever it shows.

## Cell 2 — echo resistance  (`integrity_bench_echo.py`)

Store a value, correct it, then **restate the retired value** (an echo — benign repetition or an injected
restatement). Does the current answer stay corrected, or does the stale value come back?

    add   "the {entity} is {A}."
    add   "correction: the {entity} is now {B}."
    echo  "the {entity} is {A}."             # restate the retired value
    ask   "what is the current {entity}?"    ->   B = echo resisted (good), A = resurrected (bad)

**Two honest metrics, and the naive one flatters us — so we don't use it.** Counting "did the system return the
corrected value" would show mnemo 0.90 / mem0 0.80 / Graphiti 0.55 and imply Graphiti fails echo. It does not.
Measured under the same symmetric instrument as Cell 1 (n=20):

| system | resurrection rate (the attack, lower=better) | 95% CI | clean current-truth rate (answer clarity) |
|---|---|---|---|
| **mnemo** (echo_guard) | **0.00** | [0.00, 0.16] | 0.90 |
| mem0 2.0.11 (native) | **0.05** | [0.01, 0.24] | 0.80 |
| Graphiti (native, live) | **0.00** | [0.00, 0.16] | 0.55 |

The real finding: **no system systematically resurrects the stale value** — resurrection is at or near zero
across the board (mnemo 0/20, Graphiti 0/20, mem0 1/20 = 0.05; within noise, not a systematic failure). An
earlier probe of ours over-stated this failure mode; corrected here. Note mnemo's clean rate is 0.90, not a
suspiciously perfect 1.00 — under the fair instrument even mnemo's recall surface reads ambiguous to the judge
2/20 of the time. Where the systems actually differ is *answer clarity*: mnemo and mem0 hand back a single
current value; Graphiti, by bitemporal design, surfaces both the invalidated old edge and the valid new one, so
a naive reader (our judge, 9/20) sees ambiguity — that is a different retrieval contract, **not** a resurrection. If
your consumer resolves validity itself, Graphiti's behaviour is correct; if it just reads the top facts, the
ambiguity can bite.

This cell is the honest counterweight to the revert cell: on the attack that actually matters (resurrection),
mnemo does **not** win — every system lands at or near zero. Publishing that is the whole point.

## Cell 3 — conflict-consolidation fidelity  (`mab_official/run_mnemo_official.py`)

Not our fixture: **MemoryAgentBench FactConsolidation, Single-Hop** (arXiv:2507.05257), run on its own
published protocol (`agent_chunk_size=4096`, `retrieve_num=100`, gpt-4o-mini, temp 0.7). A long transcript
states many facts, some superseded later; the system ingests it, then answers a question whose correct answer
is the *final* value. This measures whether the memory **keeps the facts at all** under ingest load.

    ingest  <sh_6k transcript: ~228 facts, some later corrected>
    ask     "what is the current {entity}?"   ->   correct = the final value survived ingest

**Validation that the harness is faithful, not a home fixture:** our mem0 run reproduces mem0's *own published*
CR-SH number. Published ~18% (arXiv:2507.05257 Tab. 2); we measure 16% at n=100 (12.5% at n=40). Same
answerer, protocol, and data for every system.

| system | fidelity (final value survives ingest, n=100) | note |
|---|---|---|
| naive verbatim RAG | 0.87 | de-keyed append + recency; a non-product baseline |
| **mnemo** (verbatim store) | **0.85** | keeps every fact; answerer resolves the final value |
| long-context (no memory) | 0.83 | whole transcript in the prompt; the answerer ceiling |
| mem0 2.x (native extraction) | **0.16** | LLM extraction from 228-fact chunks drops most facts |

**Honest reading (the caveat is the point).** The real result is **~5× mem0**, and it is a claim about a
*class* of memory, not about mnemo's cleverness: **any verbatim store (mnemo 0.85, naive 0.87, raw long-context
0.83) is ~5× mem0's 0.16**, because mem0's LLM extraction destroys facts when it summarizes big chunks, while a
verbatim store keeps them. mnemo **ties the naive baseline** here — MAB's chunk-dump protocol hands mnemo no
per-fact keys, so its *supersession* mechanism is not even exercised (that needs the keyed atomic contract or
sh_32k/64k retrieval pressure). So the honest headline is **"deterministic verbatim memory beats lossy
LLM-extraction memory ~5×"**, with mnemo's keyed supersession as an additional integrity layer this particular
cell does not test. We publish the tie with naive next to the 5× so the frame can't be read as mnemo-only.

**This is a replication, not a discovery.** "Deterministic/verbatim memory beats LLM-freshness-tracking on
conflict resolution" and "a fair verbatim baseline ties or beats extraction memory once you add it" are both
already-published findings in the 2026 agent-memory-evaluation literature; we reproduce them on this harness and
cite them rather than presenting the 5× as novel. (Specific citations pending the citation-verification pass.)

## Cell 4 — verifiable forgetting  (`forget_verification_xsystem.py`)

Store several subjects, issue a delete for one, then look for the deleted value on **every** surface the store
exposes — not just the default query. A right-to-erasure (GDPR Art. 17) claim fails if the value is gone from
search but recoverable from a history log or the raw vector rows.

    add     subject_1 .. subject_k
    forget  subject_1
    check   query surface · enumerate-all surface · history DB · raw vector storage   ->   value must be gone from ALL

| system | erasure score (1.0 = gone on every surface, n=8) | where the deleted value survives |
|---|---|---|
| **mnemo** (`forget_subject`) | **1.00** | nowhere — query 0, enumerate 0, history 0, raw 0 |
| Graphiti (native, live) | 1.00 | nowhere (bitemporal invalidation + node delete) |
| mem0 2.x (native) | **0.625** | **history DB 8/8, raw vector store 4/8** — recoverable after "delete" |

**Reading.** mem0's delete clears the *query* surface, but the retired value stays readable in its history
database (8/8 runs) and, half the time, in the raw vector rows (4/8) — so an operator who must *prove* a value
was erased cannot, on mem0, without extra scrubbing. mnemo and Graphiti both erase across every surface. This
is a genuine capability difference (and the one honest place a competitor — Graphiti — ties mnemo), not a "mem0
is bad" claim: mem0 keeps history by design; that design is simply not erasure-provable out of the box.

**Prior art.** Right-to-be-forgotten is GDPR Art. 17 (2018) and the machine-unlearning literature (Cao & Yang
2015; Bourtoule et al. 2021, SISA). What this cell adds is the narrow, operational check that erasure holds on
*every* retrieval surface a real store exposes, not just the primary query.

## Cell 5 — poison at the retrieval surface (the realistic production contract)

Cell 2 fed every system its **full memory state** to a frontier judge and found no system resurrects — a tie.
But full-state-into-a-strong-judge is the competitor's *best* case, not production. In production a memory
returns **top-k retrieved entries** and a task LLM answers from only those. What decides correctness is then not
"can a judge resolve the contradiction" but **"does the retired value stay in the retrieved surface at all"** —
a property of the store, checkable with no LLM.

Fixture (synthetic, so no world-knowledge can confound it): plain re-assertion poison, no "correction" label.

    add "the {entity} is {A}."   add "the {entity} is {B}."   add "the {entity} is {A}."   # re-assert retired A
    retrieve top-k for "{entity}" ; read the surface -> current value

**The primary metric is LLM-free and deterministic:** does the poison value A appear in the retrieved top-k
surface? Raw surfaces are saved per system in `poison_realistic_surfaces_<system>.json` — re-score with `grep`,
no model needed. (A temp=0 reader column shows the downstream consequence.)

Two fixtures, both scoring the LLM-free `surface_clean` (poison value absent from the retrieved top-k): a
**synthetic** one (code-valued, un-confoundable, but so short that the LLM-extraction stores retrieve sparsely)
and a **real-entity** one (MemoryAgentBench pairs, where every system retrieves). mnemo and naive are LLM-free;
mem0/Graphiti ran on gpt-4o-mini.

| system | poison removed from surface (real-entity, n=6) | (synthetic, n=12) | how it behaves |
|---|---|---|---|
| **mnemo** (supersession + echo_guard) | **1.00** (6/6) | **1.00** (12/12) | retires A, echo_guard rejects the re-assertion → surface = `{B}` |
| naive verbatim RAG | 0.00 (0/6) | 0.00 (0/12) | recency surfaces the poison as the newest write |
| mem0 2.x (native) | 0.00 (**6/6 returned surfaces keep A**) | 0.00 (7/7 kept; 5/12 empty) | stores and returns both values |
| Graphiti (native, live) | **0.17** (1/6; 3/6 empty, rest inconsistent) | not scorable (12/12 empty*) | bitemporal: keeps the invalidated edge, or returns the wrong value |

`*` **Honest limitations (not swept under the rug).** The synthetic fixture is un-confoundable but so terse
that mem0 retrieved nothing 5/12 times and Graphiti built no searchable nodes at all (12/12 empty) — so we do
**not** claim a synthetic Graphiti score (an empty-retrieval "0.00" is an artifact, not "it keeps the poison").
On the real-entity fixture every system retrieves: mem0 kept the poison in **6/6** returned surfaces (a clean,
consistent result). Graphiti is **not cleanly scorable at this n**: it retrieved on only 3/6, and of those 3 one
was clean, one kept both, one returned only the retired value — so we report it as "1 of 3 non-empty surfaces
clean, n too small to state a rate", **not** a headline 0.17. Small n (budget); directional. Raw surfaces are
saved per system for independent re-scoring.

**Prior art.** The attack — re-asserting a retired value so it re-enters retrieval — is the memory-poisoning /
MINJA line (Dong et al., and the 2026 defense papers). What this cell adds is the cross-system measurement that a
deterministic supersession + echo_guard keeps the re-assertion out of the top-k surface entirely, rather than
relying on the reader to discount it. (Specific citations pending the citation-verification pass.)

**Reading.** Only mnemo removes the retired value from the retrieval surface: supersession retires A and
echo_guard rejects the re-assertion, so top-k returns `{B}` and the poison never reaches the reader —
correctness is independent of reader strength. A recency store (naive) surfaces the poison as the newest write;
mem0 stores and returns both; Graphiti keeps the invalidated edge. Whenever the surface still contains the
poison, a temp=0 reader is pulled to it (naive 11/12, mem0 5/7). This is a **reliability property** (the correct
value is the only thing retrieved), **not** a claim that competitors "fail" an abstract poison test — under a
strong full-state judge (Cell 2) they recover. Cells 2 and 5 together are the honest picture: competitors need
the reader to do the disambiguation; mnemo does it in the store.

**Scope (no overclaim).** This is EXACT re-assertion poison (same key) — the classic echo/MINJA restatement.
Paraphrased poison that changes the key is a harder, separate case where mnemo's exact-key echo_guard is weaker;
we do not claim that here.

## The landscape — is mnemo unique among the *top* systems, or only vs mem0/Graphiti?

The cells above measure three systems live. The fair question is whether mnemo's combination is special across the
*field*, not just against two incumbents. The table below is a **structural** survey of eleven widely-used
open-source agent-memory systems, read from their **published docs and source code** (every cell is sourced; this
is a code-reading, not a live benchmark — only mnemo / mem0 / Graphiti rows are measured above). Markers: `conf` =
confirmed in code/docs, `inf` = inferred, `unclear` = not found. **This section is pending the citation-verification
pass before publication** (see gate note).

Axes: **A** LLM on the write/ingest path · **B** deterministic recall · **C** verifiable erasure (removes from
*all* surfaces) · **D** revert/undo a correction on command · **E** runs with no vector/graph DB, no cloud, no LLM ·
**F** conflict handling (deterministic supersession vs LLM-mediated vs none).

| System | A. no LLM on write | B. determ. | C. verifiable erasure | D. revert | E. zero-dep | F. conflict handling |
|---|---|---|---|---|---|---|
| **mnemo** | **YES** | **YES** | **YES** (all surfaces, measured) | **YES** (measured) | **YES** | deterministic key supersession + echo_guard |
| mem0 | no (LLM extract) | no | partial — prev_value kept in history | no | no | keep both, LLM ranks at recall |
| Zep / Graphiti | no (LLM graph) | no | partial — invalidate, not delete | no | no | temporal invalidation, edge retained |
| Letta (MemGPT) | no (LLM tool edits) | no | partial/unclear | unclear | no | LLM overwrites block |
| Cognee | no (LLM extract) | no | partial/unclear | unclear | no | usage reweight, not correction |
| Memary | no (LLM triplets) | no | no/unclear | unclear | no | append, no supersession |
| claude-mem | no (LLM compress) | no | unclear/weak | unclear | no | append session summaries |
| Memobase | no (LLM merge) | no | partial | unclear | no | LLM emits UPDATE vs APPEND |
| MemoryScope | no (LLM workers) | no | partial — `EXPIRED` flag, not purge | no | no | LLM marks contradiction EXPIRED |
| LangMem | partial (raw CRUD only) | partial | partial | no | no | LLM reconciles (manager path) |
| agentmemory (classic) | **YES** | yes | yes (single-store hard delete) | no | no | none (upsert) — **repo deleted / abandoned** |
| txtai (as memory) | **YES** | yes | yes (id-keyed, all indexes) | no | partial (heavy ML stack) | overwrite-by-id, no detection |

**What the field survey shows (honest reading, and its limits).** Eight of the eleven put an LLM on the write
path, which is why their recall is nondeterministic and their conflict handling is the LLM's judgment rather than
a rule. Note the axes are **not fully independent**: deterministic recall (B) and deterministic supersession (F)
largely *follow from* having no LLM on the write path (A), so the honest count is roughly **two orthogonal things
— no-LLM-on-write, and the two explicit operations (revert D, cross-surface erasure C)** — not five separate wins.
Two of those are held by **essentially no one on this survey**: a **revert-to-predecessor command** (column D was
**not found** in the docs/code of any surveyed system — a from-docs read cannot prove a capability is *absent*,
only that it is undocumented) and a **provable cross-surface erasure exposed as a primitive** (mem0 keeps
`prev_value`, Graphiti invalidates by design, MemoryScope only flags `EXPIRED`). The systems that *do* avoid an
LLM on the write path — classic **agentmemory** (deterministic, but abandoned, repo deleted, no supersession or
revert), **txtai** (a clean deterministic embeddings store with a real id-keyed delete, but no revert and no
supersession beyond overwrite), and **partially LangMem** — each still lack the rest.

So the honest, sourced claim is **not** "mnemo beats everyone" and **not** a bare "ONLY": it is that **across this
11-system survey (3 live-measured, 8 read from docs), mnemo is the only one that combines all of these integrity
properties at once — and each property alone is shared by some named system** (deterministic no-LLM stores: txtai,
agentmemory; temporal conflict handling: Graphiti, MemoryScope; etc.). Because we chose these axes and host the
benchmark, the combination is only meaningful if you also read the recall-quality frontier column (still open) —
integrity is the corner mnemo occupies, not a total-ranking crown. The mechanisms are textbook (AGM belief
revision, Doyle truth-maintenance, bitemporal DBs); the cross-system *measurement* is what is fresh.

## Recall quality — the LOCOMO number (standalone, LLM-free)

Everything above is *integrity*. Buyers also ask "what's your recall number?" — so here it is, measured on the
standard **LOCOMO** benchmark (arXiv:2402.17753), with the shipped tuned recipe (semantic embedder + hybrid RRF
+ a soft speaker prefilter via `recall(prefer=...)`; see `mnemo/examples/recall_recipe_locomo.py`).

We report **retrieval-recall**, not an LLM-judged end-to-end QA score, on purpose: retrieval-recall is
deterministic, LLM-free, free to run, and **un-gameable** — it asks the one thing a memory's job actually is,
*did the gold supporting turn get retrieved into the top-k?*, with no answerer or judge to inflate it. (An
LLM-as-judge QA number is judge-dependent and not comparable across harnesses; we do not publish one as a
headline.)

| metric (mnemo, tuned recipe, k=25) | value | n |
|---|---|---|
| **recall@25 (any evidence turn retrieved)** | **0.783** | 1536 |
| **recall@25 (all evidence turns retrieved)** | **0.648** | 1536 |

By category (any): open 0.80 · temporal 0.81 · inference 0.59 · multi-hop 0.79 (multi-hop is 55% of the set).

**Honest scope.** This is mnemo's **own** number, not a head-to-head: mem0/Zep publish LLM-judged end-to-end QA
(≈0.67 / 0.71), a *different metric* on a *different harness*, so it cannot be directly compared to a
retrieval-recall figure. A true comparison requires running those systems through **this** harness; we have not
done that (it needs their pipelines + a paid LLM), so we make no "beats them on recall" claim here. What we do
claim is narrow and checkable: **mnemo retrieves a supporting turn for 78% of LOCOMO questions, deterministically
and for free — run `research/probes/retrieval_recall_locomo.py` and reproduce it.**

## Planned cells (harness shape is the same)

- **atomic-keyed conflict** — the contract where mnemo's supersession IS exercised (the coding-agent plugin
  contract), to show the mechanism the chunk-dump protocol of Cell 3 cannot.

Every number traces to a probe in this folder. The recall-quality axis is now measured standalone (the LOCOMO
section above: mnemo retrieval-recall@25 = 0.78 any / 0.65 all, LLM-free); we still make no cross-system recall
claim until competitors are run through the identical harness.

---

*Gate status: the numbers in Cells 1–2 shipped after the fairness-fix red-team; Cells 3–5 are added
2026-07-18 and must clear the full validate→storm→audit→verify frame before this file is published outward.*

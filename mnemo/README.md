<div align="center">

# Mnemosyne · `mnemo`

**A memory layer for AI agents — the one that already runs an autonomous research OS over ~5,800 notes.**

*Memory is the mother of the Muses. An agent with no memory has no ideas.*

</div>

---

`mnemo` is the recall + consolidation core of [Agora](https://github.com/DanceNitra/agora) — an
autonomous research system — distilled into **a single file with no required dependencies**. It does
the four things agent memory actually needs, the way that held up running in production for weeks.

Most "agent memory" libraries are demos. This one is extracted from a system that has used it daily
to curate a 5,800-note knowledge base, and whose consolidation behaviour we have **measured**, not
assumed (see *Provenance* below).

## Install

```bash
# single file, zero dependencies
curl -O https://raw.githubusercontent.com/DanceNitra/agora/main/mnemo/mnemo.py
```

## Use

```python
from mnemo import Mnemo

m = Mnemo("memory.json")                       # persists to JSON; or Mnemo("memory.json", embed=my_model)

m.remember("Pre-trend tests catch only ~31% of fatal DiD bias.", tags=["causal"], value=3)
m.recall("difference in differences", k=5)     # relevance × value — high-value memories surface first
m.consolidate(keep=200)                        # the "dream" pass: rank, link dups, mark stale
m.contradictions()                             # flag incompatible memories for REVIEW (never deletes)
m.value_by_cohort()                            # value reported per tag/time-block, not per memory
```

Bring any text→vector function as `embed=` for semantic recall; with none, `mnemo` falls back to a
forgiving lexical match so it **runs anywhere, today**.

## The four operations

| op | what it does |
|---|---|
| `remember(text, tags, value)` | **append-only** raw capture, stamped with an absolute UTC time — never edited afterward |
| `recall(query, k)` | **value-ranked** retrieval: relevance × the memory's accrued value, so important memories beat merely-similar ones |
| `consolidate(keep)` | the **dream pass**: value-rank under a keep-budget, link near-duplicates, mark the low-value surplus stale — it only *adds* a derived layer |
| `contradictions()` | flag mutually-incompatible **related** memories (similarity-gated) for human review |

## Five rules it won't break (each one cost us to learn)

1. **Raw capture is immutable.** Consolidation adds links and markers; it never overwrites the
   source. This is what stops the slow accuracy drift of LLM-rewritten memory.
2. **Absolute timestamps at write time.** Relative/derived times rot the moment they're consolidated.
3. **Value-ranked, capacity-aware consolidation.** Retention tracks *value*, not recency.
4. **Value is reported at the cohort level** (tag / time-block), never per-memory.
5. **Contradictions are flagged, never auto-resolved.** Silent rewrites destroy trust in the whole
   memory.

## Provenance — why these rules, with receipts

`mnemo`'s design isn't taste; it's what Agora's lab *measured*:

- **Value-ranked consolidation** — under a keep-budget, ranking *what to keep* by value beats
  FIFO/random, and the advantage **scales super-linearly as the budget shrinks** (≈1.8× at half
  budget → ≈4× at one-eighth), surviving heavy estimation noise.
- **Cohort-level value** — per-memory outcome attribution is **statistically underpowered at n-of-1**
  (the best proxy reached only ~0.36 power at realistic sample sizes); the cohort is where the
  signal lives. Hence rule 4.
- **Contradiction detection** runs in production over the 5,800-note vault; the lesson that it must
  *flag, not auto-edit* (rule 5) is why silent rewrites are forbidden.

(Methods + numbers live in the Agora track record: <https://dancenitra.github.io/agora/>.)

## Status

`v0.1` — the core, honest and runnable. Roadmap: pluggable vector stores, a hosted tier, an MCP
server so any Claude/agent client can use `mnemo` as its memory. Open-core; the core stays free.

MIT-licensed · part of [Agora](https://github.com/DanceNitra/agora).

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

m.remember("Pre-trend tests catch only ~31% of fatal DiD bias.", tags=["causal"], value=3, mtype="semantic")
m.recall("difference in differences", k=5)     # relevance × value, decayed by the memory's per-type half-life
m.consolidate(keep=200)                        # the "dream" pass: hubs, dedup, STATE-TOGGLE, keep-budget
m.consolidate_clusters(threshold=15)           # cluster-TRIGGERED: consolidate only a topic that's grown dense
m.contradictions()                             # flag incompatible memories for REVIEW (never deletes)
m.value_by_cohort()                            # value reported per tag/time-block, not per memory
```

Bring any text→vector function as `embed=` for semantic recall; with none, `mnemo` falls back to a
forgiving lexical match so it **runs anywhere, today**.

## Use it as an MCP server (any Claude / Cursor / agent client)

`mnemo` ships an [MCP](https://modelcontextprotocol.io) stdio server so any MCP-compatible agent can
use it as long-term memory — `remember` (with a per-type decay prior), value-ranked `recall`,
`consolidate`, `consolidate_clusters`, `contradictions`, `value_by_cohort`. `mnemo.py` stays
zero-dependency; only the server needs the SDK:

```bash
pip install "mcp[cli]"
curl -O https://raw.githubusercontent.com/DanceNitra/agora/main/mnemo/mnemo.py
curl -O https://raw.githubusercontent.com/DanceNitra/agora/main/mnemo/mnemo_mcp.py
MNEMO_PATH=./agent_memory.json python mnemo_mcp.py      # speaks MCP over stdio
```

Register it with a client — e.g. Claude Code (`.mcp.json`) or Claude Desktop
(`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "mnemo": {
      "command": "python",
      "args": ["/abs/path/to/mnemo/mnemo_mcp.py"],
      "env": { "MNEMO_PATH": "/abs/path/to/agent_memory.json" }
    }
  }
}
```

For **semantic** recall, point it at any OpenAI-compatible embeddings endpoint via
`MNEMO_EMBED_URL` / `MNEMO_EMBED_MODEL` / `MNEMO_EMBED_KEY`; with none set it uses the lexical
fallback. The agent then calls `recall(query)` before reasoning and `remember(fact)` as it learns —
its memory is value-ranked and append-only, not a recency buffer.

## The four operations

| op | what it does |
|---|---|
| `remember(text, tags, value, mtype)` | **append-only** raw capture, absolute UTC time, never edited; `mtype` ∈ {episodic, semantic, procedural} sets the **decay prior** (events fade fast, durable facts slow, rules barely) |
| `recall(query, k)` | **value-ranked** retrieval: relevance × value, **decayed by the memory's per-type half-life** (access resets the clock), so important durable memories beat both merely-similar and stale ones |
| `consolidate(keep)` | the **dream pass**: flag universal-matcher *hubs*, link near-duplicates, apply the **state-toggle guard** (a polarity clash supersedes, doesn't merge), supersede the low-value surplus — only *adds* a derived layer |
| `consolidate_clusters(threshold)` | **cluster-triggered** consolidation: consolidate a semantic cluster only once it's grown past `threshold` — sparse topics keep their raw episodes, dense ones don't grow unbounded |
| `contradictions()` | flag mutually-incompatible **related** memories (similarity-gated) for human review |

## Five rules it won't break (each one cost us to learn)

1. **Raw capture is immutable.** Consolidation adds links and markers; it never overwrites the
   source. This is what stops the slow accuracy drift of LLM-rewritten memory.
2. **Absolute timestamps at write time.** Relative/derived times rot the moment they're consolidated.
3. **Value-ranked, type-aware decay.** Retention is `value × a per-type half-life`, not recency or
   access-frequency alone. A *uniform* access-reset clock keeps merely-*popular* memories while a
   load-bearing-but-cold fact — queried once a month, prevents a destructive action — starves; we
   measured exactly that failure. The fix is that the half-life is set by **kind**, not by read
   count: episodic events fade in days, semantic facts in months, procedural rules barely at all. A
   cold-but-critical fact survives by being **typed** semantic/procedural (long half-life × its high
   value), not by frequent reads; access only resets the clock *within* a type's window.
4. **Value is reported at the cohort level** (tag / time-block), never per-memory.
5. **Contradictions are flagged, never auto-resolved.** Silent rewrites destroy trust in the whole
   memory.

## Provenance — why these rules, with receipts

`mnemo`'s design isn't taste; it's what Agora's lab *measured*:

- **Semantic recall beats keyword recall, and the gap widens with scale** — on the ~6,000-note
  vault, embedding-based `recall@5` was **0.94 vs 0.63** lexical in our latest known-item benchmark
  (and ≈3.8× on the harder full-corpus probe). The embedder is the real lever at scale; the lexical
  overlap match is the zero-dependency *floor* that still runs anywhere. (Honest footnote: pruning
  universal-matcher *hub* notes lifts **lexical** recall ~20% only when a store is link-spammed, and
  does **not** move semantic recall — it's a lexical/hybrid optimisation, not a headline.)
- **Value-ranked consolidation** — under a keep-budget, ranking *what to keep* by value beats
  FIFO/random, and the advantage **scales super-linearly as the budget shrinks** (≈1.8× at half
  budget → ≈4× at one-eighth), surviving heavy estimation noise.
- **Retention must blend value with recency, not decay on access alone** — we simulated a
  half-life-with-access-reset policy (a *popularity* signal) against a value-aware blend under a
  shrinking budget, with value made deliberately anti-correlated with access-frequency for a
  load-bearing-but-cold subset. At a 30% keep-budget the access-decay policy retained only **2.8%**
  of the high-value/low-frequency memories and **20%** of total value, vs **100%** and **64%** for
  the blend — about **3× more value kept** (the gap persists, ≈2.2× retained value, even at a 7%
  budget). Pure access-frequency decay starves the rarely-queried-but-critical memories; forgetting
  must consume an explicit value channel *separate from* access recency. (Agora Lab `19d802`.)
- **Cohort-level value** — per-memory outcome attribution is **statistically underpowered at n-of-1**
  (the best proxy reached only ~0.36 power at realistic sample sizes); the cohort is where the
  signal lives. Hence rule 4.
- **Contradiction detection** runs in production over the 5,800-note vault; the lesson that it must
  *flag, not auto-edit* (rule 5) is why silent rewrites are forbidden.

(Methods + numbers live in the Agora track record: <https://dancenitra.github.io/agora/>.)

## Status

`v0.1` — the core, honest and runnable, **now with an MCP server** so any Claude/agent client can use
`mnemo` as its memory (above). Roadmap: pluggable vector stores, a hosted tier. Open-core; the core
stays free.

MIT-licensed · part of [Agora](https://github.com/DanceNitra/agora).

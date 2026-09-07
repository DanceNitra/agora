<div align="center">

# Inspeximus · `inspeximus`

**The self-correcting memory layer for AI agents.**

*Memory is the mother of the Muses. An agent with no memory has no ideas.*

`pip install inspeximus` · [PyPI](https://pypi.org/project/inspeximus/) · [Hugging Face](https://huggingface.co/Danchi17/inspeximus) · [DOI 10.5281/zenodo.21128549](https://doi.org/10.5281/zenodo.21128549) · MIT · v0.7.19

Built by **[Rastislav Drahoš](https://github.com/DanceNitra)** — founder of [Agora](https://github.com/DanceNitra/agora), an autonomous research organization.

</div>

---

## What is inspeximus?

**inspeximus is a zero-dependency Python memory layer and MCP server for AI agents.** It handles the full lifecycle of a fact: store it, correct it, retire the old value, and audit the history.

Most "agent memory" libraries are demos. This one is extracted from a system that has used it daily to curate a 6,000-note knowledge base, and whose consolidation behaviour we have **measured**, not assumed.

**The problem it solves:** Agent memory must handle the full lifecycle of a fact — store it, correct it, retire the old value, and audit the history. When a fact is corrected, can the store *undo* the correction on command? Does restating a retired value *resurrect* it? Most memory layers fail at these integrity questions.

**The mechanism:** Deterministic supersession keys, echo guards, erasure certificates, and value-ranked recall — no LLM on the write path, no similarity threshold, no coin-flips.

**The proof:** Measured against mem0 and Graphiti in their native configs with a shared, ground-truth-blind judge. See the [benchmark](#benchmark) below.

---

## Benchmark: correction is a first-class operation

Any memory layer can store a fact and retrieve it. The harder, less-benchmarked property is **integrity**: when a fact is corrected, can the store *undo* the correction on command, and does restating a retired value *resurrect* it?

We measured inspeximus against mem0 and Graphiti in their **native configs** with a shared, **ground-truth-blind** judge:

| value-obscuring revert · undo a correction from an unmarked "go back" (n=20) | success | 95% CI |
|---|---|---|
| **inspeximus** (route/revert) | **0.75** | [0.53, 0.89] |
| mem0 2.0.11 (native, gpt-4o-mini) | 0.20 | [0.08, 0.42] |
| Graphiti (native, live neo4j) | 0.00 | [0.00, 0.16] |

Only inspeximus exposes a channel to undo a correction on command. We lead with the cell we *don't* win: **echo-resurrection is a tie** — all three defend against a restated stale value. This is a narrow, adversarial, command-driven cut, not a general "inspeximus is better" claim; run it yourself or add your system.

**EU AI Act readiness:** inspeximus ships tamper-evident write receipts, erasure certificates, and governance reports — the record-keeping evidence Article 12/19 requires. See [governance_report()](#governance-report) and [erasure certificates](#erasure-certificates).

---

## Install

```bash
# single file, zero dependencies
curl -O https://raw.githubusercontent.com/DanceNitra/agora/main/inspeximus/inspeximus.py

# or via PyPI
pip install inspeximus
```

## Use

```python
from inspeximus import Inspeximus

m = Inspeximus("memory.json")                       # persists to JSON; or Inspeximus("memory.json", embed=my_model)

m.remember("Pre-trend tests catch only ~31% of fatal DiD bias.", tags=["causal"], value=3, mtype="semantic")
m.recall("difference in differences", k=5)     # relevance × value, decayed by the memory's per-type half-life
m.consolidate(keep=200)                        # the "dream" pass: hubs, dedup, STATE-TOGGLE, keep-budget
m.consolidate_clusters(threshold=15)           # cluster-TRIGGERED: consolidate only a topic that's grown dense
m.contradictions()                             # flag incompatible memories for REVIEW (never deletes)
m.value_by_cohort()                            # value reported per tag/time-block, not per memory
```

Bring any text→vector function as `embed=` for semantic recall; with none, `inspeximus` falls back to a forgiving lexical match so it **runs anywhere, today**.

---

## Use it as an MCP server (any Claude / Cursor / agent client)

`inspeximus` ships an [MCP](https://modelcontextprotocol.io) stdio server so any MCP-compatible agent can use it as long-term memory — `remember` (with a per-type decay prior), value-ranked `recall`, `consolidate`, `consolidate_clusters`, `contradictions`, `value_by_cohort`, `forget` (verified erasure).

```bash
pip install "mcp[cli]"
curl -O https://raw.githubusercontent.com/DanceNitra/agora/main/inspeximus/inspeximus.py
curl -O https://raw.githubusercontent.com/DanceNitra/agora/main/inspeximus/mcp.py
INSPEXIMUS_PATH=./agent_memory.json python mcp.py      # speaks MCP over stdio
```

Register it with a client — e.g. Claude Code (`.mcp.json`) or Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "inspeximus": {
      "command": "python",
      "args": ["/abs/path/to/inspeximus/mcp.py"],
      "env": { "INSPEXIMUS_PATH": "/abs/path/to/agent_memory.json" }
    }
  }
}
```

For **semantic** recall, point it at any OpenAI-compatible embeddings endpoint via `INSPEXIMUS_EMBED_URL` / `INSPEXIMUS_EMBED_MODEL` / `INSPEXIMUS_EMBED_KEY`; with none set it uses the lexical fallback.

---

## Key features

### Deterministic correction (supersession)

`remember(key=...)` retires the old value deterministically — no similarity threshold, no LLM. A corrected fact stays corrected, even if the old value is re-stated later (`echo_guard`).

### Verifiable erasure (GDPR / EU AI Act)

`forget()` truly deletes — hard-removes the matched records *and* scrubs their ids from every survivor's links + toggle pointers + caches. `forget_subject()` handles right-to-erasure with deletion tombstones. `erasure_certificate()` produces a portable, independently-verifiable proof.

### Poison-resistant recall

`recall(..., influence_only=True)` returns only memories that earned corroboration — a credited good outcome, or ≥2 distinct-source links. Measured: single-instance poison rank-1 hijack → **0%** on MiniLM/BGE/Contriever.

### Tamper-evident receipts

Every write is hash-chained and signed. `verify_writes()` checks the chain. `anchor()` produces a signed head commitment you can publish externally. `verify_consistency()` detects append-only violations.

### Governance reports

`governance_report()` gives a one-call snapshot: erasure/retention posture, tamper-evidence status, integrity counters — the summary a DPO/CISO or auditor asks for.

### Zero-dependency

One file, no required dependencies. Runs anywhere Python runs.

---

## The four operations

| op | what it does |
|---|---|
| `remember(text, tags, value, mtype, key)` | **append-only** raw capture, absolute UTC time, never edited; `mtype` ∈ {episodic, semantic, procedural} sets the **decay prior**. Optional `key` = a **deterministic (subject, relation) supersession key** |
| `recall(query, k, where=…)` | **value-ranked** retrieval: relevance × value, **decayed by the memory's per-type half-life**. Optional `where` = a **metadata pre-filter** |
| `consolidate(keep)` | the **dream pass**: flag universal-matcher *hubs*, link near-duplicates, apply the **state-toggle guard**, supersede the low-value surplus |
| `consolidate_clusters(threshold)` | **cluster-triggered** consolidation: consolidate a semantic cluster only once it's grown past `threshold` |
| `contradictions()` | flag mutually-incompatible **related** memories for human review |
| `forget(ids, where)` | the one op that **truly deletes** — hard-removes the matched records *and* scrubs their ids from every survivor's links + toggle pointers + caches |

---

## Five rules it won't break

1. **Raw capture is immutable.** Consolidation adds links and markers; it never overwrites the source.
2. **Absolute timestamps at write time.** Relative/derived times rot the moment they're consolidated.
3. **Value-ranked, type-aware decay.** Retention is `value × a per-type half-life`, not recency or access-frequency alone.
4. **Value is reported at the cohort level** (tag / time-block), never per-memory.
5. **Contradictions are flagged, never auto-resolved.** Silent rewrites destroy trust in the whole memory.

---

## Provenance — why these rules, with receipts

`inspeximus`'s design isn't taste; it's what Agora's lab *measured*:

- **Semantic recall beats keyword recall, and the gap widens with scale** — as the store grows to the ~6,000-note full corpus, lexical `recall@5` decays from **0.94** (small store) to **0.25**, while semantic **holds at ~0.65** — ≈**2.6×** at full scale.
- **Value-ranked consolidation** — under a keep-budget, ranking *what to keep* by value beats FIFO/random, and the advantage **scales super-linearly as the budget shrinks** (≈1.8× at half budget → ≈4× at one-eighth).
- **Retention must blend value with recency, not decay on access alone** — at a 30% keep-budget the access-decay policy retained only **2.8%** of the high-value/low-frequency memories vs **100%** for the blend.
- **Supersession needs a deterministic key, not embedding similarity** — a cosine-similarity classifier separating a *contradicted* fact from a *rephrased duplicate* scores **AUROC ~0.61** (near chance).

Full receipts: [`probes/INTEGRITY_BENCHMARK.md`](probes/INTEGRITY_BENCHMARK.md), [`probes/locomo_retrieval_map.py`](probes/locomo_retrieval_map.py), [`probes/agentpoison_influence_gate.py`](probes/agentpoison_influence_gate.py).

---

## Threat model & layered defense

inspeximus treats memory poisoning as a real threat, not a footnote. The defense is layered:

1. **Echo guard** — a restated retired value cannot resurrect a corrected fact.
2. **Influence gate** — `recall(..., influence_only=True)` returns only memories that earned corroboration.
3. **Slash** — when a memory is caught driving a bad outcome, it forfeits the entire accrued standing of that source.
4. **Warrant gate** — `credit_requires_warrant` blocks the self-graded-outcome loop.
5. **Tamper-evident receipts** — every write is hash-chained and signed.

Honest boundary: no defense makes poisoning impossible. The goal is to raise attacker cost until it's not worth it.

---

## The `second_brain` thinking layer

`second_brain_mcp.py` is a read-only MCP server over your notes. It finds relevant notes, coverage gaps, bridge candidates, and extractable claims — the thinking layer on top of your vault.

```bash
python second_brain_mcp.py   # reads NOTES_DIR, writes only its own index
```

| tool | returns |
|---|---|
| `index_status` | notes indexed, folder spread, resolved `NOTES_DIR` |
| `relevant_notes` | the `k` most relevant notes by relevance × accrued value |
| `coverage_gap` | the **negative space** of a question: top notes + a measured completeness score |
| `find_gaps` | isolated/under-linked notes + thin folders |
| `bridge_candidates` | distant notes that are semantically close = candidate connections |
| `extract_claims` | claim-like sentences from a note |
| `idea_methods` | a toolkit of named idea-generation recipes |

Dogfood result: pointed at the maintainer's own ~6,000-note vault, an agent using these tools caught a number in his *own* forecasting note inflated ~7× ("60-78%" vs the real ~6-11%).

---

## Self-maintaining (maintain.py)

The #1 second-brain frustration is **maintenance**, not capture. `maintain.py` finds dead `[[wikilinks]]`, orphan notes, stale notes, near-duplicate clusters, and a **vault health score**. It turns findings into **actions**: for each orphan it suggests which existing note to link it to.

```bash
python maintain.py   # runs a verified round-trip on a synthetic vault
```

---

## Status

`v0.7.19` — the core, honest and runnable, with two MCP servers (`mcp` for memory, `second_brain_mcp` for the thinking layer over your notes) and a deterministic supersession key. Roadmap: pluggable vector stores, a hosted tier. Open-core; the core stays free.

**Changelog:** [CHANGELOG.md](CHANGELOG.md) — every feature, every fix, with receipts.

MIT-licensed · part of [Agora](https://github.com/DanceNitra/agora).

<!-- MCP registry ownership proof -->
mcp-name: io.github.DanceNitra/inspeximus

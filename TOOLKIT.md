# Agora Memory Toolkit

Three zero-dependency tools, distilled from an autonomous research OS that runs over ~5,800 notes.
Each is one file you can copy, or `pip install` together. Each ships with a runnable, measured demo —
because the rule here is *measured, not assumed*.

| tool | one line | run the proof |
|---|---|---|
| **[mnemo](mnemo/)** | agent memory + a **self-maintaining** second brain (recall by value, consolidate, find dead-links/orphans/stale, suggest+apply links, health gauge) | `python mnemo/maintain.py` |
| **[ragfresh](ragfresh/)** | a **freshness/decay layer** for RAG/vector stores — keep/down-weight/refresh/prune by value×freshness, not recency | `python ragfresh/ragfresh.py` |
| **[nullcheck](nullcheck/)** | **is this number real, or just noise?** — null-simulation A/B + permutation test + peeking-inflation | `python nullcheck/nullcheck.py` |
| **[selfref](selfref/)** | **is your AI training on itself?** — measures collapse (data-mix) + lock (self-trust) risk for any system that learns from its own output | `python selfref/selfref.py` |
| **[quitkit](quitkit/)** | **when to quit a depleting effort** — a measured drawdown-exit threshold (θ≈0.6, an interior optimum), beats mining-to-depletion +239% | `python quitkit/quitkit.py` |
| **[idcheck](idcheck/)** | **is your causal/attribution number identified, or biased?** — audits each control by its graph role; proves a collider flips a correct estimate's sign | `python idcheck/idcheck.py` |
| **[goodhart](goodhart/)** | **how gameable is your proxy/metric?** — measures Goodhart fidelity decay (80%→20%) and how many independent metrics fix it (reward hacking / KPI drift) | `python goodhart/goodhart.py` |
| **[herdcheck](herdcheck/)** | **will your multi-agent system herd?** — measures when a crowd of agents collapses to one member's competence (popularity trap) and the fix | `python herdcheck/herdcheck.py` |

They share one idea: **keep / trust what survives contact with a null or with reality.** mnemo keeps
the memory that proves valuable; ragfresh keeps the chunk that's still fresh and worth its cost;
nullcheck keeps only the effect a no-effect null can't reproduce; selfref keeps a system anchored to
the outside world so its own output can't quietly take it over; quitkit keeps your effort on a vein only
while it's still paying, then cuts; idcheck keeps only the controls that actually identify the effect,
and drops the ones injecting bias; goodhart keeps a metric honest only while optimizing it still tracks
the goal, and tells you when it doesn't; herdcheck keeps a crowd of agents wiser than its best member by
catching the moment they start copying each other.

## Install
```bash
pip install .                 # the three cores (dependency-free)
pip install ".[mcp]"          # + the MCP servers (mnemo-mcp, second-brain-mcp, ragfresh-mcp)
pip install ".[pgvector]"     # + ragfresh Postgres/pgvector adapter
```
```python
import mnemo, ragfresh, nullcheck, selfref, quitkit, idcheck, goodhart
m = mnemo.Mnemo("agent_memory.json")           # remember / recall / consolidate
plan = ragfresh.triage(items, now=...)         # keep/downweight/refresh/prune
verdict = nullcheck.ab_test(100, 1000, 115, 1000)   # real or noise?
risk = selfref.audit(external_fraction=0.0, self_trust_p=2.0)  # collapse / lock?
cut = quitkit.should_quit(recent_yields)       # drawdown stop — keep or quit?
id_ = idcheck.audit({"age": "confounder", "saw_ad": "collider"})  # identified or biased?
gh = goodhart.audit(gameability=2.0, n_metrics=1)   # is the metric gamed?
hc = herdcheck.audit(peers_seen=2, own_weight=1.0)  # will the agent crowd herd?
```

## MCP (use them from Claude / Cursor / any agent)
```bash
mnemo-mcp            # agent long-term memory
second-brain-mcp     # think over + MAINTAIN a notes folder  (NOTES_DIR=...)
ragfresh-mcp         # decide what to keep/prune in a vector store
selfref-mcp          # is this agent/model training on itself? (collapse + lock)
quitkit-mcp          # when to quit a depleting effort (drawdown-exit threshold)
idcheck-mcp          # is this causal/attribution number identified, or biased?
goodhart-mcp         # how gameable is this proxy/metric? (reward hacking / KPI drift)
herdcheck-mcp        # will this multi-agent system / ensemble herd?
```

## Try everything at once
```bash
python examples/toolkit_demo.py
```

Open-core: the cores stay free.

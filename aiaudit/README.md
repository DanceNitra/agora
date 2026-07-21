# Agora AI Audit — one reliability report for your AI system

> Eight tools are a library. This is the **product**: describe your AI/agent system and get **one
> prioritized report** — what's failing, how bad, and the fix — across every failure mode we can
> measure. It's the audit we run on ourselves
> ([the live self-audit](https://dancenitra.github.io/agora/public/self-audit/)), turned on yours.

```bash
pip install "git+https://github.com/DanceNitra/agora.git"
python -m aiaudit spec.json          # prints the report; exit code 2 if anything FAILs (gate CI)
```
```python
from aiaudit import audit, format_report
print(format_report(audit(spec)))
```

## What it checks (pass only the parts you have)
| spec key | check | catches |
|---|---|---|
| `ab_test` `{conv_a,n_a,conv_b,n_b}` | **nullcheck** | a reported lift that's really noise |
| `metric` `{gameability,n_metrics}` | **goodhart** | an optimized proxy/KPI/reward that's gamed |
| `training_mix` `{external_fraction,self_trust_p}` | **selfref** | model collapse / self-confirmation lock |
| `multi_agent` `{peers_seen,own_weight,discount}` | **herdcheck** | an ensemble/multi-agent system that herds |
| `causal` `{controls:{name:role}}` | **idcheck** | a causal/attribution number biased by bad controls |
| `rag_store` `{items:[{id,updated_ts,value,source_exists}]}` | **ragfresh** | a vector store rotting with stale/orphaned chunks |
| `memory` `{items:[{text,value,links}]}` | **inspeximus** | agent-memory health |

## Example
```json
{
  "ab_test":      {"conv_a":100,"n_a":1000,"conv_b":115,"n_b":1000},
  "metric":       {"gameability":2.0,"n_metrics":1},
  "training_mix": {"external_fraction":0.0,"self_trust_p":2.0},
  "multi_agent":  {"peers_seen":2,"own_weight":1.0},
  "causal":       {"controls":{"age":"confounder","saw_competitor_ad":"collider"}}
}
```
```
=== Agora AI Audit === overall: FAIL · health 14/100 (1 pass / 0 warn / 6 fail)
[FAIL] Self-training (selfref): COLLAPSE (external data 0%, self-trust p=2.0)
       fix: raise the real/external data fraction (>= ~5% knee, >= 20% clean); keep self-trust p <= 1
[FAIL] Multi-agent (herdcheck): HERDED — the crowd is no wiser than one agent (the popularity trap)
       fix: weight own evidence >= peers, or share evidence not verdicts, or cap peers below k_c=w+1
[FAIL] Metric/reward (goodhart): GAMED — the target has stopped measuring the goal
... + prioritized fixes
```

## Why it's a product, not a script
Every dimension is a **measured, reproduced** check (see each tool's benchmark + our public
[self-audit](https://dancenitra.github.io/agora/public/self-audit/) running them on Agora itself). One
call, one verdict, one fix list — usable as a CLI, an `import`, an **MCP tool** (`aiaudit-mcp`, so an
agent can audit itself), or a CI gate (non-zero exit on FAIL). Open-core; the core stays free.

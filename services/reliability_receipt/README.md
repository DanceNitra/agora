# Reliability Receipt

Turn an AI-automation's run log into a one-page monthly **SLA receipt** a client renews against.

**Why:** AI automations sell as $500-1,500/mo *retainers*, but the maintenance is invisible, so
clients keep questioning the fee. This makes the invisible work legible: uptime, the issues you
absorbed, the dollars of work delivered, and an early **drift** warning when an upstream change
starts breaking things.

## Use

```bash
# See a sample receipt on synthetic data (writes sample_runs.jsonl + sample_receipt.md):
python receipt.py --demo

# Real run log (JSON-lines; only ts + ok are required):
python receipt.py runs.jsonl --client "Acme Co" --automation "Invoice agent" --rate 800
```

Run-log line format:

```json
{"ts": "2026-06-01T08:00:00", "ok": true, "interventions": 0, "dollars_saved": 42.0, "error": null, "latency_s": 3.1}
```

## What it reports
- **Uptime / success rate** and runs handled
- **Interventions** you caught and fixed (the maintenance the retainer covers)
- **Value delivered** ($ of work done) and ROI vs the retainer
- **Drift watch** - compares the last 7 days vs the prior baseline; flags a >=15pp success drop
- **Bottom line** - "running clean" vs "action needed"

See `sample_receipt.md` for example output. Zero dependencies (Python stdlib only).

Sells the retainer by making the maintenance you already do *visible*. Pair it with the automation
you ship (e.g. `services/support_agent/`).

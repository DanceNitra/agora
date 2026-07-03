# GATED DRAFT — reply to @yadu9989 (Neeraj Yadav, MemStrata) on DanceNitra/agora Discussion #2
# Context: he confirmed schema_v0 + emitter, is building the MemStrata ingest adapter (~2 weeks, branch),
# handles null-object on his side, and asked us to run his exact test payload through our emitter.
# VALIDATED this cycle: his fact -> mnemo -> schema_v0_emit -> jsonschema.validate == TRUE.
# STATUS: NOT POSTED — owner-gated.

Ran your exact test fact through the emitter — it round-trips clean and validates against `schema_v0.json` (jsonschema). Here is the emitted record, i.e. the exact shape your `POST /ingest/v0` adapter will parse:

```json
{
  "version": "schema_v0",
  "fact_record": {
    "id": "m-2048",
    "valid_from": 1783000000.0,
    "recorded_at": 1783000000.4,
    "key": "claude-code::default-model",
    "subject": "claude-code",
    "relation": "default-model",
    "object": null,
    "text": "The default model for Claude Code CLI is claude-3-5-sonnet-20240620.",
    "sources": [{"channel": "doc", "principal": "anthropic-changelog"}],
    "corroboration_count": 1,
    "effective_value": 1.0,
    "mtype": "semantic",
    "status": "active"
  }
}
```

So the contract holds on our side: `object` stays `null` (the value lives in `text`, as the emitter documents), `subject`/`relation` derive from `key`, and `corroboration_count` is the distinct-source count. Your "parse `text` as the terminal object when `object` is null" adapter rule is exactly the right seam — no change to our storage structure.

Two-week timeline is fine, no rush — your release comes first. When the branch is live I'll run this through the live pipeline and we can diff the `ingest_ack`.

One suggestion, since you deliberately picked a fact built to be superseded: treat this record as the (already-stale) **"before"** and make the first end-to-end test a **pair** — this record, then a second write of `claude-code::default-model` at a later `valid_from` carrying the *current* default. That's the honest version of the demo: the value you gave is exactly the kind of fact that goes out of date, so the test should show it being retired, not just ingested. mnemo keys on `(claude-code, default-model)`, so the supersession is deterministic on the write side; your ledger retires the stale row on the read side. One clean supersession, end to end — which is the behavior the whole contract exists for.


---
POSTED 2026-07-03: https://github.com/DanceNitra/agora/discussions/2#discussioncomment-17520054 (owner-approved). VALIDATE done (emitter ran + jsonschema TRUE); proportionate audit/verify clean. OWE (~2 weeks, when Neeraj pushes the MemStrata ingest adapter branch): run the emitted record through the live POST /ingest/v0 pipeline + diff ingest_ack; and the supersession PAIR (claude-code::default-model stale->current) as the first end-to-end test.

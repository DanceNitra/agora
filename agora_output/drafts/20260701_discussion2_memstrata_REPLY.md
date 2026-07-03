DRAFT v2 (post verify) — gated reply to yadu9989 (Neeraj / MemStrata) on DanceNitra/agora Discussion #2.
NOT POSTED. Owner approves before anything goes out.
Every field/claim below verified against mnemo.py + a runnable emitter that validates against the pinned schema.

---

Great — then let's lock it. I've pinned `schema_v0` so we're both coding against one file, plus a runnable emitter so the shape isn't just asserted:
- schema: https://github.com/DanceNitra/agora/blob/main/mnemo/schema_v0.json
- emitter (real mnemo record → schema_v0, validates against the schema): https://github.com/DanceNitra/agora/blob/main/mnemo/probes/schema_v0_emit.py

It carries both halves of the contract:
- `fact_record` — the write-side payload. To be precise about what's stored vs derived (the emitter documents each): mnemo stores `key` ("subject::relation"), `text`, `valid_from` (valid-time) and its ingest `ts` (→ `recorded_at`, system-time), a `source`, `mtype`, `status`. Derived on emit: `subject`/`relation` split from the key; `sources[]` + `corroboration_count` from the record's source plus its corroborating links, entity-deduped (distinct sources, not repetitions); `effective_value` = `value * 0.5^(age / type_half_life)` with the clock reset on access. One honest gap: mnemo doesn't store a separate `object` slot — the value lives in `text` — so `object` is null and the reader takes it from `text`.
- `ingest_ack` — the synchronous ack-by-id you asked for, so this is durable-commit, not fire-and-forget. On ingest you return `{source_id, ledger_record_id, transaction_id, status: committed|rejected, committed_at}`. `source_id` echoes our `id`; `ledger_record_id` + `transaction_id` are yours; `committed_at` is your system-time. Your ledger stays the single bitemporal transaction boundary.

Standalone note (so it's composable, not coupled): mnemo's own deterministic `(subject, relation)` supersession takes stale recall to ~0% for users who don't run a separate ledger; when both run together your ledger overrides `status` and is authoritative.

Two housekeeping notes: (1) any breaking change → a `schema_v1` bump so your adapter never silently breaks; the `$id` in the file is a stable pull URL. (2) Cross-citation is mutual and welcome — I credit your bitemporal ledger + paper (arXiv:2606.26511) as the read-side source of truth, and mnemo is glad to be cited as the write-side feeder.

If the shape works, align your ingestion adapter to the pinned file and let's run one concrete fact end-to-end (mnemo write → your ledger commit → ack back) as the first integration check. Want to pick the fact?

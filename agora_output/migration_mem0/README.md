# mem0 -> inspeximus real migration receipt

**Run:** 2026-09-07, scenario A01_update.json, live mem0 OSS (glm-5.2 over
ollama.com, local nomic-embed-text embeddings, qdrant on-disk).

## Numbers
- 50 sessions ingested in 735.5s (1 LLM parse error, mem0's own extraction)
- A real `m.update()` and a real `m.delete()` were issued through mem0's own API,
  so the ledger holds genuine UPDATE and DELETE events (not harness inventions)
- **250 ledger events -> 248 chains -> 247 imported, 0 unkeyed** — mem0's ledger
  covered every live memory; one chain ends deleted and stays out of recall
- Superseded events replayed: 1 · noop replays: 0 · reconciled: 0

## Parity (honest metric)
- "What is my current job title at Bridgemark Solutions?" — both stores return
  the SAME fact in different wording (keyphrase overlap 0.75, keyphrase_match true;
  exact-string match false by construction).
- "what do you remember about me?" — top-1 differs (overlap 0.0): open-query rank
  sensitivity, reported as such rather than smoothed over.

## Files
- `MIGRATE_REAL_RESULT.json` — full receipt (preheat, counts, parity rows)
- `history.db` — mem0's ledger as read (229 KB)
- `current.json` — the live get_all export (ground truth for reconciliation)
- `migrated.json` — the inspeximus store produced by the tool

## Reproduce
Tool: `migrate_mem0.py` in DanceNitra/inspeximus (chain-preserving migrator;
end-state test: `python tests/test_migrate_mem0.py`). Driver + post-process live in
`agora_output/lab/memops/` (gitignored lab dir): `migrate_real_run.py A01_update.json`
(~12 min; needs mem0ai, qdrant-client, ollama nomic-embed-text at 127.0.0.1, and the
dungeon LLM key in agora-game-server/.env read via pilot.py).

## Known limits
- Write receipts were DISABLED in this run (INSPEXIMUS_RECEIPTS unset), so
  verify_writes() reports "nothing to verify" — a receipts-on rerun is the next step.
- One scenario, one user scope. Multi-user and larger corpora are future runs.

---

## Receipts-on pass (v2, same real inputs)

A second migration pass over the SAME ledger + export, with the tamper-evident
write chain enabled (`Inspeximus(receipts=True)`):

- Same numbers: 250 events -> 248 chains -> 247 imported, 0 unkeyed
- **`verify_writes()` = `[true, []]`** — the hash-chained write chain verifies over
  all 247 imported records
- Parity recomputed live against the v1 temp mem0 store: same rows
- Files: `migrated_receipts.json` + sidecar `migrated_receipts.json.receipts.json`
  (228 KB receipt chain), receipt `MIGRATE_RECEIPTS_RESULT.json`

The tool gained `--receipts` / `receipts=True` (inspeximus repo commit) so this
needs no code edit, just the flag.

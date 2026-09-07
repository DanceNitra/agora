# PAUSED — waiting for inspeximus 3.0.0 (in release on another machine)

**Paused 2026-09-07.** Resume the migration-product work only after 3.0.0 lands.

## State at pause (all pushed)
- `DanceNitra/inspeximus` main @ dedc123: migrate_mem0.py (chain-preserving, --receipts,
  parity metric with keyphrase overlap), tests/test_migrate_mem0.py (PASS),
  MIGRATION_FROM_MEM0.md (scoped-recall example fixed to user_id=).
- `agora` @ 4b0a949: receipts (verify_writes [true,[]]), multi-user run
  (3 users, 777 chains, no leakage, uid distribution exact), README with resolved
  33/266 probe (relevance-floor abstention, verified 33==33).

## Must re-verify against 3.0.0 before any migration claim stands again
1. `python tests/test_migrate_mem0.py` — end-state test against the new core.
2. Store format: 1.88 persists SQLite (records/meta tables); 3.0.0 may change the
   schema — the diagnostic scripts read `records(id, ord, doc)` + history via
   migrate_mem0.read_history.
3. API surface used by the tool: remember(valid_from, key, object, user_id, meta),
   recall(user_id=), forget(ids), verify_writes(). If 3.0.0 renames/moves meta.uid
   scoping (core.py:2786, 10771, 10974), the driver checks + guide Step 2 need the
   same fix again.
4. Re-run receipts-on pass (verify_writes must be [true, []]) before re-claiming
   tamper-evidence.
5. Guide's mem0-side facts (ledger schema, API, top_k-not-limit) are pinned to the
   2026-09-07 audit read — mem0 side unchanged by our 3.0.0, no re-verification
   needed there unless mem0 itself ships a new release.

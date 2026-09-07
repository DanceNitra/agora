# PAUSED — waiting for inspeximus 3.0.0 release

**Paused 2026-09-07.** Resume the migration-product work only after 3.0.0 is published on PyPI.

## CORRECTION (was wrong in the first draft of this note)
- The library is NOT "1.88" — that figure came from a stale comment in the
  agora shim header (inspeximus_pypi/inspeximus/__init__.py, "reached 1.88.0").
- Actual: pyproject.toml = **3.0.0** (release in flight); PyPI = **2.26.1**.
- **Today's migration runs and the end-state test already ran on the 3.0.0 core**
  (the row-store). The UnicodeDecodeError when reading migrated_multi.json as text
  was the 3.0.0 on-disk format (SQLite), per the 3.0.0 CHANGELOG: BREAKING on disk
  only — 2.26.1 and earlier cannot read it; downgrade is a file rename.

## State at pause (all pushed)
- `DanceNitra/inspeximus` main @ dedc123: migrate_mem0.py (chain-preserving, --receipts,
  parity metric with keyphrase overlap), tests/test_migrate_mem0.py (PASS on the 3.0.0
  core), MIGRATION_FROM_MEM0.md (scoped-recall example fixed to user_id=).
- `agora` @ 5d0a1ac: receipts (verify_writes [true,[]]), multi-user run
  (3 users, 777 chains, no leakage, uid distribution exact), 33/266 probe resolved
  (relevance-floor abstention, verified 33==33).

## Checklist once 3.0.0 is published
1. `python tests/test_migrate_mem0.py` — re-run against the final 3.0.0 tag
   (today's run was against the pre-release state of the same repo).
2. Confirm the on-disk format story in the release notes is final (row-store,
   downgrade = file rename) and that migrate_mem0.read_history unaffected (it reads
   mem0's history.db, not ours).
3. Re-run the receipts-on pass if anything in the receipts path changed.
4. Guide's mem0-side facts (ledger schema, API, top_k-not-limit) are pinned to the
   2026-09-07 audit read — mem0 side unaffected by our 3.0.0.

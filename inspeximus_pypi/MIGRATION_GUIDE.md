# Migrating from mem0 — canonical guide

The migration tool and guide live in the inspeximus library repository, not here
(this directory is a forwarding shim, not the release source — see the header of
`inspeximus/__init__.py`).

- **Guide:** https://github.com/DanceNitra/inspeximus/blob/main/MIGRATION_FROM_MEM0.md
- **Tool:** `migrate_mem0.py` in the same repository — reads mem0's history ledger,
  rebuilds correction chains as inspeximus supersession keys, reconciles against the
  live export, and writes a migration report.
- **Proof:** `python tests/test_migrate_mem0.py` in that repo runs an end-state test on
  a synthetic ledger built with mem0's exact schema.

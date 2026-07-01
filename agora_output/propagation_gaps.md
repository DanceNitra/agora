# Propagation phase — status + open gaps (2026-06-28, overnight)

## DONE autonomously (our own surfaces, all pushed)
1. **Crucible** — re-rendered the ledger (was frozen at the 2026-06-20 render): 51 → **64 entries** (42 reproduced / 7 failed / 15 not-computable), added the supersession replication, synced landing counts (64/42/7/15, 35 essays).
2. **Landing — Mnemosyne section** — refreshed to **mnemo v0.2**: new stat card `42% → 0%` (supersession), footer rewritten (deterministic supersession key, sybil-resistant entity-resolution gate, `forget()`), links the new post. EN/SK.
3. **Landing — RAMR section** — reconciled with the repo: added the acronym **Retrieval-Augmented Memory Reliability**, **Six → Nine metrics**, added `TEMPORAL-AS-OF` (bi-temporal supersession — ties to mnemo v0.2) + `OPERATIONAL-CONTINUITY` rows. EN/SK.

## OPEN — needs owner go (credentialed external-publication acts; NOT done overnight)
4. **HF dataset card `Danchi17/ramr`** is STALE: says "six metrics", data files at `v0.1.0`. Repo is **v0.1.9 / 9 metrics** (adds COMPRESSION-vs-RAW, OPERATIONAL-CONTINUITY, TEMPORAL-AS-OF). Fix = update the HF README/card + re-upload the current data files. Needs HF token (Danchi17). Tool: `tools/publish_*_hf.py` pattern.
5. **Zenodo RAMR record** (DOI 10.5281/zenodo.20818291) is at **v0.1.1 / "six failure modes"** (published 2026-06-23). DOI resolves fine. Repo is v0.1.9/9. Fix = deposit a **new version** (0.1.9) with updated metadata + files. Needs Zenodo token. NOTE: a Zenodo version is permanent + citeable — deliberate act, owner should approve.
6. (not yet checked) folklore-index HF/Zenodo — lower priority; verify next.

**Recommendation:** the site/Crucible/landing are fully current. The two external RAMR mirrors (HF + Zenodo) lag the repo by ~8 patch versions; updating them is a credentialed publish — propose doing it together as a single "RAMR v0.1.9 release" pass on owner's go (sync HF card+data, then cut a Zenodo new version), verifying every number vs the repo first.

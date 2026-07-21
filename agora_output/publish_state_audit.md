# Publish-state audit — single source of truth (updated 2026-06-28, post-release)

## RAMR — now v0.4.1 EVERYWHERE (released 2026-06-28)
- **GitHub** (github.com/DanceNitra/ramr): repo at v0.4.1; **git release `v0.4.1` cut** (first machine-readable tag — https://github.com/DanceNitra/ramr/releases/tag/v0.4.1). CITATION.cff synced to v0.4.1 / nine metrics (+ v0.4.1 archive DOI line).
- **HF** (Danchi17/ramr): card refreshed to **nine metrics + Folklore Meter + RAMR↔LS interop**, CITATION + data re-uploaded. ✓ current.
- **Zenodo**: new permanent version **v0.4.1 → DOI 10.5281/zenodo.20996166** (concept DOI 10.5281/zenodo.20818291 preserved, "always latest"). Prior archive v0.1.1 = 10.5281/zenodo.20818813.
- Headline **9 metrics**: CONVERSION, CHAIN-FRAGILITY, DISTRACTION, FACT-RETENTION, OUTCOME-RANKED-RECALL, FORGET-PRECISION, COMPRESSION-vs-RAW, OPERATIONAL-CONTINUITY, TEMPORAL-AS-OF (+ aux ABSTENTION, CROSS-SCOPE-LEAKAGE). v0.4 tooling: Folklore Meter (`ramr_folklore_meter.py`) + RAMR↔LS shared evidence fixtures (safal207/LS).

## Folklore Index — now v0.1.2 EVERYWHERE (released 2026-06-28)
- Rebuilt from the grown Crucible (51→64): **60 → 73 claims** (43 REPRODUCED / 15 FAILED / 15 NOT_COMPUTABLE; 64 replication + 9 ai-claim).
- **HF** Danchi17/folklore-index ✓ v0.1.2. **PyPI** folklore-index 0.1.2 ✓ (`pip install folklore-index`). **Zenodo** new version **v0.1.2 → DOI 10.5281/zenodo.20996247** (concept 10.5281/zenodo.20771544 preserved).

## inspeximus
- v0.2.1 in github.com/DanceNitra/agora /inspeximus — supersession key + entity-resolution sybil gate + forget(). Shipped 2026-06-28.

## WEBSITE (dancenitra.github.io/agora) — synced 2026-06-28
- Landing RAMR section: **nine metrics shown** (added COMPRESSION-vs-RAW, verified −0.55 @k=50 n=20) + **Folklore Meter / RAMR↔LS interop** line. ✓
- Landing Inspeximus: inspeximus v0.2 ✓. Crucible: 64 entries (42/7/15) ✓. RAMR DOI badge = concept DOI (always latest) ✓.

## STATUS: all external mirrors (HF + Zenodo + PyPI) now MATCH the repos. Nothing stale.
Note: RAMR_HF_CARD.md lives under gitignored agora_output/benchmark/ (build input, on HF only — not in the public repo, by design).

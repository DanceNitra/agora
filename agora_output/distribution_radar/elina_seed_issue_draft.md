# Elina-Seed issue draft (GATED — owner approves, then I open via gh on deepseek-launch-community/Elina-seed)
# Requested by qingkong66 in deepseek-ai/DeepSeek-V3#1121. Keep it concise + human, not over-polished.

TITLE:
Cross-architecture memory-reliability probes — adapter for the Elina-Seed format

BODY:
Following up from the conversation in deepseek-ai/DeepSeek-V3#1121 (cc @qingkong66) — moving it here so it lives next to the memory format.

I wired an adapter against Elina-Seed's `{fact_N: {timestamp, note}}` shape (from `memory/memory_loop.py`) so our memory-reliability probes can run on Elina-format data and we can compare on the same ground:

- Adapter + probes: https://github.com/DanceNitra/agora/tree/main/research/probes (`elina_adapter.py`)
- Reference doc (context): https://github.com/deepseek-launch-community/Elina-seed/blob/main/docs/references/external_experiments_dancenitra.md

What it does today: runs a corroboration/poison check on Elina-format records. The built-in demo shows a repeated-but-unverified note being surfaced by recency recall, while a corroboration gate blocks it (repetition isn't corroboration — it needs ≥2 distinct sources). Run it on a real Elina memory dump with `--file memory.json`.

Next, if it's useful: if Elina fixtures carry a per-record source (or valence) field, I'll wire those into the eviction (two-tier) and supersession probes too, for a fuller side-by-side across the two architectures.

Open to whatever shape of test format keeps results comparable — happy to follow your lead on the fixture spec.

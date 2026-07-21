# qingkong66 reply #3 — DRAFT (GATED; I post via gh on owner OK). deepseek-ai/DeepSeek-V3 #1121.
# Now references the LIVE adapter we built against their public format — concrete, not a promise.
---
@qingkong66 — went ahead and wired an adapter against your public memory format (`memory_loop.py`'s `{fact_N: {timestamp, note}}` shape) so we can compare on the same data, not just talk about it:

https://github.com/DanceNitra/agora/blob/main/research/probes/elina_adapter.py

It runs our corroboration check on Elina-format records. The built-in demo makes the cross-architecture point concretely: a repeated false, unverified note ("the capital of Australia is Sydney", stored across several sessions) is surfaced as current by recency recall, but blocked by a corroboration gate — because repetition isn't corroboration (it needs ≥2 *distinct* sources, sybil-resistant). A genuinely 2-source fact passes.

Point it at a real Elina memory dump with `--file memory.json` and it'll report the poison + eviction exposure on your actual data. If your richer fixtures carry a source (or valence) field per record, I'll wire those into the eviction (two-tier) and supersession probes as well, so we get a full side-by-side.

Happy to open an Elina-Seed issue with this adapter as the starting artifact if that's the better place to iterate.
---

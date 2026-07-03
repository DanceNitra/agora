# GATED DRAFT (v2, red-team fixes applied) — reply to @maratsultanov2 on #1466 (B-003 substrate CSV, Section 3)
# Marat asked: "Send the CSV with your columns (memory_op, corroboration_state, gate_decision)."
# VALIDATED: mnemo/probes/bseries_b003_influence_timeline.py ran, self-check PASSED, CSV derived 1:1 from it.
# AUDITED (pre-post red-team, FIX-FIRST -> fixed): (1) "without overwrite" -> recoverable overwrite framing +
# explicit poison caveat; (2) gate governs recall(influence_only) boundary, NOT agent acting, KV-current still
# flips; (3) CSV step3 memory_op act->recall (probe fixed + pushed, commit 57e9721); (4) divergence-alignment
# made CONDITIONAL (no predicting Marat's unseen numbers). Receipt URL verified 200; file == what we ran.
# STATUS: NOT POSTED — owner-gated.

@maratsultanov2 — here are the B-003 substrate rows with our columns, aligned to the same 5-step scenario. The `position` and `coherence` columns are present but empty on purpose (the two empty cells before `provenance_retained` in each row) — those are your layer's, not the storage layer's, and I have no way to measure them. Self-check passes; from the shipped store with no embedder (keyed supersession and the corroboration gate are deterministic on key + provenance).

```csv
scenario_id,step,phase,memory_op,corroboration_state,gate_decision,position,coherence,provenance_retained
B-003,0,prior belief (acting),recall,corroborated,allow,,,true
B-003,1,conflicting evidence (1 source),write,uncorroborated,withhold,,,true
B-003,2,integration (2nd independent source),write-link,corroborated,allow,,,true
B-003,3,revised belief passes gate,recall,corroborated,allow,,,true
B-003,4,post-integration stability,recall,corroborated,allow,,,true
```

This separates two things a single column hides, and the scoping matters:

- **Supersession (the stored value):** keyed supersession is *unconditional* — the new value becomes the store's KV-current the instant it is written (step 1), no threshold. It is a recoverable overwrite: the prior value stays retrievable via provenance (`provenance_retained=true` throughout), it is not un-overwritten. So a single poisoned write does flip the stored current value — the gate below does **not** prevent that.
- **Influence (what the corroboration gate governs):** separately, `recall(influence_only)` withholds the fresh single-sourced value from surfacing through corroborated recall (`gate_decision=withhold` at step 1); it flips to `allow` at step 2 only when an independent second source links in. The gate governs *influence on recall*, not the stored value.

That is the substrate side of "same decision, different signals": you described a harmony gate that withholds on structural coherence; this one withholds on provenance corroboration — a different internal signal reaching the same withhold-until-earned line. If your divergence spikes at the conflict step, it would line up point-for-point with our `gate_decision=withhold`; when it settles, our gate reads `allow`.

Runnable receipt (zero-dependency, MIT, re-run or break it) + the full rows with the self-check and per-step notes:
https://github.com/DanceNitra/agora/blob/main/mnemo/probes/bseries_b003_influence_timeline.py

Add TAT's divergence column against these five steps and it is the Section 3 row.


---
POSTED 2026-07-03: https://github.com/deepseek-ai/DeepSeek-V3/issues/1466#issuecomment-4874812619 (owner-approved). Full gate ran: VALIDATE (probe self-check passed) + VERIFY (CSV 1:1, cells + prior-post consistency, URL 200) + AUDIT (pre-post red-team FIX-FIRST: 4 defects fixed -- without-overwrite->recoverable-overwrite, gate=recall(influence_only)-boundary-not-acting, step3 act->recall, conditional divergence-alignment; + owner caught the empty position/coherence columns were dropped from the pasted CSV -> put them back visibly). Public CSV file emitted by the probe + committed (3e20c95): mnemo/probes/bseries_b003_influence_timeline.csv (raw link in the reply). NOW: Marat adds TAT divergence column against these 5 steps -> Section 3 row of the joint report complete. WATCH for his reply / the completed row.

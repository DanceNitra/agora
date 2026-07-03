# B-001 substrate claim — STRESS-CLAIM + VERIFY verdict (2026-07-01)

**VERDICT: REFRAME — do NOT post the current version.** 6-agent adversarial panel + prior-art verifier
converge: as written it is a textbook re-derivation on a rigged n=6 fixture, with a partly-wrong
prior-art citation. It would be correctly demolished by the very framework authors we'd be addressing.

## The three fatal problems (must fix before any post)
1. **RIGGED FIXTURE / n=6 (method auditor — sharpest hole).** The store (20 on-topic engineering
   distractors) and the 6 queries were hand-paired so preferences are orthogonal by construction. The
   "3/6 queries surface 0/3" split is n=6 noise (Wilson 95% CI ~0.15–0.85 — uninformative on rate). NOT
   fixable by a caveat — needs randomized/held-out queries, distractors sampled independently of the
   queries, more n, ideally a 2nd embedder + centering.
2. **STRAWMAN framing (steelman skeptic — kill shot).** Every framework we cite as "the fix" was built
   to NOT similarity-retrieve preferences. "similarity structurally buries preferences" reads as
   knocking down a baseline nobody ships. Drop "failure mode / structurally buries"; reframe as a
   **quantified ablation / runnable receipt** that puts a number on *why* the in-context profile tier
   exists.
3. **Prior-art citation errors (verifier).** (a) "core memory" is **Letta's** term, not the MemGPT
   paper's — the paper says *main/working context* (arXiv:2310.08560). (b) **mem0 does NOT have an
   always-injected profile** — it is user-scoped but STILL similarity-retrieved (filtered by `user_id`).
   So mem0 does NOT solve the orthogonality problem; citing it as an example of the fix is wrong.
4. (minor) **Metric mislabel:** don't emit our cosine under Cophy's `causal_density_at_retrieval` column;
   call it `substrate_query_cosine_proxy`.

## The genuinely valuable thing buried in it (the postable pivot)
Prior-art verifier: the *mechanism* is textbook, but a clean *quantified measurement* of the
orthogonality cost is "not previously done in this isolated form" → postable ONLY as an instrument, not
a discovery. AND two lenses (skeptic + blind-spot) converge on the actually-novel question:
- **Channel-selection vs channel-scaling confound:** typed_profile=1.0 is trivial at 3 preferences (all
  fit the budget). The real open problem: as preferences accumulate (50, 500; stale/contradictory),
  "inject all" overflows and becomes its own retrieval + **supersession** problem — which **fuses B-001
  with B-003** into one story (maintaining a bounded, current preference set).
- **Frontier question to offer the thread:** *At what preference-set size / query-overlap does the
  profile channel stop being "inject-all" and become its own retrieval+supersession problem — and is
  THAT crossover, not the channel itself, what governs cross-framework identity persistence?*

## Recommendation
The current draft fails our RAISED BAR (no textbook re-derivations). Two honest paths:
- **A (harden into the crossover finding):** redesign the fixture (de-rig, bigger n, 2nd embedder),
  add the crossover/scaling measurement + the B-001↔B-003 supersession fusion, reframe as an instrument
  citing MemGPT correctly. Produces a genuinely novel, thread-worthy contribution. ~1–2h of work.
- **B (hold):** don't post now. No pressure — qingkong said B-series fixtures aren't stable yet;
  luoxuejian said "if convenient." Tell them we'll run it properly against their real fixtures when
  stable.

Panel raw outputs: prior-art hunter, steelman skeptic, method/confound auditor, overclaim/framing,
blind-spot 6th lens, prior-art verifier (all 2026-07-01).

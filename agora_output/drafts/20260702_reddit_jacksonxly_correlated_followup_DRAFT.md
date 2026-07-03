# GATED Reddit follow-up draft — r/Rag 1ujwwu6, to jacksonxly: the correlated-cue arm result

Owner posts manually (owner already replied once; this is the deeper frontier-arm result — post as a
follow-up if wanted, or hold). Numbers VALIDATED: locomo_correlated_cue_composition.py, self-check
(single_A invariant across correlation) + reproducible across runs. AUDITED (REFRAME applied: report the
unconditional trend + c=0 slice so it's not cherry-picked; credit product-of-experts; scope as a controlled
stress-test since cue B is injected).

---

## DRAFT BODY

Ran the correlated-cue arm — and it turned the hypothesis on its head, which was the useful part.

Setup: real LoCoMo + the same prefer scoring, cue A = the correct speaker (truthful), cue B = a second binary cue injected as a noisy copy of A at a controlled mixing level, so I can dial the measured correlation phi(A,B) from ~0 to 1 and read product vs sum vs the single trusted cue. (cue B is synthetic, so this is a controlled composition stress-test, not a natural LoCoMo correlation.)

The prediction was "correlation makes the product double-count and flip below the sum." What I measured is that **correlation isn't the driver at all**. The product−sum gap is *worst at zero correlation* (unconditional −0.226 at phi≈0) and *shrinks* toward 0 as phi→1 — a redundant copy of a cue just can't miss when the real cue hits, so it stops hurting. So higher correlation makes the product *less* bad, not more.

The real axis is cue reliability, and it's the product-of-experts veto (Hinton 2002): a near-zero factor vetoes the whole score. On the slice where cue B is wrong-for-the-query, the numbers are stark — recall@20 **product 0.10 vs sum 0.52 vs the single trusted cue 0.70**. A multiplicative miss can't be compensated; an additive one degrades gracefully. So a *noisy* second cue hurts a product much more than a sum, and can do worse than not composing at all. (Caveat so I'm not overselling the crater: that slice is conditioned on the gold missing cue B, so its *magnitude* is a near-worst case; the load-bearing part is the ordering single > sum > product and the trust dose-response below.)

The fix is the per-cue trust weight — exactly your abstain-vs-guess point, one layer up. Down-weighting cue B's trust (0.9→0.3) pulls the product back to ≈sum on the misleading slice at low correlation; it only partially helps as the cue becomes a redundant copy (nothing helps at phi=1, but there the cue is inert anyway). So the rule I'd actually ship: compose a second cue as a product **only when it's independently reliable for the query**, and weight it by that reliability — the product punishes a miscalibrated cue far harder than the sum does.

Receipt: `mnemo/probes/locomo_correlated_cue_composition.py` (self-check: the single-cue arm is invariant across the correlation knob; runs reproducibly) at https://github.com/DanceNitra/agora/tree/main/mnemo/probes .

---
(sign-off in owner's voice; keep it plain)

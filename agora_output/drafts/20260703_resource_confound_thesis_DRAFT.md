# DRAFT v3 (NOT PUBLISHED) — after VALIDATE + 3-lens AUDIT (killed v1's framing) + STORM (academic +
# practitioner) + VERIFY (all citations vs primary). STILL GATED: needs the runnable reality_check.py tool
# + a seed-swept CI receipt, then bilingual EN/SK + SEO + re-audit + owner approval before publish.
#
# Working title: "Locate a method win before you believe it — a reality-check for LLM-memory claims"

## Frame (what this is / is NOT)
Not a new principle. "Find the *source* of a claimed gain before crediting the method; wins vanish under fair
comparison" is a well-worn genre — Lipton & Steinhardt name our exact failure mode ("failure to identify the
sources of empirical gains"); Ferrari Dacrema et al. beat 6/7 neural recommenders with tuned simple
baselines; Musgrave et al. found a decade of metric-learning gains marginal under equal comparison; Henderson
et al. traced deep-RL "gains" to seeds/implementation; Bouthillier et al. show single-run deltas evaporate
once variance is modeled. We stand on that genre.

What's ours is small and concrete: **a runnable check + four LLM-memory receipts** where a tempting "method
win" dissolved — including two we nearly shipped. The receipts are the point; run the check on *your own*
candidate win.

## Read the checks as DIAGNOSTICS, not verdicts
A check that fires doesn't mean "bad method" — it means "the win isn't coming from where you named it."
A method that wins by spending 3× the tokens can still be the right production call; the check tells you
*why* it won, so you buy it for the right reason and don't generalize a confound.

**1. Variance first.** Report multi-seed means with confidence intervals (bootstrap on per-item deltas).
A delta inside the noise band is not a result. (Bouthillier et al.) — this is the check that separates
"it won" from "it won by luck," and it's the one most single-run blog benchmarks skip.
**2. Compute- and plumbing-match.** If the method makes N calls / K× tokens, give the baseline the same
budget; hold the judge/generation prompt and per-stage model identical. Many "method" gains are a budget or
prompt artifact. (Diagnostic, not a production verdict — see above.)
**3. Proxy-vs-target.** Add a cheap-proxy arm (length, recency, "just spend more tokens"). If the proxy ties
the method, the method *is* the proxy — it isn't measuring what you named it.
**4. Ablation-to-localize.** Turn the claimed mechanism off. If the number barely moves, the mechanism isn't
the source. (Lipton & Steinhardt's "identify the source.")
**5. Impossibility / prior-art (sidebar, judgment not probe).** Does it reduce to a known impossibility
(Sybil, Douceur 2002) or a named principle (Biba integrity, risk-based access control)? Scope the claim and
cite the rest.

## Four receipts (honest, self-caught — not "debunked methods")
**A — Proxy kills "an embedding-norm re-ranker recovers recall cosine throws away."** *Our* LoCoMo re-ranker.
Norm-aware re-rank beat cosine (+0.043 recall@10, bootstrap CI excludes 0) — but the raw nomic norm is a
**length proxy** (corr(|d|, tokens) = −0.71); a pure length arm ties it (norm − length = −0.0001, CI crosses
0). No specificity signal beyond length. The most cross-cutting gotcha here: embedding *magnitude tracks
token count*, silently corrupting recency/importance heuristics and cosine-vs-dot choices. (This says nothing
about arXiv:2606.30625's own setup, which we did not reproduce.) Receipt: `norm_specificity_reranker.py`.
**B — Compute-match kills "decomposed judging beats holistic, gap grows with complexity."** *Our own*
"atomic-decomposition law." Capped the holistic judge at one tight call → looked dramatic (Δ→+0.73/+1.00 at
8 sub-claims). But decomposition makes K calls = K× tokens; **matched tokens → Δ=0** at every complexity
across deepseek-v4-flash/pro, kimi-k2.6 (two families) and Claude, and Δ=0 on chained affirming-the-consequent
fallacies too. *Scope, loudly:* this refutes **our own** law on clean/independent checks. The published
decomposition-judging claims live in a **different regime we do NOT test and that stands** — Theoria
(Saldivar & Slivinski, arXiv:2607.01223) reports 90.6% vs 62.5% on **hidden premises**. And "extra tokens can
supply computation" is contested, not settled: Pfau et al. (2404.15758) show filler tokens can substitute for
CoT on *specific synthetic tasks with dense supervision*, while Lanham et al. (2307.13702) found filler gives
**no** gain on natural benchmarks. So matched-compute is a **necessary control**, not a universal explanation.
Receipts: `atomic_decomposition_calibration_law.py` (+ `_crossfamily`, `_subtle_errors`).
**C — Proxy/discrimination kills "a burst monitor closes the corroboration-poisoning hole."** A stateful
fresh-source-burst monitor *we* proposed then rejected: it can't tell a Sybil burst from two genuine new
sources reporting at once (TPR = FPR = 1 in the fresh-burst regime) and is bypassed by dripping / pre-aging
domains. Receipt: `bseries_forged_provenance_stateful_monitor.py`.
**D — Impossibility check on a reader's proposed defense (with credit, sidebar).** In an r/LangChain thread,
jacksonxly proposed scaling memory authority by an action's blast radius. We built and stress-tested it *with
him*: it recovers the recall tail but reduces to Douceur's 2002 Sybil impossibility (the high-stakes tier
rests on an unforgeable-independence test) and is standard risk-based / Biba-integrity authorization (CaMeL,
arXiv:2503.18813, is the current agent-side statement). A good idea, correctly scoped — not a debunk.

## The deliverable (this is what makes it a tool, not a blog post)
`reality_check.py`: drop it next to your eval; it runs the compute-match, proxy, and variance-CI controls and
prints **PASS / CONFOUNDED** per check. Each of the four receipts is `git clone && python probe.py` and
prints every headline number (the practitioner bar: "the only credible benchmark result is one you can
reproduce yourself"). MIT, github.com/DanceNitra/agora/tree/main/mnemo/probes.

## What we did NOT show + the honest edges
Not that decomposition is useless (its hidden-premise regime stands); not that the norm paper's own setup is
wrong; not that compute-match is a production verdict (in production, latency/token budget IS the constraint).
A related confound worth naming: parametric leakage — a "retrieval win" that's really the base model
answering from memory (arXiv:2510.27246). The routine catches cheap confounds; a method can pass all five and
still be real, or fail them and still help in a regime you didn't test.

## The one door that isn't a wall
For provenance/corroboration defenses, Douceur's own escape is a **cost to mint an identity** — attestable /
signed source credentials (C2PA-style) or earned-and-verified standing. That's the arm worth building.

## MUST-CITE (all verified vs primary 2026-07-03)
Lipton & Steinhardt, Troubling Trends (arXiv:1807.03341) · Ferrari Dacrema, Cremonesi, Jannach, RecSys 2019
(1907.06902) · Musgrave, Belongie, Lim, ECCV 2020 (2003.08505) · Henderson et al., AAAI 2018 (1709.06560) ·
Bouthillier et al., Accounting for Variance (2103.03098) · Pfau, Merrill, Bowman (2404.15758) · Lanham et al.
(2307.13702) · Douceur, Sybil, IPTPS 2002 · Theoria, Saldivar & Slivinski (2607.01223) · CaMeL, Debenedetti
et al. (2503.18813) · NIST RAdAC · Biba integrity 1977 · parametric-leakage (2510.27246).

# Published-post audit tracker (verify-claims + stress-claim, EN+SK+SEO)

Order = oldest first. src = edit .md + re-render; piece = edit HTML directly.
Verdicts: CLEAR / MINOR / REFRAME / KILL.

| # | idx | date | slug | type | status | verdict | commit |
|---|-----|------|------|------|--------|---------|--------|
| 1 | 41 | 06-10 | causal-inference-phase-diagram | src | DONE | REFRAME | dfcdbbb |
| 2 | 40 | 06-11 | pre-trends-test-weak-evidence | src | DONE | REFRAME | 22a7cae |
| 3 | 38 | 06-12 | the-operating-point-trap | piece | DONE | REFRAME | 2341c3e |
| 4 | 39 | 06-12 | why-crowds-get-dumber | piece | DONE | REFRAME | 70859a0 |
| 5 | 37 | 06-13 | passing-a-pre-trends-test-weak-evidence-which-diff | piece | DONE | REFRAME | a641c69 |
| 6 | 36 | 06-14 | a-95-confidence-interval-that-covers-31 | piece | DONE | REFRAME (nums re-run 100%) | 3564a60 |
| 7 | 35 | 06-14 | more-data-more-wrong-bayesian-credible-interval | piece | DONE (FULL panel) | REFRAME — framing/estimand fixes panel found | 89f7fa5 |
> NOTE 2026-06-29: #7-9 first got a LIGHT pass; owner flagged it (alpha-omega: never shorten). #7 redone via FULL /stress-claim 5-lens panel above. #8, #9 below STILL NEED the full panel re-do (they had only lab re-run + 1 verifier).
| 8 | 34 | 06-15 | everyone-says-set-exit-criteria | piece | DONE (FULL panel) | heavy REFRAME — strawman baseline + wrong mechanism + giving-up-time family | b8cc9a8 |
| 9 | 33 | 06-15 | your-ai-might-be-training-on-itself | piece | DONE (FULL panel) | heavy REFRAME — 'lock law' is textbook (Arthur 1989 + telescoping p-series), retracted as ours; +curation caveat | d1ada81 |
| 10 | 32 | 06-15 | your-second-brain-is-dying-of-maintenance | piece | DONE (FULL panel) | REFRAME — percolation claim substantiated+scoped (ran sweep), prior-art (Molloy-Reed + Obsidian plugins), coverage caveat | 64150ef |
> Audit now ALSO captures NEW findings/frontier questions -> agora_output/audit_new_findings.md (per owner 2026-06-29).
| 11 | 31 | 06-15 | your-rag-store-is-rotting-freshness-beats-retrieval | piece | TODO | | |
| 12 | 30 | 06-15 | dunning-kruger-is-a-statistical-artifact | piece | TODO | | |
| 13 | 29 | 06-15 | the-hot-hand-fallacy-was-the-fallacy | piece | TODO | | |
| 14 | 28 | 06-16 | i-scored-the-16-most-hyped-anti-aging | piece | TODO | | |
| 15 | 27 | 06-16 | the-calibrated-prior-for-we-reversed-aging-in-mice | piece | TODO | | |
| 16 | 26 | 06-16 | a-pre-trend-too-gentle-to-see | piece | TODO | | |
| 17 | 25 | 06-17 | the-most-confident-systems-are-least-grounded | piece | TODO | | |
| 18 | 24 | 06-18 | we-hunted-for-the-tipping-point-in-8-systems | piece | TODO | | |
| 19 | 23 | 06-18 | we-looked-for-the-grounding-tipping-point | piece | TODO | | |
| 20 | 22 | 06-18 | why-a-more-capable-ai-can-be-more-confidently-wrong | piece | TODO | | |
| 21 | 21 | 06-18 | robustness-checks-arent-ritual | piece | TODO | | |
| 22 | 20 | 06-19 | we-built-a-firewall-for-ai-confidently-wrong | piece | TODO | | |
| 23 | 19 | 06-19 | we-built-a-meter-for-when-an-ai-is-confidently-wrong | piece | TODO | | |
| 24 | 18 | 06-19 | why-a-captured-company-doesnt-un-capture-itself | piece | TODO | | |
| 25 | 17 | 06-22 | the-verification-tax | piece | TODO | | |
| 26 | 16 | 06-22 | diversity-is-noise-for-answers-signal-for-ideas | piece | TODO | | |
| 27 | 15 | 06-25 | multihop-recall-model-in-the-loop | piece | TODO | | |
| 28 | 14 | 06-25 | does-long-context-kill-rag | piece | TODO | | |
| 29 | 13 | 06-25 | memory-poison-resistance-measured | piece | TODO | | |
| 30 | 12 | 06-26 | adaptation-corruption-separation-law | piece | TODO | | |
| 31 | 11 | 06-26 | agent-memory-eviction-two-tier | piece | TODO | | |
| 32 | 10 | 06-26 | best-of-n-exploitability | piece | TODO | | |
| 33 | 9 | 06-26 | ai-memory-consolidation-scope-law | piece | TODO | | |
| 34 | 8 | 06-27 | agent-memory-poisoning-corroboration-gate | piece | TODO | | |
| 35 | 7 | 06-28 | can-an-llm-trust-its-own-confidence | piece | TODO | | |
| 36 | 6 | 06-28 | rag-supersession-blind-spot | piece | TODO | | |
| 37 | 5 | 06-29 | food-nudges-publication-bias | src | TODO | | |
| 38 | 4 | 06-29 | good-to-great-zero-skill-null | src | TODO | | |
| 39 | 3 | 06-29 | llm-as-judge-length-confound | src | TODO | | |
| 40 | 2 | 06-29 | founder-led-survivorship-null | src | TODO | | |
| 41 | 1 | 06-29 | chatbot-arena-style-not-skill | src | TODO | | |
| 42 | 0 | 06-29 | ai-coding-productivity-operating-point | src | DONE (live-validated A) | MINOR | 2b33c3a |

Note: #42 was the verify-claims live-validation earlier (3 corrected, 0 FALSE). Counts as audited.

# SEO flagship optimization roadmap

**Goal:** every published post gets Mode-A treatment — an `## FAQ` (→ FAQPage JSON-LD), ≥3 topic-cluster internal links, answer-first framing, `dateModified` bump. FAQ Q&A must use **verified numbers pulled from the post itself** (no new claims). EN+SK both.

**Per-post recipe:** pull exact numbers from the post → write 3–4 Q&A (EN+SK) → inject FAQ + "Related research"/"Súvisiaci výskum" links before each lang div close → append FAQPage to JSON-LD + bump Article `dateModified` → `render_sitemap.py` → leak-scan → anon commit → push → deploy 200.

Cadence: ~1–2 posts/cycle. Mark `[x]` when live.

---

## DONE (4)
- [x] adaptation-corruption-separation-law
- [x] agent-memory-poisoning-corroboration-gate  (MINJA)
- [x] does-long-context-kill-rag  (Crucible marquee)
- [x] diversity-is-noise-for-answers-signal-for-ideas  (Diversity-Flip Law)

---

## TIER 1 — agent-memory / retrieval frontier (our SEO wedge; do first)
- [x] agent-memory-eviction-two-tier
- [x] multihop-recall-model-in-the-loop
- [x] memory-poison-resistance-measured
- [x] ai-memory-consolidation-scope-law
- [x] your-rag-store-is-rotting-freshness-beats-retrieval-and-we-m...
- [x] best-of-n-exploitability

## TIER 2 — grounding / confidence / self-training (capstone family)
- [ ] we-built-a-meter-for-when-an-ai-is-confidently-wrong---and-c... (grounding meter)
- [ ] we-built-a-firewall-for-ai-confidently-wrong-answers---and-i... (grounding firewall)
- [ ] why-a-more-capable-ai-can-be-more-confidently-wrong
- [ ] the-most-confident-systems-are-the-least-grounded
- [ ] we-looked-for-the-grounding-tipping-point-in-ai-self-trainin...
- [ ] we-hunted-for-the-tipping-point-in-8-systems-only-one-is-a-t...
- [ ] your-ai-might-be-training-on-itself-and-we-measured-the-two-...
- [ ] the-verification-tax

## TIER 3 — causal inference / methodology
- [ ] causal-inference-phase-diagram
- [ ] a-pre-trend-too-gentle-to-see-can-bias-a-difference-in-diffe...
- [ ] passing-a-pre-trends-test-is-weak-evidence-which-difference-...
- [ ] pre-trends-test-weak-evidence
- [ ] the-operating-point-trap-methods-break-exactly-where-they-ar...
- [ ] robustness-checks-arent-ritual---theyre-a-measurable-filter-...
- [ ] more-data-more-wrong-a-bayesian-credible-interval-is-not-cov...
- [ ] a-95-confidence-interval-that-covers-31-of-the-time-differen...
- [ ] everyone-says-set-exit-criteria-nobody-gives-you-the-number-...

## TIER 4 — other rigor / hype-busting / product
- [ ] the-hot-hand-fallacy-was-the-fallacy-a-famous-null-is-a-meas...
- [ ] dunning-kruger-is-a-statistical-artifact-a-zero-deficit-null...
- [ ] the-calibrated-prior-for-we-reversed-aging-in-mice-near-zero...
- [ ] i-scored-the-16-most-hyped-anti-aging-interventions-zero-hav...
- [ ] why-crowds-get-dumber-when-they-watch-each-other-and-the-sur...
- [ ] why-a-captured-company-doesnt-un-capture-itself-governance-h...
- [ ] your-second-brain-is-dying-of-maintenance-so-we-built-one-th... (mnemo/quitkit)

---

## Notes / watch for
- **Possible near-duplicate pairs** (SEO cannibalization risk — flag, don't merge here):
  - `passing-a-pre-trends-test-is-weak-evidence-which-difference-...` vs `pre-trends-test-weak-evidence`
  - `we-looked-for-the-grounding-tipping-point...` vs `we-hunted-for-the-tipping-point-in-8-systems...`
  - grounding-meter / grounding-firewall / most-confident-least-grounded / more-capable-more-confidently-wrong — overlapping grounding family
- Cluster links should point within the SAME theme tier where possible (tighter topic cluster = stronger authority signal).

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
- [x] we-built-a-meter-for-when-an-ai-is-confidently-wrong---and-c... (grounding meter)
- [x] we-built-a-firewall-for-ai-confidently-wrong-answers---and-i... (grounding firewall)
- [x] why-a-more-capable-ai-can-be-more-confidently-wrong
- [x] the-most-confident-systems-are-the-least-grounded
- [x] we-looked-for-the-grounding-tipping-point-in-ai-self-trainin...
- [x] we-hunted-for-the-tipping-point-in-8-systems-only-one-is-a-t...
- [x] your-ai-might-be-training-on-itself-and-we-measured-the-two-...
- [x] the-verification-tax

## TIER 3 — causal inference / methodology
- [x] causal-inference-phase-diagram
- [x] a-pre-trend-too-gentle-to-see-can-bias-a-difference-in-diffe...
- [x] passing-a-pre-trends-test-is-weak-evidence-which-difference-...
- [x] pre-trends-test-weak-evidence
- [x] the-operating-point-trap-methods-break-exactly-where-they-ar...
- [x] robustness-checks-arent-ritual---theyre-a-measurable-filter-...
- [x] more-data-more-wrong-a-bayesian-credible-interval-is-not-cov...
- [x] a-95-confidence-interval-that-covers-31-of-the-time-differen...
- [x] everyone-says-set-exit-criteria-nobody-gives-you-the-number-...

## TIER 4 — other rigor / hype-busting / product
- [x] the-hot-hand-fallacy-was-the-fallacy-a-famous-null-is-a-meas...
- [x] dunning-kruger-is-a-statistical-artifact-a-zero-deficit-null...
- [x] the-calibrated-prior-for-we-reversed-aging-in-mice-near-zero...
- [x] i-scored-the-16-most-hyped-anti-aging-interventions-zero-hav...
- [x] why-crowds-get-dumber-when-they-watch-each-other-and-the-sur...
- [x] why-a-captured-company-doesnt-un-capture-itself-governance-h...
- [x] your-second-brain-is-dying-of-maintenance-so-we-built-one-th... (mnemo/quitkit)

---

## Phase 2 — in-content contextual links (2–3 per post, pillar-funneled, EN+SK)
Owner-approved: quality over quota; link toward cluster pillars; keep the Related lists too.
Tool: `tools/seo_add_inline_links.py` (NFC-robust; feed Write-tool JSON, NOT bash heredoc — heredoc
mangles some SK chars like ľ). Anchors must be tag-free body phrases NOT duplicated in meta/JSON-LD.
Pillars: memory→adaptation-corruption-separation-law; grounding→the-most-confident-systems-are-the-least-grounded; causal→causal-inference-phase-diagram.

- [x] MEMORY cluster (8): law(3), eviction(3), poison-resistance(3), consolidation(3), MINJA(3), rag-rot(2), multihop(2), RAG-dead(1) — audited 0 issues
- [x] GROUNDING cluster (8) DONE: meter, firewall, more-capable, most-confident(pillar), looked-tipping, hunted-tipping, training-on-itself, verification-tax
- [x] CAUSAL cluster (9) DONE: phase-diagram(pillar), pre-trends x3, 95-CI, more-data, operating-point, robustness, exit-criteria
- [x] OTHER (7) DONE: hot-hand, dunning-kruger, calibrated-prior, i-scored-16, why-crowds, captured-company, second-brain
- [x] best-of-n, diversity DONE. Phase-2 COMPLETE 32/34 (skip: passing-* canonicalized dup; deep-dive-hot-hand legacy page)

---

## SK-BODY FIX (2026-06-27)
Found + fixed 5 posts published EN-body-only (no Slovak body): more-capable, a-pre-trend, robustness, calibrated-prior, i-scored. Full SK translations + h1/tldr SK spans added. Audit: 0 posts missing SK body. (First audit had off-by-one bug; thorough re-audit = prose-length check before FAQ.)

## Notes / watch for
- **Possible near-duplicate pairs** (SEO cannibalization risk — flag, don't merge here):
  - `passing-a-pre-trends-test-is-weak-evidence-which-difference-...` vs `pre-trends-test-weak-evidence`
  - `we-looked-for-the-grounding-tipping-point...` vs `we-hunted-for-the-tipping-point-in-8-systems...`
  - grounding-meter / grounding-firewall / most-confident-least-grounded / more-capable-more-confidently-wrong — overlapping grounding family
- Cluster links should point within the SAME theme tier where possible (tighter topic cluster = stronger authority signal).

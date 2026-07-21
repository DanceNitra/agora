---
name: seo
description: SEO + AI-search (AEO/GEO/LLMO) optimizer for the Agora storefront (dancenitra.github.io/agora) — a bilingual EN/SK static research blog on GitHub Pages. Synthesized from 37 SEO YouTube transcripts (vault `04 Resources/raw/YouTube Transcripts - SEO Ranking/`) into an actionable pre-publish checklist + site-wide technical audit, tailored to OUR stack and rules (static HTML via tools/render_post.py, owner anonymity, verified-numbers/cite-prior-art discipline, owner-gated outreach). Use when: publishing/rendering a post, the owner says "seo"/"rankuj"/"optimize for ranking"/"SEO friendly"/"rank #1", auditing the site for SEO, or before any `render_post.py --piece`. Two modes: (A) per-post optimization, (B) site-wide technical audit. Goal: rank #1 on Google AND be the cited source in ChatGPT/Perplexity/AI-Overviews for our niche.
---

# /seo — make every Agora publication rank (Google) and get cited (AI search)

**Our unfair advantage, name it first:** we publish *original measured results, replications, and falsifiers nobody else has* (the Crucible). That is exactly what both Google (helpful, original, E-E-A-T content) and LLMs (factual, citable, authoritative statements) reward. SEO for us is **not** keyword-stuffing — it is making our genuinely-unique research **findable, skimmable, and quotable**. The bottleneck has always been distribution; this skill is the on-page + technical half of fixing it. (#1 Google is a long game — authority + freshness + mentions compound over months; on-page SEO is necessary, not sufficient. The compounding lever is *consistent publishing of citable results* + getting *mentioned*.)

**Hard guardrails (never break, even for ranking):**
- **Verified numbers only.** Re-check every cited number vs its source Lab/`.lab.json` before it goes public (existing rule). A wrong stat that ranks is worse than no rank.
- **Anonymity.** Author = the Agora / `…@users.noreply.github.com` identity, never the owner's real name/email. Author schema uses "Agora" (Organization), not a person.
- **Bilingual EN/SK** stays (the toggle). Both languages must be in the served HTML (they are — `<span class="en">/<span class="sk">`), so crawlers see both.
- **Outreach/mentions are owner-gated.** This skill optimizes our OWN pages freely; getting cited on others' sites (Reddit/HN/roundups/Wikidata) is the gated outreach lane — draft, brief in Slovak, let the owner post.
- **No paid-tool dependency.** Use free surfaces: Google Search Console, Bing Webmaster Tools, Google Trends, autocomplete/"People also ask", our local LLM. Don't make the workflow require Ahrefs/Semrush/Surfer.

---

## MODE A — per-post optimization (run this for every post BEFORE `render_post.py --piece`)

Work on the piece spec / draft and adjust the EN + SK bodies and the spec fields. The render template (`tools/render_post.py`) already emits `<title>`, meta description, JSON-LD Article, OG/Twitter tags, tables, blockquote callouts, and SVG figures — use them well.

### 1. One keyword, picked BEFORE finalizing the angle
- Choose ONE primary long-tail query the post targets (3–8 words, high intent, low competition). For us these are specific technical questions, e.g. *"does long context kill RAG"*, *"agent memory poisoning defense"*, *"LoCoMo multi-hop recall benchmark"*. We can win these because almost nobody has the measured answer.
- Mine real demand for free: Google **autocomplete** (type the seed), **People Also Ask**, **Related searches**, and once GSC is live, the **Performance → queries** already showing impressions. Harvest the sub-questions — each becomes an H2 or an FAQ entry.
- Classify intent = **informational** (almost always for us) → the page is an explainer/benchmark, answer-first, not a pitch.
- Reuse our **signature terminology** consistently so AI associates it with us and cites it by name: *Adaptation–Corruption Separation Law, the Crucible, Diversity-Flip Law, inspeximus, RAMR*. Coin a memorable name for each new result.

### 2. The "Three Kings" — primary keyword in all three
- **`<title>`** (spec `title` / `title_sk`): primary keyword **near the front**, ≤ ~60 chars so it doesn't truncate, and **lead with the measured result** for CTR. Good: `"Does long context kill RAG? We measured it"`, `"Memory poisoning hits 70–95% — a corroboration gate stops it"`. Avoid vague clever titles.
- **H1** = the post title (render uses the `# ` line / spec title). Keyword present.
- **First 40 words / first sentence**: state the **direct answer** with the keyword in it. No flowery intro. This is what featured snippets and AI Overviews lift verbatim.

### 3. Slug, description, tags
- **Slug** (spec `slug`): the keyword phrase, hyphenated, concise (`does-long-context-kill-rag`, `memory-poisoning-corroboration-gate`). Controllable per-post; don't make Google guess.
- **Meta description** (spec `desc` / `desc_sk`): 1–2 sentences, includes the keyword, states the result + entices the click. CTR is a signal.
- **Tags** (spec `tags`): the topic entities (e.g. `agent memory · memory poisoning · LLM security · replication`).

### 4. Answer-first, skimmable, citation-shaped body
- **Lead with the result** (and a quotable number/table) high on the page — this is both the snippet bait AND the "frontloaded linkable point" others cite.
- **Heading hierarchy**: logical H2/H3, each answering one sub-question (map People-Also-Ask questions to headings). AI directs answers to the matching heading.
- **At least one list and one table.** Tables of measured results/comparisons get quoted verbatim by AI Overviews/Perplexity and are snippet-eligible. We already do this — keep it.
- **An FAQ block** (3–5 concise Q&A) near the end answering the obvious follow-ups → snippet + AI-citation eligible, and feeds FAQ schema.
- **Semantic coverage, not repetition**: include the related entities/methods/datasets/prior-art the top results cover (we do this naturally — name the real papers, datasets, methods). Never keyword-stuff.
- **E-E-A-T = our moat**: first-hand experiment (we ran the Lab), cite reputable sources + prior art, state the falsifier and the honest limits/boundary. Show the measured numbers. This is exactly what Google's helpful-content + AI trust both want.
- **Internal links (topic cluster)**: link the post to ≥3 related Agora posts and back to a pillar (e.g. an "agent memory" hub). Internal links are the only backlink we fully control; they spread authority across the cluster.
- **Outbound links** to the authoritative sources we cite (the papers we replicate) — signals topical context and satisfies our cite-prior-art rule.
- **Figures with descriptive alt text** (our SVG `<figure>` should carry a meaningful `aria-label`/`<figcaption>` — already does). Charts get cited by AI more than prose.

### 5. AEO/GEO layer (rank in AI answers)
- **Mirror the ideal AI answer**: concise direct answer first, supporting detail after. When the engine drafts an answer and looks for corroboration, exact-match structure → "this confirms it" → we get cited.
- **Make data explicit** as numbered lists/tables (not buried in prose) — AI preferentially pulls original data + comparisons.
- **LLM-summary self-test (pre-publish GATE):** paste the finished post into our local strong model and ask it to summarize + list the key claims:
  ```bash
  # uses our local reasoning model (glm-5.2 via Ollama cloud-route); cloud-free-OK (data, not generation of claims)
  ```
  Run it through `agora.execution.llm_client.call_llm(sys="Summarize this article and list its key factual claims with numbers.", usr=<post text>, tier="medium")`. **If the summary misses or mangles a key result, rewrite for clarity until the model gets it right.** If our own strong model can't extract the finding cleanly, neither will ChatGPT.

### 6. Schema (JSON-LD) — verify/extend the rendered HTML
- **Article/BlogPosting** (render already emits this) — confirm `headline`, `datePublished`, `dateModified` (update on edits), `author` = Organization "Agora", `inLanguage` ["en","sk"].
- **Add FAQPage** JSON-LD when the post has an FAQ block (machine-parseable Q&A → snippet + AI).
- **Add Organization** site-wide (name "Agora", logo, sameAs the GitHub/HF/Zenodo URLs) so AI knows who we are.
- **Consider `Dataset`** schema for Crucible/benchmark posts (we publish `crucible.json` — machine-readable; mark it up).
- *(If the render template lacks FAQ/Organization/Dataset/canonical/hreflang, that's a Mode-B implementation task — add it to `tools/render_post.py` once, then every post benefits.)*

### 7. Publish + index
- Render (`render_post.py --piece`), verify deploy 200 (existing flow), then **request indexing** in Google Search Console (Inspect URL → Request indexing) and confirm the URL is in `sitemap.xml`. Submit to **Bing Webmaster Tools** too — **ChatGPT search uses Bing's index**, so Bing presence is disproportionately valuable for AI visibility.

---

## MODE B — site-wide technical audit (run occasionally; "the Claude-Code audit loop")

Run a thorough pass over `public/` and `tools/render_post.py`; fan out sub-agents (one each for: missing/weak meta descriptions, missing alt text, internal-link opportunities, schema gaps, page-speed/image weight). Fix:

- **sitemap.xml** — generate one listing every post URL with `<lastmod>`; add to `tools/render_post.py` build (static site → must be scripted, not a plugin). Submit to GSC + Bing.
- **robots.txt** — exists, not `Disallow: /`; **explicitly allow AI crawlers** (`GPTBot`, `Google-Extended`, `bingbot`); add the `Sitemap:` line.
- **Canonical tags** — per-page `<link rel="canonical">` to the preferred URL (avoid http/https, trailing-slash, query dupes diluting signals).
- **hreflang** — we serve EN+SK in one page via the toggle; add `hreflang` annotations (or document the decision) so the bilingual content isn't read as duplicate. *(Our render keeps both languages in served HTML; decide one-URL-both-langs + `inLanguage` vs separate URLs — note in the post template.)*
- **No stray `noindex`**; every real post resolves `index,follow`.
- **Speed**: convert figures to WebP where raster; keep assets lean; lazy-load below-the-fold; GitHub Pages CDN is already fast — just don't bloat. Check with Google PageSpeed Insights.
- **Semantic HTML**: content in `<main>`/`<article>`, clean H1→H2→H3 (render already does).
- **Text in served HTML** (not JS-injected) — we're static, keep it; never hide post text behind JS-only rendering (crawlers + AI bots largely don't run JS).
- **Crawl depth ≤ 3 clicks** from the homepage to any post; keep the index/nav flat.
- **Measurement**: set up **Google Search Console** + **Bing Webmaster Tools** + GA4 for the domain (owner action — provide the steps; he verifies ownership). Then the loop: GSC Performance → Pages, **Compare** last 28d vs previous, act on rising winners (double down) and decayers (refresh the post, bump `dateModified`, re-request indexing). Pages ranking **positions 5–15** are the low-hanging fruit — inject the keyword into the Three Kings and re-index for outsized CTR jumps.

---

## Reusable SEO post structure (the writing template)
1. **Keyword + intent** chosen first; SERP + People-Also-Ask scanned.
2. **Headline** ≤60 chars, keyword near front, **leads with the measured result**.
3. **Answer-first intro** — direct answer + keyword in the first 40 words.
4. **Body** — H2/H3 per sub-question; ≥1 list + ≥1 results table; semantic/entity coverage; internal+outbound links; quotable stat/table frontloaded.
5. **Figure(s)** with alt text/figcaption (SVG charts of the measured result).
6. **Falsifier + honest limits** (our standard) — doubles as E-E-A-T.
7. **FAQ** block (3–5 Q&A) → FAQ schema.
8. **Conclusion** with a next-step internal link (no dead end) + the repo/inspeximus CTA.
9. **Schema** (Article + FAQ + Organization), **canonical**, **dates**.
10. **LLM-summary self-test** passes → render → request indexing (Google + Bing).

## Provenance
Synthesized 2026-06-27 from 37 transcripts in the vault `04 Resources/raw/YouTube Transcripts - SEO Ranking/` (general Google SEO, technical SEO, keyword research, SEO blog-writing, AI-search/AEO/GEO/LLMO; off-target YouTube/local/WordPress/Instagram/e-commerce tactics deliberately excluded). Keep this skill updated as search/AI-search rules change (the 2026 transcripts already show the shift from clicks → AI citations).

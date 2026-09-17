---
name: dev-tool-launch
description: How a developer tool gets found and adopted. Use BEFORE writing or editing any README, project site, landing page, PyPI description, dev.to article or launch post for inspeximus, RAMR or Agora, and whenever the owner asks why nobody finds us, how to get stars, traffic or users, or to "marketingovo vytiahnut" a product. Built 2026-09-17 by measuring the first screen of the five highest-starred READMEs in our category (mem0 65k, LangGraph 42k, cognee 31k, Graphiti 31k, Supermemory 30k), two Eddie Jaoude videos on open-source promotion, one video on ranking a niche site with one page per high-intent query, and our own Search Console. Not recalled; measured.
---

# Developer-tool launch: what the winners' first screen holds, and what ours lacked

## Why this skill exists

On 2026-09-17 the owner asked why the EU AI Act evidence work brought nobody. Search Console
answered: 1 of 6 inspeximus pages indexed, 0 external links, the AI Act page linked from nowhere
(the README linked a docs file instead), both sitemaps "Couldn't fetch" for weeks, and the README
opened with 313 words of essay before the first code block. I had written the README from taste.
This file is the measurement I should have made first, so the next surface is built from it.

## The first screen, measured on the leaders

Word position of the first element, from the raw README (2026-09-17):

| repo | stars | first image | first H2 | first code | badges on top | headline number on screen 1 |
|---|---:|---:|---:|---:|---:|---|
| mem0 | 65,480 | 4 | 114 | 536 | 9 | benchmark table as the FIRST H2 (LoCoMo 92.5, LongMemEval 94.4) |
| LangGraph | 41,806 | 13 | 144 | 91 | 4 | one bold line: "Low-level orchestration framework for building stateful agents" |
| cognee | 30,763 | 4 | 214 | 380 | 8 | one line of what it is, then "When to use" |
| Graphiti | 30,953 | 4 | 263 | 1,263 | 8 | "What is a Context Graph", then "Why Graphiti" |
| Supermemory | 29,858 | 2 | 303 | 803 | 3 | "#1 on every major AI memory benchmark; 95% Recall@15 with 99.4% context reduction" |
| inspeximus, before | 6 | 10 | 365 | 313 | 11 | none; a medieval-charter etymology instead |

Every leader's first screen is the same seven blocks, in this order:

1. Centered logo or banner image.
2. **One bold sentence that claims the category.** "The Memory Layer for Personalized AI."
   "State-of-the-art memory and context engine for AI." "The Open-Source AI Memory Platform for
   Agents." Category noun first, differentiator second, no hedging.
3. A link row: Docs · Quickstart · Demo · Discord (or the equivalents you have).
4. Badges: PyPI version, downloads, license, CI, stars. Five to nine.
5. **The headline number**, on the first screen, in a table or one bold line. It is the number
   the reader repeats to a colleague. mem0 puts its benchmark table before any prose.
6. Two or three sentences of what it is and who it is for, then a feature table (one row per
   capability, one line each; Supermemory uses an icon column).
7. Install and a five-line example, within the first 100 to 550 words.

Everything else (architecture, method, caveats, history, the name's etymology) comes after the
first code block. The leaders keep it; they do not open with it.

## What the promotion videos add (Eddie Jaoude, 2 videos; 1wKtKFY_ueM, bASuF1TbMy4)

- The repo description must make the project understood "within a few seconds"; it is the first
  text GitHub search and Google show.
- A screenshot or GIF near the top: "the first thing people see is a screenshot, that's what they
  want." One or two, not ten.
- Quickstart plus a tech stack line plus documentation; onboarding is iterated with newcomers
  ("if you can't tell me what the project does from the README, the README is wrong, not you").
- GitHub Community Standards all green: description, README, code of conduct, license,
  CONTRIBUTING, issue and PR templates. People search GitHub by issue label; use
  `good first issue` on real issues, and keep issues open even when working alone.
- Hide unused sidebar sections (Packages, Environments) so the repo does not look dormant; use
  Releases with a changelog, since releases are the visible heartbeat.
- Do not spam links. Ask for a star only once traction exists, and rarely.

## What the SEO method adds (gWNFna6fgS8, one page per high-intent query)

- List 25 to 50 queries, then classify each by intent and buying stage. Only high-intent ones
  get a page.
- **One dedicated page per query** ("supply" for the "demand"). A niche with few competitors
  ranks in days to weeks; a broad term takes months.
- On every page: title carrying the query, meta description, schema, alt text, and internal
  links to every related page. Internal links were the single biggest lever in that run.
- Measure in Search Console weekly: indexed pages, sitemap status, queries, links.

## The checklist, in order (each item is a measurement, not an opinion)

1. **Index first.** Search Console: pages indexed vs known vs in the sitemap; sitemap status;
   external links. A page with zero inbound links from README, site root and storefront is
   "crawled, not indexed" by default. Fix links before touching copy.
2. **Repo description and topics** carry the category and the query words (they did by 09-17).
3. **README first screen** follows the seven blocks above. Check with
   `probes/readme_first_screen.py`-style counting: first image, first H2, first code block,
   headline number present.
4. **One page per high-intent query** on the project site, each with title, description, schema,
   and links to the others and back to the README. The query list lives with the page.
5. **Distribution surfaces that already rank** for the query: dev.to (canonical to our page),
   the framework's own issue tracker where a feature request matches what we ship, Glama and
   PyPI listings. Each goes through the outbound gate.
6. **Community Standards** green, `good first issue` labels, releases with notes, unused
   sidebar sections hidden.
7. **Weekly read** of Search Console into the loop, with the four numbers above.

## What this does not override

The standing gate (validate, storm, stress-claim, verify-claims, humanizer) still decides
whether a claim is true. This skill decides where it sits on the page and whether anyone can
find it. A headline number goes on the first screen only if it already passed the gate and its
artifact is named. And "honest" is not a reason to bury a capability we ship; a scope note is one
sentence at the end of the section, not the section's first line.

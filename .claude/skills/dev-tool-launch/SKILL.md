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


## What the frames showed that the transcripts did not (watched 2026-09-17, frame by frame)

Eddie Jaoude's repo walkthrough (bASuF1TbMy4), the screen itself:
- The repo header carries 40 open issues, 12 open PRs, Discussions ON, 34 labels in three axes
  (`aspect: interface`, `goal: improvement`, `talk: discussion`), milestones, and "Open in Gitpod"
  on every PR. A repo that looks worked-on is the first trust signal, before the README.
- A product screenshot sits inside the README, not a chart about the product.
- Community profile: every row green (description, README, code of conduct, contributing,
  license, issue templates, PR template). Ours was 57% until 2026-09-17.
- Repo settings: website URL and topics filled; unused sidebar sections (Packages, Environments)
  hidden so the page does not read as dormant; Releases used as the visible heartbeat.

Matthew Yonkovit's slides (CFIVdndP5Hs):
- The funnel: millions who could use it -> tens of thousands who find it (awareness) -> thousands
  who try it (easy) -> hundreds who rely on it (a kick-ass product). Driving awareness before the
  product is ready "can damage your project's reputation"; early days go to product and engineering.
- Good docs, nine points: explains the project and use cases in common language; understood in
  10 seconds on the first page; visuals, even unpolished; navigation easy; install instructions
  AND recipes/examples/tutorials; installation covers the common scenarios; language-specific
  examples in separate sections; a way to give feedback; docs as a repo.
- Free-to-paid converts on: better security, support ("the insurance"), zero ops, automation,
  and company policy: "companies may have specific compliance requirements". That is the
  inspeximus-pro pitch in one slide.
- Open-source adoption is not commercial success; track both, with different metrics.

The AI-search video (bhTo8fDmr5I) demoed a content editor: pages built as an outline of questions
(H2 = the question), each section with a fact and its source, and a "topics and questions" panel
listing what competing pages answer. That is the page template for every query page we build.

YC's dev-tools talk (z1aKRhRnVNk), transcript read in full: nobody knows you, so the first users
come from personal outreach, not inbound; launch on Show HN and launch again on every release
(Ollama did; Supabase runs a launch week each quarter); reply to every comment, including the
hostile ones, for the benefit of the readers; open source is the go-to-market for a library;
the paid tier is the enterprise set (SSO, audit logs, disaster recovery, SLA); sell with a demo,
never a deck; "documentation is marketing" and a feature is not done until its doc is.

## Where the transcripts live

`agora_output/study/videos.jsonl.gz` (deduplicated, 12 videos, 102 KB) with an index in
`agora_output/study/videos.md`. `python tools/watch_library.py list`. Temp directories from
/watch are deleted by `python tools/watch_library.py clean` after each study pass.

## What this does not override

The standing gate (validate, storm, stress-claim, verify-claims, humanizer) still decides
whether a claim is true. This skill decides where it sits on the page and whether anyone can
find it. A headline number goes on the first screen only if it already passed the gate and its
artifact is named. And "honest" is not a reason to bury a capability we ship; a scope note is one
sentence at the end of the section, not the section's first line.

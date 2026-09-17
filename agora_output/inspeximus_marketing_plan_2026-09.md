# inspeximus: the distribution plan, 2026-09-17

Owner's order of priority: marketing first, SEO second, AEO third, indexing fourth. Built from
measurements made today (Search Console on all five properties, the first screen of the five
highest-starred READMEs in the category) and from eight talks read in full as transcripts:
Lee Robinson (Vercel) on developer marketing, Y Combinator on dev-tools companies, Eddie Jaoude
(two) on open-source promotion, Ahrefs and two others on answer-engine optimization, Matt Kenyon on
the three-step SEO playbook, Matthew Yonkovit on growing open-source adoption, and a short on
launching on Hacker News. What each source says is marked; what we measured is marked.

## Where we stand (measured 2026-09-17)

| surface | state |
|---|---|
| GitHub stars | 6 (mem0 65,480; Supermemory 29,858) |
| Search Console, inspeximus, 3 months | 1 click, 47 impressions, 0 external links |
| Agora homepage | not on Google; last crawl 2026-07-12; requested today |
| sitemaps, all five | "Couldn't fetch" for weeks; live test fetches them; resubmitted today |
| README first screen | rebuilt today to the leaders' seven blocks (131560c, 64eb5a1) |
| ai-act.html inbound links | 0 before today; README, storefront and root site now link it |
| erasure.html, audit-trail.html | live 2026-09-17 on 2.39.1 after a 3-lens red team (four verifier holes fixed first); IndexNow accepted, GSC request queued for the quota reset |
| good first issues | #30 to #33 open, labels in three axes, Discussions on |
| LangChain #35357 / #35691 | KILLED at the pre-draft read: closed vendor pile-ons, maintainer hides pitches |
| dev.to article | drafted, gated, canonical to ai-act.html; needs the owner's dev.to account |
| category queries ("EU AI Act Article 12 logging agent", "agent memory GDPR erasure") | we appear nowhere; dev.to posts, PLUR (3 posts), LangChain issue #35357, supra-wall, asqav do |

## 1. Marketing (first)

What the sources agree on, and how it lands here:

**Trust is the product (Robinson, Yonkovit).** Developers adopt after a reproducible demo and
docs that get them running in minutes; an over-promised demo costs trust that does not come back
("the Devon controversy"). We already hold the strongest trust asset in the category: every number
ships with a probe. It is not on the first screen of anything except the README as of today.
- Action, done today: README first screen carries the measured tables as the first heading.
- Action, this week: a "Why inspeximus" section (cognee and Graphiti both have one) that states in
  five lines who this is for and who it is not for. Gated only by claims audit.
- Action, this week: `good first issue` items on real work (Eddie: people search GitHub by label;
  an empty issues tab reads as a dead project). Community Standards to 100% (done today: 57% ->
  files added).

**Free tier and self-serve (Robinson, YC).** `pip install inspeximus` with zero dependencies is
the free tier; the MCP one-liner is the self-serve path. Both exist. Neither is on the first
screen of the project site. Action: the site's first screen gets the same seven blocks as the
README, with the one-liner above the fold.

**Launch where the audience is technical (YC, HN short).** Hacker News over Product Hunt for a
dev tool; "Show HN" with a technical title, the author present in comments the whole day, no
marketing copy. The launch asset is the measurement nobody else publishes: "we measured how often
mem0, Graphiti and inspeximus resurrect a corrected fact". Gated: owner approval, and the
launch text goes through the standing gate. Timing: after the product GIF and the "Why" section,
not before; a launch that lands on a README without social proof wastes the one shot.

**Content that developers actually read (Robinson, Yonkovit).** Tutorials, walkthroughs and
worked examples outperform announcements; "most developers go directly to the code". Action:
each page on the site opens with the runnable command and its printed output, then the prose.
`compare.html` already does; `ai-act.html` will.

**Talk to developers (Robinson, YC, Yonkovit).** The threads we are already in (claude-code
#82056, #81081, agmi PR #1, DeepSeek #1644, hermes #23367) are the developer conversations; they
are our distribution today and they produced every external mention we have. Keep the cadence:
one measured reply per thread event, through the gate.

**Risk avoided, not upside gained (Grosser).** Buyers reduce risk about four times as often as
they buy upside. Every page's first sentence names the risk the reader avoids: an auditor they
cannot answer, a DSAR they cannot prove, a correction that came back. Done today on the two new
pages (erasure, audit trail); the index hero still leads with the mechanism and gets the same edit.

**Word of mouth over paid (all).** Nobody in the sources recommends ads for a dev tool at this
stage. No budget is proposed.

## 2. SEO (second)

**The three-step playbook (Kenyon), applied.**
1. Keywords by intent. The list, classified (bottom of this file). Only high-intent queries get a
   page; a niche with few competitors ranks in weeks (the Claude-Code SEO run), a head term takes
   months.
2. The best page for the query: title carries the query, opens with the answer, one runnable
   command, a table, internal links to every related page, schema. One page per query.
3. Authority: interrelated pages first (topical cluster with internal links), then backlinks.
   Backlinks we can earn without asking: dev.to canonical posts (they link back), Glama and PyPI
   listings (exist), the framework threads where we post measurements (exist), and answers on
   the LangChain #35357 request.

**Cluster for this quarter (the pages):**
- `ai-act.html`: "EU AI Act Article 12 logging for AI agents" (exists; retitled today)
- `compare.html`: "does agent memory keep a correction: mem0 vs Graphiti" (exists)
- `claude-code.html`: "persistent memory for Claude Code" (exists)
- new: "GDPR right to erasure for AI agent memory" (erasure certificate, `forget_subject`,
  `export_subject`, Art. 15/16/17), the query PLUR ranks for with three posts
- new: "audit trail for AI agents: what the agent knew when it acted" (action ledger,
  `matches()`, agent-audit-trail export)
- ~~new: "mem0 to inspeximus migration"~~: live 2026-09-17 as migrate-from-mem0.html on 2.41.0, with a
  real `import-mem0` run (no migration doc existed before; the importer was built for the page and the
  red team's re-import-after-erasure break was fixed in code first)
Each new page: claims reused from already-gated pages or the README; anything new goes through
the gate.

## 3. AEO (third)

**What gets cited by AI answers (Ahrefs, the 2026 AI-search talk):** brand mentions across the
web are the strongest lever; on-page, a question as the heading and a direct answer in the first
two sentences under it, FAQ blocks, statistics with a named source, author and organization
schema, and covering the topic from every angle so the page is one of the ~5 sources an answer
draws on. Traditional SEO remains the foundation.
- Action, today: `llms.txt` at the site root naming the pages and what each answers (the AI
  crawlers are already allowed in the root robots.txt).
- Action, this week: FAQ schema on `compare.html` and `claude-code.html` (`ai-act.html` has one);
  each H2 phrased as the question a developer types; the first two sentences under it are the
  answer with the number and the probe.
- Action, ongoing: mentions. Every measured reply on a maintainer's thread is a mention on a
  high-authority domain; that is why the thread work stays in the plan.

## 4. Indexing (fourth, mostly done today)

Done: sitemaps resubmitted (agora, inspeximus), the wrong `/sitemap.xml/` removed, indexing
requested for 11 URLs until the daily quota, IndexNow accepted 226 URLs from all five sitemaps.
Open: the remaining Agora pages and the root homepage after the quota resets; re-read the five
sitemap rows in seven days; a weekly Search Console read (indexed vs known, sitemap status,
queries, links) into the loop.

## Cadence

- Weekly: Search Console read; one new query page or one refreshed page; one measured thread
  reply if a thread moved.
- Monthly: re-measure the category queries (who ranks; are we in the top 10), star and download
  counts, external links.
- Once, when the GIF and the "Why" section exist: the Show HN, gated.

## Query list, classified

| query | intent | page |
|---|---|---|
| EU AI Act Article 12 logging AI agent | high, buying | ai-act.html |
| AI agent audit trail EU AI Act | high | ai-act.html, new audit-trail page |
| GDPR right to erasure AI agent memory | high | new erasure page |
| delete user data from AI agent memory | high | new erasure page |
| agent memory audit trail python | high | new audit-trail page |
| mem0 alternative | high | compare.html, migration page |
| mem0 vs graphiti | medium | compare.html |
| persistent memory Claude Code | high | claude-code.html |
| MCP memory server | high | claude-code.html, index |
| tamper-evident agent memory | medium | index |
| agent memory correction supersede revert | medium | compare.html |
| zero dependency python agent memory | low | index |

## What this plan does not do

It does not promise a rank or a date. Rankings depend on links we cannot manufacture, and the
sources say so. It does promise that every surface a searcher or an answer engine can reach
carries the capability, the number, and the command, in that order.

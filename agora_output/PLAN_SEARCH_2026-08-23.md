# Search plan — what the Search Console export actually says, and what to do about it

Written 2026-08-23 from the owner's GSC export (`Performance on Search`, Web, last 3 months, data
2026-06-26 → 2026-08-20). Companion to `PLAYBOOK_DISTRIBUTION.md`, which covers the *referral*
channel (HN / GitHub / Reddit). This one covers *search*, and the two do not compete: on the numbers
below, search is currently the weaker of the two by a wide margin.

Every figure here is from the export or from a sweep of the deployed site run today. Where I could not
measure something, it says so and it becomes step 0 rather than an assumption.

---

## 1. The drop is real, and it is smaller than it sounds because the base was near zero

Matched 28-day windows, so the comparison is not an artifact of window length:

| window | days | impressions | mean/day | median/day | zero-impression days |
|---|---|---|---|---|---|
| 2026-06-26 → 07-23 | 28 | **325** | 11.61 | 8.0 | 1 |
| 2026-07-24 → 08-20 | 28 | **55** | 1.96 | 1.5 | 4 |
| change | | **−83%** | −83% | **−81%** | |

The median is there deliberately. The early window contains four spike days (30, 40, 30, 33
impressions) and a low baseline, so a mean-only comparison could be one crawl event dressed up as a
trend. It is not: the median falls by 81% as well. **The drop is genuine.** The owner said "roughly
90%"; measured, it is 83%.

**And now the number that reframes the whole exercise.** Over the entire 56 days the site received
**5 clicks**. All five came from Slovakia, at average position 3, with an 83% click-through rate.
Every other country combined — 257 impressions from the United States, 22 from the UK, and 37 further
countries — produced **zero clicks**.

A position-3 result with 83% CTR from our own country is us, checking our own site.

> **External clicks over 56 days: approximately zero, before the drop and after it.**

So the honest statement of the problem is not "we lost our traffic". It is: **we never had any, and
the thing that fell by 83% was our visibility in impressions, from 8 a day to 1.5 a day.** Restoring
the July number would restore nothing a business could use. That has to change what we work on.

## 2. Only three URLs have ever been seen

The sitemap declares **135 URLs**. The export's page report lists **three**, and they account for all
384 impressions:

| page | impressions | clicks | avg position |
|---|---|---|---|
| `/agora/` (home) | 225 | 5 | 11.35 |
| `/agora/public/crucible/index.html` | 83 | 0 | 6.52 |
| `/agora/public/crucible/` | 76 | 0 | 21.72 |

**132 of 135 pages have never produced a single impression in eight weeks.** Not a low number — zero.
Every post, every Slovak translation, the leaderboard, the comparison page: nothing.

That is the actual problem, and it dwarfs the 83%.

The two crucible rows are one page seen under two URLs. I checked the live site: `index.html` carries
`rel="canonical"` pointing at the directory form, which is correct. Google is still reporting both
while it consolidates. **Nothing to fix there** — I nearly filed it as a defect and the check said
otherwise.

## 3. The technical layer is not the cause

Full sweep of all 135 sitemap URLs on the deployed site, today, 16 workers:

| check | result |
|---|---|
| HTTP status | **135/135 return 200** |
| `noindex` | 0 (one post carries it deliberately and is not in the sitemap) |
| canonical pointing elsewhere | **0** |
| duplicate `<title>` | **0** — 135 unique titles over 135 pages |
| duplicate meta description | **0** |
| missing title / description | 0 / 0 |
| pages with no `<h1>` or more than one | 0 / 0 |
| thin content (< 300 words) | **0** — min 347, median 1230, max 7757 |
| orphans (zero inbound internal links) | **3** of 135 |
| root `robots.txt` | 200, permissive, declares both agora sitemaps |
| sitemap freshness | live, `lastmod` current to 2026-08-22 |

There is no crawl blocker, no indexation blocker and no duplication problem on the live site. The SEO
work that was done is intact and technically correct. **Whatever caused the drop, it is not a broken
tag.**

> **Instrument note, because it nearly produced a false headline.** My first sweep reported *124 of
> 135 pages have no internal links*. That was my regex, which looked for `href="/agora/…"` while the
> site uses absolute URLs and relative paths. The homepage has 25 internal links and the corrected
> graph gives a median of 3 inbound links per page and **3 orphans, not 124**. A number that alarming
> should be checked against its own instrument before it reaches a plan.

## 4. What did change, and how confident I am

Two site-wide changes sit in the window:

- **2026-07-21** — `847eea7` rebrand of the storefront and posts from Agora to inspeximus, plus
  `f1a494a` and `d1d29c4` purging the old name.
- **2026-07-28** — `918f3d7` one URL per language, English in place and Slovak under `/agora/sk/`,
  followed the same day by four commits fixing defects that split introduced (`880d8aa` JSON-LD
  clobbering, `6d4bd1d` two canonical defects, `b3f8496` a sitemap the deploy was not staging).

The impressions fall begins **2026-07-25/26**, four to five days after the rebrand, which is the right
lag for a re-crawl of a small site.

**I cannot prove the rebrand caused it.** At 8 impressions a day the series is too small to separate a
site-wide cause from ordinary variance, and the average position moved earlier and in the opposite
direction (worsening from ~6 to ~21 around 2026-07-10, then recovering). Anyone claiming certainty
here is guessing. What is defensible: it is the only site-wide content change in the window, and the
timing fits.

**What I did find, measured on the live pages:**

| where the brand appears | count |
|---|---|
| `<title>` ends with "Agora" | **132 of 135** |
| `<title>` mentions inspeximus | 2 |
| `<h1>` contains "Agora" or "inspeximus" | **0 of 135** |

The homepage sells inspeximus; 132 page titles are branded Agora; no H1 anywhere names either. For a
site with no external authority, the entity name in the most heavily weighted on-page element is one
of the few signals we fully control, and it currently says two different things. This may be
deliberate — Agora the research organisation, inspeximus the product — but if so it is a decision
nobody wrote down, and Google is being asked to work it out from a split signal.

## 5. The blocking unknown, which is step 0

The 132 zero-impression pages are in one of two states, and **the export the owner sent cannot tell
them apart**:

- **Not indexed** — Google knows the URL and chose not to store it. Fix: indexation, internal links,
  crawl demand, quality signals.
- **Indexed and never ranking** — stored, but never in the top ~100 for anything anyone types. Fix:
  query targeting, which means changing what we write about.

**These require opposite work.** Writing the rest of this plan without knowing which is the mistake
the owner is objecting to in the first place.

The answer is one screen in Search Console. The needed export is **Indexing → Pages** (Slovak:
*Indexovanie → Stránky*), which gives "Indexed" vs "Not indexed" with a reason per URL. The
performance export he sent does not contain it.

---

# The plan, in the order it should be worked

Ordered by expected effect on the actual bottleneck, not by how much it looks like SEO. The classic
on-page fixes are near the bottom on purpose: they improve pages that get impressions, and 132 pages
get none.

### S0 — Get the indexation report *(blocking, 5 minutes, owner)*
Search Console → *Indexovanie → Stránky* → export. It returns the split between indexed and
not-indexed with a reason ("Crawled – currently not indexed", "Discovered – currently not indexed",
"Duplicate", "Excluded by noindex").
**Decides:** whether S1 or S2 is the real work.
**Success:** we know the number. Everything below is provisional until we do.

### S1 — If the pages are NOT indexed: earn crawl demand
A site on a GitHub Pages subdirectory with essentially no inbound links has almost no crawl budget.
"Crawled – currently not indexed" on a 1,200-word technical post is Google saying *this is fine and
nobody has given me a reason to keep it*.
- Link the three orphans: `/public/leaderboard/`, `/public/compare/`, `/agora/sk/public/posts/`.
- 37 pages have exactly one inbound link. Every post should be reachable in two clicks from the home
  page and linked from at least two sibling posts on the same topic.
- Real backlinks are the lever, and we already have the sources: the DeepSeek-V3, claude-code, CML,
  memex and RAMR threads where our work is cited by name. A Zenodo DOI. PyPI. These are the only
  external signals we own — and none of them currently point at a *post*, they point at repos.
**Expected effect:** this is the one that can move a zero. Slow — weeks.

### S2 — If the pages ARE indexed: we are writing for queries nobody types
The evidence is already in the export. The single biggest query is **"zero proof ai mcp receipts"** —
63 impressions at position 8.48 — a problem-shaped phrase. Second is **"crucible ai"**, 20
impressions at position 58.85. Everything else is one impression each, including three junk matches
for other products called Agora.

Meanwhile our titles read like this:
- *"We looked for the grounding 'tipping point' in AI self-training…"* (119 chars)
- *"A reality-check on agent-memory poisoning defenses: you pric…"* (102)
- *"The same classical tradeoff in four AI-memory mechanisms — a…"* (86)

These are essay titles. They are good essay titles. Nobody searches them.
- Pick **five** queries with real volume that our existing work already answers, and build or retitle
  one page each. We have no keyword-volume data in-house — this needs a source (GSC's own query
  report once there is traffic, or a keyword tool).
- The one page that already earns impressions at position 8.48 gets **zero clicks**. That is a
  title/snippet problem on a page we already rank on, and it is the cheapest CTR win available.
**Expected effect:** the only route to non-zero clicks that does not depend on authority.

### S3 — Settle the brand, once, in writing
Decide whether the entity is Agora, inspeximus, or Agora-the-org publishing inspeximus-the-product,
then make the titles, the H1s and the `Organization` JSON-LD agree. 0 of 135 H1s naming either is not
a strategy, it is an omission.
**Cost:** one decision from the owner, then a scripted pass.
**Caution:** do not churn titles that already rank. Three pages have impressions; leave those two
crucible URLs alone.

### S4 — Cut the titles to a length Google will show
115 of 135 titles exceed 60 characters — median 80, max 149. Google truncates around 60. The keyword
belongs in the first 60 characters and on most of our pages it is past the cut.
**Expected effect:** real but small, and only on pages that get impressions. Deliberately ranked below
S1–S3 despite being the most obvious "SEO fix" on the list.

### S5 — Decide what the Slovak half is for
64 of 135 URLs are Slovak translations of English-language technical research. Slovak search volume
for "agent memory provenance" is effectively zero. They consume half the crawl budget and half the
internal link equity of a site that has very little of either.
**This is the owner's call, not mine** — there may be reasons for the Slovak half that have nothing to
do with search. But it should be a decision, not a default.

### S6 — Stop measuring this channel weekly
At 1.5 impressions a day, week-to-week movement is noise. A single query drifting three positions
moves the percentage more than anything we do. Review on a **monthly** cadence against the two numbers
that matter, both currently zero: *pages with at least one impression* (3 of 135) and *external
clicks* (0).

---

## What I would do first, if it were my call

**S0 today** — it is five minutes and it decides everything else.

Then, whatever S0 says: **S1's backlink half**, because it is the only item on this list that
addresses why 132 pages are invisible, and because it is the same work `PLAYBOOK_DISTRIBUTION.md`
already argues for on its own merits. Those GitHub threads are the only external signal we have, and
right now every one of them points at a repository instead of at a page that could rank.

The on-page work — S3, S4 — is a day's scripting and should be done, but nobody should expect it to
show up in the numbers. It is hygiene on a site whose problem is that almost nothing links to it.

**And one thing not to do:** do not revert the July SEO work. It is measurably correct on the live
site, and rolling it back would trade a clean technical layer for a hypothesis I have already said
cannot be proven at this volume.

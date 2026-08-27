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

## 4. ANSWERED — the coverage export, and it is a third state

*Added later on 2026-08-23, from the owner's `Coverage` export (`Indexovanie → Stránky`, "all known
pages"). It answers §5's blocking question and it overrides the attribution in §4 below, which is kept
because being wrong in a documented way is cheaper than quietly editing it out.*

**Google has never known more than three URLs of the 135 in our sitemap.**

| date | URLs Google knows | indexed | not indexed |
|---|---|---|---|
| 2026-06-30 | 2 | 2 | 0 |
| 2026-07-01 | **3** | 3 | 0 |
| 2026-07-11 | 3 | 2 | 1 |
| 2026-08-06 → today | 3 | **1** | 2 |

Maximum ever discovered: **3**. Currently indexed: **one page**. The two non-indexed are "Alternate
page with proper canonical tag" (the crucible `index.html`, working as designed) and "Crawled –
currently not indexed".

So §5's question — *not indexed, or indexed and never ranking?* — had a third answer I did not offer:
**132 of 135 URLs were never discovered at all.** Not crawled and rejected. Not seen.

And the impressions track the index count almost exactly:

| period | index state | impressions/day (mean) | median |
|---|---|---|---|
| 06-30 → 07-10 | 3 indexed | 9.91 | 7.0 |
| 07-11 → 07-24 | 2 indexed | 10.64 | 8.5 |
| **07-25 → 08-05** | **2 indexed** | **2.50** | **2.0** |
| 08-06 → 08-17 | 1 indexed | 1.67 | 1.5 |

Control, with the four spike days (≥25 impressions) removed, the ordering holds: 7.22 / 6.15 / 1.67.

**There are two separate hits, not one, and I had merged them:**

- **A · 2026-07-25** — impressions fall from 10.6 to 2.5 a day **while the index count does not move**.
  This is a ranking loss on pages that stayed indexed. It is four days after the 2026-07-21 rebrand,
  which is the only site-wide content change in range.
- **B · 2026-08-06** — a page is dropped from the index, 2 → 1, and the site settles at 1.67 a day.

Hit B is not the rebrand: it is fifteen days later and it is a deindexing, not a demotion.

**What this does to the plan below.** S2 (query targeting) is premature — you cannot rank pages Google
has not found. S4 (title lengths) is cosmetic on 132 invisible pages. The entire problem is
**discovery**, and the sitemap that declares 135 URLs has produced **zero** discovered URLs in eight
weeks, which is the strongest available evidence that **Google is not processing our sitemap at all**.

That is now the one thing to check, and it is one screen: **Search Console → Indexovanie → Sitemapy** —
does it say success, and how many URLs did it report discovering? A note in our own memory says it once
showed *"Nie je možné načítať"* and we recorded that as "async, normal". On this evidence that
assumption was never re-checked and may have been wrong for two months.

## 4d. ANSWERED, with a date: Googlebot stopped visiting on 2026-07-30

*The root property's `robots.txt` report, readable only after verifying the host-root property today.*

```
https://dancenitra.github.io/robots.txt
  Posledná kontrola:  30. 7. 2026 19:26
  Stav:               Načítané          995 B      Problémy: —
```

Google fetched it successfully and **has not fetched it since — 24 days**. Googlebot re-reads
`robots.txt` roughly daily for any host it actually crawls. Twenty-four days without a re-read means
one thing:

> **Googlebot has not been crawling `dancenitra.github.io` since 2026-07-30.**

It fits every number in this document:

| evidence | date |
|---|---|
| last `robots.txt` fetch | **2026-07-30** |
| index fell 2 → 1 | 2026-08-06 |
| impressions settle at 1.67/day | from 2026-08-06 |
| four sitemaps, never read | submitted 07-30, 08-05, 08-23, 08-23 |
| URLs Google knows | 3, since 2026-07-01 |

**And it re-reads the sitemap status.** "Nie je možné načítať" does not mean the fetch failed. It means
the fetch was **never attempted**, because the host is not being crawled. That is why all four failed
identically regardless of file, project or submission date — and it is why hours spent inside the
sitemap XML were hours spent on a file Google never asked for. Mine included.

**So nothing is misconfigured.** Not the sitemap, not `robots.txt`, not the canonicals, not the titles.
All verified clean. The site has no crawl demand, because almost nothing links to it, and an invitation
does not help when the guest has stopped coming.

The only thing that brings Googlebot back is links from hosts it crawls daily. Not a setting, and not a
button in Search Console. This is why the manual "request indexing" calls are worth making — each one
is a per-URL invitation that bypasses crawl budget — and why Bing, which accepted all 135 URLs through
IndexNow, is currently the more useful index for us.

**Done the same day:** the `agora` README now links six published pages (it linked none), which also
gives the leaderboard and comparison pages their first inbound path; the root repo's homepage field is
set. Both are nofollow and pass no authority — they are discovery paths, recorded as such and not as a
fix.

## 4c. It is not our sitemap. It is the whole host.

*Added after verifying `https://dancenitra.github.io/` as a second property on 2026-08-23.*

The root property lists **four sitemaps, across three projects, submitted on four different dates**,
and every one of them reads the same:

| sitemap | submitted | status | discovered | last read |
|---|---|---|---|---|
| `/sitemap.xml` | 2026-08-23 | Nie je možné načítať | 0 | — |
| `/agora/sitemap.xml` | 2026-08-23 | Nie je možné načítať | 0 | — |
| `/danchi/sitemap.xml` | 2026-08-05 | Nie je možné načítať | 0 | — |
| `/inspeximus/sitemap.xml` | 2026-07-30 | Nie je možné načítať | 0 | — |

Four files, three projects, four dates, one failure. **So it was never the agora sitemap**, and every
hour spent inside that file was spent in the wrong place — including several of mine.

Everything on our side is now ruled out, with receipts:

| candidate | result |
|---|---|
| sitemap content | spec-clean on nine checks |
| fetchability | 20/20 HTTP 200, plus HEAD, gzip, no-UA, Googlebot UA, HTTP/1.1 |
| GSC's own live URL test | "stránka je k dispozícii" |
| root `robots.txt` | read in full, **no `Disallow` anywhere** |
| homepage `<base>` / `meta robots` / `nofollow` | none / none / **0 of 50 internal links** |
| homepage HTML | complete, `</html>` present, self-canonical |
| **all four GitHub Pages edge nodes** | `185.199.108–111.153` each serve `/sitemap.xml`, `/agora/sitemap.xml` and `/robots.txt` at **200** |
| host root 404 | fixed — a sitemap index now lives at `https://dancenitra.github.io/sitemap.xml` |

**The one path I could not test is IPv6.** The host has AAAA records (`2606:50c0:8000–8003::153`,
confirmed by an authoritative DoH lookup, not by this machine's resolver) and Google prefers IPv6 when
it is available. GitHub Pages IPv6 serves millions of sites, so this is unlikely — but it is the only
technical unknown left, and I am recording it as untested rather than as cleared.

**The most probable remaining explanation is not technical.** A sitemap is a hint, not an instruction.
For a host with essentially no inbound links, Google assigns near-zero crawl budget and is free to
never fetch the hint at all — which matches every number here: three URLs discovered in eight weeks,
an index count decaying 3 → 2 → 1, and four sitemaps sitting unread across three projects.

**The screen that settles it: Nastavenia → Štatistiky prehľadávania (Crawl stats).** It reports total
crawl requests to this host over 90 days. Near zero confirms crawl budget and closes this line of
investigation for good; a healthy number means something else is wrong and we look again.

If it is crawl budget, then S1d — external links — is not one item on the list. It is the whole list.

## 4b. What did change, and how confident I am
*(Written before the coverage export arrived. §4 above corrects it: the Jul-25 hit is real and still
unexplained, but the August collapse is a separate deindexing event, and the dominant fact — that only
three URLs were ever discovered — is not about the rebrand at all.)*

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

### S0 — DONE. Answer: 3 of 135 URLs discovered, 1 indexed
See §4. The pages are not "indexed and not ranking" and not "crawled and rejected" — they were never
found. This kills S2 and S4 as first moves and makes everything below about discovery.

### S0b — Is Google reading our sitemap at all? *(blocking, 2 minutes, owner)*
**Search Console → Indexovanie → Sitemapy.** For `sitemap.xml` and `sitemap_index.xml`, report back
three things: the **status** (Úspešné / Nie je možné načítať / Má chyby), the **date last read**, and
the **"Zistené stránky"** count.

A valid sitemap listing 135 URLs that yields 3 discovered URLs in eight weeks is either not being
fetched, or being fetched and rejected. Those have different fixes and the screen says which.

I verified everything on our side today, so the failure is not in the file:

| check | result |
|---|---|
| `sitemap.xml` HTTP | 200, `application/xml`, 19,912 bytes, no BOM |
| XML well-formed | yes, correct `sitemaps.org/schemas/sitemap/0.9` namespace |
| `<loc>` entries | 135, all absolute `https://` URLs matching the property prefix |
| `<lastmod>` | 125 entries, **0 malformed** |
| `sitemap_index.xml` | 200, valid, points at `sitemap.xml` |
| root `robots.txt` | 200, `Allow: /`, declares both sitemaps |
| `X-Robots-Tag` header | **absent** on homepage, posts index and sitemap |
| crawl path from home | 25 unique internal `<a>` links, including the posts index and 14 posts |

**If the status is "Nie je možné načítať":** resubmit both, and if it persists the working alternative
is the account-root sitemap declaration plus Bing/IndexNow, which we already have a key for.

### S1 — Earn discovery and crawl demand *(the actual work)*
Discovery has two channels and both are currently producing nothing. Work them in this order.

**S1a — force the first URLs in by hand (today, owner, ~20 minutes).**
Search Console → **Kontrola adresy URL** (URL Inspection) → paste a URL → **Požiadať o indexovanie**.
There is a daily quota of roughly ten, so this is not how 135 pages get indexed — it is how we find
out whether Google will accept *any* of them, and it seeds the crawler with a starting set.
Pick these first, because they are the pages worth ranking and the ones other things link to:

1. `https://dancenitra.github.io/agora/public/posts/` — the index, because it links to every post
2. `https://dancenitra.github.io/agora/public/crucible/`
3. `https://dancenitra.github.io/agora/public/leaderboard/`
4. `https://dancenitra.github.io/agora/public/compare/`
5. `https://dancenitra.github.io/agora/public/posts/verifiable-agent-receipts.html` — the topic of our
   only real query, *"zero proof ai mcp receipts"*, 63 impressions at position 8.48

**Read what the inspection says before requesting.** "URL nie je v službe Google" plus "Zistenie:
Adresa URL nie je v žiadnej mape stránok" would mean the sitemap is not connected to this property at
all, which is S0b's answer arriving from the other side.

**S1b — IndexNow, for Bing and everything downstream of it.**
We already have the key file (`104dc9a7a9aa51c3cfd78e6a87842424.txt`) at the account root, and a
previous submission of 125 agora URLs was accepted (HTTP 202). Bing feeds ChatGPT search, so this is
worth doing on its own merits and it is a second, independent discovery channel that does not depend
on whatever is wrong with the Google sitemap. Re-submit the current 135.

**S1c — the three orphans and the thin internal links.**
`/public/leaderboard/`, `/public/compare/` and `/agora/sk/public/posts/` have zero inbound internal
links; 37 pages have exactly one. Every post should be two clicks from the home page and linked from
at least two siblings on the same topic. Cheap, and it is what turns one indexed page into a crawl
path.

**S1d — external links, the only real lever.**
A `github.io` subdirectory with no inbound links gets almost no crawl budget, and that is the whole
story of "3 URLs discovered in eight weeks". The sources we already own and do not use:
the DeepSeek-V3, claude-code, CML, memex and RAMR threads where our work is cited by name; the Zenodo
DOI; PyPI. **Every one of them currently points at a repository, never at a post.** The next time we
cite our own work in a thread, cite the page, not the repo.

**Expected effect:** S1a and S1b can change the number this week. S1d is what makes it stay changed,
and it is slow — weeks.

### S2 — Query targeting *(after discovery, not before)*
Deferred, and the reason is §4: you cannot rank a page Google has not found. Keeping the analysis
because it is still true and it decides what we do once pages exist in the index.

The single biggest query is **"zero proof ai mcp receipts"** — 63 impressions at position 8.48, a
problem-shaped phrase. Second is **"crucible ai"**, 20 impressions at position 58.85. Everything else
is one impression each, including three junk matches for other products called Agora.

Meanwhile our titles read like this:
- *"We looked for the grounding 'tipping point' in AI self-training…"* (119 chars)
- *"A reality-check on agent-memory poisoning defenses: you pric…"* (102)
- *"The same classical tradeoff in four AI-memory mechanisms — a…"* (86)

These are essay titles. They are good essay titles. Nobody searches them.
- Pick **five** queries with real volume that our existing work already answers, and build or retitle
  one page each. We have no keyword-volume data in-house — this needs a source.
- The page that already ranks at position 8.48 gets **zero clicks**. Once discovery is fixed, that is
  the cheapest CTR win on the site.

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

### S6 — Measure the right number, monthly
At 1.5 impressions a day, week-to-week movement is noise. A single query drifting three positions
moves the percentage more than anything we do. Review on a **monthly** cadence against the two numbers
that matter, both currently zero: *pages with at least one impression* (3 of 135) and *external
clicks* (0).

---

## What I would do first

**S0b and S1a today**, in that order, both in Search Console and both the owner's hands: read the
Sitemaps screen, then request indexing on the five URLs in S1a. Between them they answer the only
question left — *will Google take our pages at all* — and they take under half an hour.

**S1b this week** — resubmit the 135 URLs to IndexNow. Independent of whatever is wrong on the Google
side, and Bing is what ChatGPT search reads.

Then **S1d**, which is the only durable item on the list and the one that overlaps with
`PLAYBOOK_DISTRIBUTION.md`: the GitHub threads where our work is already cited are the only external
signal we own, and every one of them points at a repository instead of at a page. That is free to fix
and we control it entirely.

The on-page work — S3, S4 — is a day's scripting and should be done, but nobody should expect it in
the numbers. It is hygiene on 132 pages Google has never seen.

**Track one number, weekly, and only this one until it moves:** *URLs Google knows about*. It has been
3 since 2026-07-01. Impressions, positions and CTR are downstream of it and reading them first is what
produced the wrong diagnosis in §4b.

**And one thing not to do:** do not revert the July SEO work. It is measurably correct on the live
site, and rolling it back would trade a clean technical layer for a hypothesis I have already said
cannot be proven at this volume.

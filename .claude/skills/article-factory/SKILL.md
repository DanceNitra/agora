---
name: article-factory
description: The one procedure for taking a research finding to a published Agora article (EN and SK, in the sitemap), a Reddit-ready version, an English "Echoes of Tomorrow" podcast episode built on NotebookLM deep research, and the episode's text promo for X and LinkedIn. Use when the owner says "urob z toho clanok", "sprav podcast", "priprav to na Reddit", "Publish article", when an inbox task of kind "Publish article" appears, or when an existing post is to be deepened and re-issued. Deep research runs BEFORE the article, so the article is the best version of itself; then the standing gate (VALIDATE, storm-research, stress-claim, verify-claims, humanizer last); then tools/derive_post.py and tools/podcast_episode.py for the mechanics. Built 2026-09-17 from agora_output/content_engine_plan_2026-09.md; reordered the same day on the owner's instruction.
argument-hint: "<slug of public/posts/src/<slug>.en.md, or the finding in one sentence>"
---

# article-factory: finding -> deep research -> article (EN, SK) -> Reddit -> podcast -> promo

The order is the owner's (2026-09-17): the NotebookLM deep research runs first, so the article
that goes under Agora is the best version we can write. Then the article is gated and published
in English and Slovak, the way every Agora post is, and registered in the sitemap. Only then do
the derivatives exist: the Reddit version, the English podcast episode, and the episode's promo.

Every derivative repeats only what the published article carries. `tools/derive_post.py check`
enforces that with numbers, links and names. Material from the deep research enters the article
in step 3, through `verify-claims`, and nowhere else.

Each numbered step below is its own step. A step written as a clause inside another step is the
shape of thing that gets skipped (audit-post, 2026-07-01, twice in one day). Do not merge them.

Cost notice, before steps 1, 3, 7a, 7b, 7c: tell the owner what runs, how many units and the
total (storm about 470k tokens, stress-claim about 420k, verify-claims per claim count), and
wait for his go-ahead. Owner rule of 2026-08-21. NotebookLM steps cost his plan quota, not
tokens; `nlm usage` shows what is left.

## 0. Select and score the topic

Inputs: the Canon, the Crucible ledger, Lab receipts, the Flywheel's open questions, the inbox,
`GET /brain/board` (`priorities`). Three questions, each yes or no:
1. Is there a measured number, a failed replication, or a result that contradicts a common belief?
2. Does a stranger with no context understand the first sentence?
3. Is it on the board and not textbook?
Three yes is a candidate. Two or fewer is not an article. Write the score and the reason into
`agora_output/distribution/content_ledger.jsonl` (one JSON line: slug, date, score, reason).

For an EXISTING post being re-issued, the score still runs: an old post can have fallen off the
board or become textbook since it shipped.

## 1. Skeptic first, before any draft

Run `stress-claim` on the claim and its measurement, not on prose. Hand it the probe and the
target. KILL or REFUTED means there is no draft and the ledger row says why. Standing rule of
2026-08-17.

## 2. Deep research in NotebookLM

```bash
python -X utf8 tools/derive_post.py init <slug>        # for an existing post; freezes its sha
python -X utf8 tools/podcast_episode.py research <slug> [--query "<the claim>"]
```
About five minutes, about 40 web sources, a new notebook "Echoes of Tomorrow: <slug>", the
existing article (if any) added as a source. The notebook id lands in
`agora_output/episodes/<slug>/episode.json`. The NotebookLM page does not refresh itself; the
owner presses F5 to see the notebook.

Read the notebook: through the `notebooklm-mcp` MCP tools (after a session restart), or
`nlm source list <nb> --json`, `nlm report create <nb> -f "Briefing Doc" -y` and
`nlm download report <nb>`. Read every source the research imported, not the briefing alone.
Pick what makes the article better: prior art we missed, the strongest counter, the one number
that changes the picture, a live thread that asks our question.

## 3. Verify what the research adds

Everything picked is NEW material. `verify-claims` on it against primary sources (`WebFetch`
each one). Write only what survived into `agora_output/derivatives/<slug>/verified_context.md`,
with the source URL beside each item, and record the receipt:
```bash
python tools/humanizer_receipt.py record agora_output/derivatives/<slug>/verified_context.md --skill verify --in-session
```
`derive_post.py check` refuses a context file whose bytes have no verify receipt.

## 4. Draft the article, English and Slovak

Write `public/posts/src/<slug>.en.md` and `public/posts/src/<slug>.sk.md` (for a re-issue,
edit both), in Google developer style, using the article's own findings and
`verified_context.md`. Fixed shape:
- First sentence: the number or the failure. No setup.
- Second paragraph: what we did, in the order we did it.
- One table or one figure.
- The falsifier: what result would have proved us wrong.
- The probe link: `research/probes/<name>.py`, public, self-contained, prints every number.
- Under 1,200 words. The long form, if any, stays on the storefront.
Do not run the humanizer here. It runs once, last, in step 8c.

## 5. VALIDATE

Re-run every probe behind every number this cycle. Then:
```bash
python -X utf8 tools/publish_gate.py public/posts/src/<slug>.en.md
```
A number that does not reproduce is corrected in the draft, never explained around.

## 6. Freshness

The cited papers still say what we cite, the tools and versions named still exist, the
competitor claims still hold. `WebFetch` each primary source. Anything stale is fixed in the
draft before the storm, so the storm reviews the true text.

## 7. The gate, in order

### 7a. STORM
`storm-research` on the article's claim. Dominant, never skipped, on every article and every
re-issue (owner, 2026-07-01). Read the contradiction map and fix the draft.

### 7b. AUDIT
`stress-claim` on the draft. PUBLISH, REFRAME or KILL. REFRAME means edit and rerun 7b.

### 7c. VERIFY
`verify-claims` on the draft: every number against its artifact, every citation against its
primary source. Record the receipts:
```bash
python tools/humanizer_receipt.py record public/posts/src/<slug>.en.md --skill verify --in-session
python tools/humanizer_receipt.py record public/posts/src/<slug>.en.md --skill redteam --in-session
```

## 8. Publish under Agora

### 8a. Render
Add the post's entry to `META` in `tools/render_post.py` (a re-issue updates `modified`), then:
```bash
python -X utf8 tools/render_post.py
python -X utf8 tools/render_sitemap.py
```
(`render_post.py` takes no slug; it renders every `META` entry, EN and SK on one page with the
toggle, and rebuilds the index and the sitemap.)

### 8b. Commit and push
Commit the sources, the HTML, the sitemap. Push to Pages. Submit the URL to IndexNow and
request indexing in Search Console, so Google finds it.

### 8c. Humanizer, once, last
The `humanizer` SKILL on the EN source, then the receipt:
```bash
python tools/humanizer_receipt.py record public/posts/src/<slug>.en.md --in-session
```
If the humanizer changed the text, mirror the change in the SK source, re-render (8a), commit
again. Never a script in place of the skill; never a second pass (owner, twice).

### 8d. Freeze
```bash
python -X utf8 tools/derive_post.py init <slug> --refreeze
```
Every derivative from here names this sha.

## 9. Derivatives

Write in `agora_output/derivatives/<slug>/`, from the article and `verified_context.md` only:
- `reddit/<subreddit>.md`, one per target from `tools/distribution_radar.py`. A live thread
  beats a self-post. No self-post where we hold no karma. Under 250 words. The link last or
  absent. Never the same text in two subreddits. The owner pastes it himself.
- `episode.md`: `## Title`, `## Description` (with the article and probe links),
  `## Chapters`, `## Focus` (what the hosts must cover and which numbers; the audio is generated
  from this string).
Then:
```bash
python -X utf8 tools/derive_post.py check <slug>
```
Every derivative that goes outward gets the `humanizer` SKILL and its receipt, keyed to its own
bytes. A derivative edited after the pass has no receipt.

## 10. The episode, in English

```bash
python -X utf8 tools/podcast_episode.py all <slug> --cover agora_output/episodes/<slug>/cover.png
```
That is: audio overview from the deep-research notebook (`deep_dive` by default; `critique` or
`debate` when the article has a strong counter), download, faster-whisper transcript, the
transcript check, ffmpeg mastering to -16 LUFS AAC 128k, and `spotify.md`. A transcript with a
number the article and the verified context do not carry FAILS, and `master` refuses.
Regenerate with a narrower `## Focus`, or cut the segment. No clean transcript, no episode.

Cover: generated per episode with an image model under the restraint rules (flat, typographic,
no emoji, no brain, no gradient blob, no glow), 3000 x 3000 PNG at
`agora_output/episodes/<slug>/cover.png`. The owner sees the rendered image before it ships.

## 11. Promo for the episode

In `agora_output/derivatives/<slug>/`, from the article and the episode only:
- `x.md`: three to five posts, the first is the number, the last carries the episode link.
- `linkedin.md`: 120 to 200 words, the episode link and the article link.
- an OG image for the article at 1200 x 630, same restraint rules, if the post has none.
`derive_post.py check <slug>` again, then the `humanizer` SKILL and receipts on each.

## 12. Brief the owner, once, in Slovak

One Telegram message: the claim in one line, the article URL, the Reddit title and body ready
to paste, where `spotify.md` and the cover are, the X and LinkedIn text. He pastes Reddit,
uploads the episode in the browser from `spotify.md` and checks every field, and taps approval
for X and LinkedIn. Nothing goes outward before that.

## 13. Ledger

Append the row: slug, article sha, gate verdicts, notebook id, episode artifact, derivative
files, channels, timestamps. The weekly metric read fills in clicks, impressions, plays and
comments later.

## What this skill does not do

It does not decide what is interesting; steps 0 and 1 do, and the owner's board outranks both.
It does not post anywhere. It does not let a podcast say a number the article never did.

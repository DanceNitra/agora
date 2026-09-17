---
name: article-factory
description: The one procedure for taking a research finding to a published Agora article, a Reddit-ready version, a NotebookLM-deepened "Echoes of Tomorrow" podcast episode, and X and LinkedIn posts. Use when the owner says "urob z toho clanok", "sprav podcast", "priprav to na Reddit", "Publish article", when an inbox task of kind "Publish article" appears, or when an existing post is to be deepened and re-issued. Chains the existing skills in a fixed order (stress-claim first, then VALIDATE, storm-research, stress-claim, verify-claims, humanizer last) and the two scripts that do the mechanics (tools/derive_post.py, tools/podcast_episode.py). Built 2026-09-17 from agora_output/content_engine_plan_2026-09.md.
argument-hint: "<slug of public/posts/src/<slug>.en.md, or the finding in one sentence>"
---

# article-factory: finding -> article -> Reddit -> deep research -> podcast -> social

One gated article is the source. Every derivative repeats only what the article passed through
the gate, and `tools/derive_post.py check` enforces that with numbers, links and names. New
material arrives only through one door, the NotebookLM deep research in step 6, and only after
`verify-claims` passed on it.

Each numbered step below is its own step. A step written as a clause inside another step is the
shape of thing that gets skipped (audit-post, 2026-07-01, twice in one day). Do not merge them.

Cost notice, before steps 3, 5a, 5b, 6d: tell the owner what runs, how many units and the total
(storm about 470k tokens, stress-claim about 420k, verify-claims per claim count), and wait for
his go-ahead. Owner rule of 2026-08-21.

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

## 2. Draft the article

Write `public/posts/src/<slug>.en.md` (and `.sk.md`), in Google developer style. Fixed shape:
- First sentence: the number or the failure. No setup.
- Second paragraph: what we did, in the order we did it.
- One table or one figure.
- The falsifier: what result would have proved us wrong.
- The probe link: `research/probes/<name>.py`, public, self-contained, prints every number.
- Under 1,200 words. The long form, if any, stays on the storefront.
Do not run the humanizer here. It runs once, last, in step 5e.

## 3. VALIDATE

Re-run every probe behind every number this cycle. Then:
```bash
python -X utf8 tools/publish_gate.py public/posts/src/<slug>.en.md
```
A number that does not reproduce is corrected in the draft, never explained around.

## 4. Freshness

Check the article is current: the cited papers still say what we cite, the tools and versions
named still exist, the competitor claims still hold. `WebFetch` each primary source. Anything
stale is fixed in the draft before the storm, so the storm reviews the true text.

## 5. The gate, in order

### 5a. STORM
`storm-research` on the article's claim. Dominant, never skipped, on every article and every
re-issue (owner, 2026-07-01). Read the contradiction map and fix the draft.

### 5b. AUDIT
`stress-claim` on the draft. PUBLISH, REFRAME or KILL. REFRAME means edit and rerun 5b.

### 5c. VERIFY
`verify-claims` on the draft: every number against its artifact, every citation against its
primary source. Record the receipt:
```bash
python tools/humanizer_receipt.py record public/posts/src/<slug>.en.md --skill verify --in-session
python tools/humanizer_receipt.py record public/posts/src/<slug>.en.md --skill redteam --in-session
```

### 5d. Render and publish
Add the post's entry to `META` in `tools/render_post.py`, then:
```bash
python -X utf8 tools/render_post.py
python -X utf8 tools/render_sitemap.py
```
(`render_post.py` takes no slug; it renders every `META` entry and rebuilds the index.)
Commit, push to Pages, IndexNow. The article's sha256 is frozen now:
```bash
python -X utf8 tools/derive_post.py init <slug>
```

### 5e. Humanizer, once, last
The `humanizer` SKILL on the article, then the receipt:
```bash
python tools/humanizer_receipt.py record public/posts/src/<slug>.en.md --in-session
```
If the humanizer changed the text, re-render (5d) and `derive_post.py init <slug> --refreeze`.
Never a script in place of the skill; never a second pass (owner, twice).

## 6. Deepen in NotebookLM

### 6a. Deep research
```bash
python -X utf8 tools/podcast_episode.py research <slug>
```
About five minutes, about 40 web sources, a new notebook titled "Echoes of Tomorrow: <slug>",
the published article added as a source. The notebook id lands in
`agora_output/episodes/<slug>/episode.json`.

### 6b. Read the notebook
Through the `notebooklm-mcp` MCP tools (after a session restart) or `nlm source list <nb>`,
`nlm report create <nb>` and `nlm download report`. Pick what deepens the piece: prior art we
missed, the strongest counter, the one number that changes the picture, a live thread that asks
our question.

### 6c. Verify what you keep
Everything picked is NEW material. `verify-claims` on it against primary sources. Write only what
survived into `agora_output/derivatives/<slug>/verified_context.md`, with the source URL beside
each item, and record the receipt:
```bash
python tools/humanizer_receipt.py record agora_output/derivatives/<slug>/verified_context.md --skill verify --in-session
```
`derive_post.py check` refuses a context file whose bytes have no verify receipt.

### 6d. Feed it back into the article
If the deep research changed what the article says (a missed counter, a wrong number, a better
example), edit the article and go back to step 3. A derivative may not be deeper than its
source. If it only adds context for the episode, continue.

## 7. Derivatives

Write in `agora_output/derivatives/<slug>/`, from the article and `verified_context.md` only:
- `reddit/<subreddit>.md`, one per target from `tools/distribution_radar.py`. A live thread
  beats a self-post. No self-post where we hold no karma. Under 250 words. The link last or
  absent. Never the same text in two subreddits. The owner pastes it himself.
- `x.md`: three to five posts, the first is the number.
- `linkedin.md`: 120 to 200 words.
- `episode.md`: `## Title`, `## Description` (with the article and probe links),
  `## Chapters`, `## Focus` (what the hosts must cover and which numbers; the audio is generated
  from this string).
Then:
```bash
python -X utf8 tools/derive_post.py check <slug>
```
Every derivative that goes outward gets the `humanizer` SKILL and its receipt, keyed to its own
bytes. A derivative edited after the pass has no receipt.

## 8. The episode

```bash
python -X utf8 tools/podcast_episode.py all <slug> --cover agora_output/episodes/<slug>/cover.png
```
That is: audio overview (`deep_dive` by default; `critique` or `debate` when the article has a
strong counter), download, faster-whisper transcript, the transcript check, ffmpeg mastering
to -16 LUFS AAC 128k, and `spotify.md`. A transcript with a number the article and the verified
context do not carry FAILS, and `master` refuses. Regenerate with a narrower `## Focus`, or cut
the segment. No clean transcript, no episode.

Cover: generated per episode with an image model under the restraint rules (flat, typographic,
no emoji, no brain, no gradient blob, no glow), 3000 x 3000 PNG at
`agora_output/episodes/<slug>/cover.png`. The owner sees the rendered image before it ships.

## 9. Brief the owner, once, in Slovak

One Telegram message: the claim in one line, the Reddit title and body ready to paste, the
X and LinkedIn text, the episode title and where `spotify.md` is. He pastes Reddit, uploads the
episode in the browser from `spotify.md` and checks every field, and taps approval for X and
LinkedIn. Nothing goes outward before that.

## 10. Ledger

Append the row: slug, article sha, gate verdicts, derivative files, episode artifact, channels,
timestamps. The weekly metric read fills in clicks, impressions, plays and comments later.

## What this skill does not do

It does not decide what is interesting; steps 0 and 1 do, and the owner's board outranks both.
It does not post anywhere. It does not let a podcast say a number the article never did.

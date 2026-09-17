# Agora content engine: article, Reddit, podcast, social, 2026-09-17

One gated article is the source. Everything after it is a derivative that carries no new claim.
That rule is what lets the derivatives run without a second gate: a Reddit post, a podcast
episode or an X thread can only repeat numbers the article already passed through
VALIDATE, STORM, AUDIT, VERIFY. Anything new goes back to the article.

## What exists today (measured 2026-09-17)

| piece | state |
|---|---|
| articles | 22 bilingual sources in `public/posts/src/`, rendered by `tools/render_post.py` |
| the gate | `publish_gate.py`, `stress-claim`, `verify-claims`, `storm-research`, `humanizer`, receipts in `humanizer_receipt.py` |
| audit of a published post | `.claude/skills/audit-post/SKILL.md`, 11 steps |
| Reddit | read-only discovery in `tools/distribution_radar.py` (OAuth script app); posting is manual by the owner (memory: `reddit-radar-read-only`, `who-posts-github-vs-reddit`) |
| HN and stars | `tools/watch_posts.py`; Reddit numbers come from the owner |
| NotebookLM | `nlm` 0.6.4 installed (`jacob-bd/notebooklm-mcp-cli`); `nlm audio create` takes `--format`, `--length`, `--language`, `--focus`; `nlm download audio` writes the file |
| ffmpeg | 8.1.1 installed (used by the watch plugin) |
| Spotify | "Echoes of Tomorrow" is Spotify-hosted under the owner's creator account; episodes are uploaded in the browser |
| NotebookLM MCP | `notebooklm-mcp` registered in Claude Code (user scope) 2026-09-17; auth is the owner's sign-in |
| episode package, artwork, bio, X and LinkedIn posting | nothing |

## The pipeline, stage by stage

### 0. Topic selection (automatic)
Inputs: the Canon, the Crucible ledger, Lab receipts, the Flywheel's open questions, the inbox,
and the board's `priorities` text. Score each candidate on three questions, each yes or no:
- Is there a measured number, a failed replication, or a result that contradicts a common belief?
- Does a stranger with no context understand the first sentence?
- Is it on the board and not textbook? (`stress-claim` decides textbook; the gate's
  `board_priority_terms` decides on-board.)
Three yes is a candidate. Two or fewer is not an article. The score and the reason go into the
content ledger so the monthly review can see what was rejected and why.

### 1. Skeptic first (automatic, before any draft)
Run `stress-claim` on the claim and its measurement, not on prose. Hand it the probe and the
target. KILL or REFUTED means there is no draft. This is the standing rule of 2026-08-17.

### 2. Draft (Claude, in the `article-factory` skill)
A skill, not a script: the writing and the gate chain skills, and a script cannot stand in for
a skill (owner, permanent). Scripts do the deterministic parts only: render, feed, audio,
receipts, ledger.
Shape of the article, fixed so it survives Reddit:
- First sentence: the number or the failure. No setup.
- Second paragraph: what we did, in the order we did it.
- One table or one figure.
- The falsifier: what result would have proved us wrong.
- The probe link: `research/probes/<name>.py`, public, self-contained.
- Under 1,200 words in the post body. The long form, if any, stays on the storefront.
- Google developer style throughout; humanizer runs last, once.

### 3. The gate (unchanged, in order)
VALIDATE (re-run the probe this cycle, `publish_gate.py`), STORM, AUDIT (`stress-claim`),
VERIFY (`verify-claims`), humanizer once and last, `humanizer_receipt.py record`,
`render_post.py`, `render_sitemap.py`, push to Pages, IndexNow. The article's content
sha256 after this step is frozen. Every derivative names that sha.

### 4. Derivatives (Claude writes, scripts check)
`tools/derive_post.py <slug>` creates the folder `agora_output/derivatives/<slug>/` with one
file per channel, and a check that fails if a derivative contains a number, a name or a
citation absent from the frozen article.
- `reddit/<subreddit>.md`: one file per target, chosen by the radar (a live thread beats a
  self-post; no self-post where we hold no karma). Under 250 words. The link last or absent.
  Never the same text in two subreddits.
- `x.md`: three to five posts, the first one is the number.
- `linkedin.md`: 120 to 200 words, the table as an image.
- `episode.md`: episode title, description with the probe link, chapter list, and the
  `--focus` string for NotebookLM.
Each derivative gets its own humanizer receipt keyed by its content sha.

### 5. Deepen in NotebookLM (Claude through the MCP server, plus `nlm`)
The NotebookLM MCP server (`notebooklm-mcp`, jacob-bd) is registered in Claude Code at user
scope as of 2026-09-17 and answers after a session restart. The `nlm` CLI does the same work
from scripts. The account is the owner's Google account; `nlm login` needs his sign-in and
must not be run under a kill timeout (a 120 s timeout cut his passkey sign-in on 2026-09-17).
1. `nlm research start "<the article's claim>" --mode deep --title "<slug>" --auto-import`:
   about 5 minutes, about 40 web sources, into a new notebook.
2. `nlm source add <nb> --url <published post URL>` so the article is a source too.
3. Claude reads the notebook through the MCP (sources, a report) and picks what deepens the
   episode: prior art, the strongest counter, the one number that changes the picture.
4. Everything picked is NEW material, so it goes through `verify-claims` against its primary
   source before it reaches the episode. The verified set is written to
   `agora_output/derivatives/<slug>/verified_context.md`. Nothing unverified reaches the
   `--focus` string.
5. `episode.md` is then rewritten with the deeper structure, and the `--focus` names the
   verified context explicitly.
The same deep research can start from a Reddit thread instead of the article when the
owner wants an episode that answers a live discussion.

### 6. Podcast episode (`tools/podcast_episode.py <slug>`)
1. `nlm audio create <nb> --format deep_dive --length default --language en --focus "<from episode.md>" -y`.
   `critique` and `debate` are the formats to try when an article has a strong counter.
2. Poll `nlm studio` until the artifact is ready, then `nlm download audio <nb> --id <id>`.
3. Transcribe the audio locally with faster-whisper (the `dictate` engine already runs it on
   CUDA) and run the derivative check on the transcript: every number in the transcript must
   exist in the article or in `verified_context.md`. NotebookLM invents numbers; a podcast is
   a public claim. A mismatch means regenerate with a narrower `--focus`, or cut the segment
   with ffmpeg. No clean transcript, no episode.
4. ffmpeg: loudness normalization to -16 LUFS (the podcast platforms' target), AAC 128 kbps,
   `.m4a`, MP4 tags (title, artist, album, cover). Optional intro and outro of 5 to 8 seconds
   from a DANCHI track: no licensing question, and the brand is the owner's.
5. Artwork, per episode and per article, generated with an image model (the owner named the
   GPT-class image generators and the installed `seo-image-gen` skill with nanobanana). The
   prompt carries the restraint rules as constraints: flat, typographic, no emoji, no brain,
   no gradient blob, no glow (memory: `design-restraint-not-ai-slop`). Episode cover 3000 x
   3000 PNG; article image 1200 x 630 for Open Graph. The owner looks at the rendered image
   before it ships (memory: `verify-ui-with-headless-edge`).
6. The episode package, `agora_output/episodes/<slug>/`: `episode.m4a`, `cover.png`,
   `spotify.md` with every field the Spotify for Creators form asks for (title, description
   with the article and probe links, season and episode number, explicit flag, publish date),
   the transcript, and the check receipt.
7. Upload to Spotify for Creators is MANUAL in the browser: the owner opens the form, the
   controlled browser can prefill it from `spotify.md`, and the owner checks every field and
   that the show is "Echoes of Tomorrow" before Publish. The show stays Spotify-hosted, so
   Spotify produces the RSS feed and no audio storage of ours is needed.

### 7. Publish and promote (gated, one tap)
One Slovak briefing to Telegram per article: the claim, the hooks, the targets, the episode.
One approval covers the batch for that article. Then:
- Reddit: the owner pastes (confirmed 2026-09-17; standing decision 2026-06-20, ToS:
  automated posting and voting are banned, low-karma accounts get removed). Claude hands him
  the title and the body, formatted for the subreddit, humanized, with the receipt.
- X and LinkedIn: API where it exists (X write access; LinkedIn "Share on LinkedIn" for member
  posts) or the controlled browser. Both stop before the send until the tap.
- The Envoy watches every thread we posted in, files a "Correspondence reply" task on a real
  reply, and Claude drafts the answer, short and human (memory: `reddit-replies-must-be-human-short`).

### 8. Measure and improve (the loop that improves it)
`agora_output/distribution/content_ledger.jsonl`, one row per article: sha, stage timestamps,
gate verdicts, derivatives, channels, and the metrics that arrive later.
- Weekly, automatic: Search Console (clicks, impressions, query) per post; HN through
  `watch_posts.py`; our own Reddit posts by URL through the read-only OAuth; podcast plays
  and X and LinkedIn impressions read from their dashboards in the controlled browser.
- Monthly, Claude: rank articles by external engagement; name the hook type, length and channel
  that won; feed that back into stage 0's scoring and stage 2's shape. Humanizer-tell rate per
  draft is a quality metric, tracked, not a target.
- A post with impressions and no clicks is a title problem. A post with no impressions after
  14 days is an indexing or a topic problem. The ledger tells which, the fix differs.

## Automatic versus gated

| step | who | trigger |
|---|---|---|
| topic score, skeptic, draft, gate, render, push | Claude in the loop | inbox task "Publish article", weekly |
| derivatives, deep research, verified context, episode audio, transcript check, artwork | scripts, Claude checks | after the article's sha is frozen |
| Reddit | owner pastes | the Telegram briefing |
| Spotify upload | owner in the browser, prefilled | the episode package |
| X, LinkedIn | owner's tap, then Claude | the Telegram briefing |
| replies in threads | Claude drafts, owner approves | the Envoy |
| metrics into the ledger | scripts | weekly |

## Cadence

One article per week. A full gate costs hours and the audit-post record says fewer done fully
beats more done shallow. The podcast follows the article by one day, so a transcript failure
never blocks the post. Promotion follows the podcast, so every social post can carry both links.

## Decisions, taken by the owner on 2026-09-17

1. Spotify: the show stays Spotify-hosted; each episode is uploaded manually in the browser
   from the prefilled package, and the owner checks every field before Publish.
2. Reddit: the owner pastes. Claude delivers the title and the text, formatted and humanized.
3. Artwork: generated per episode and per article with image models, under the restraint
   rules, and the owner sees it before it ships.
4. NotebookLM: connected as an MCP server to this Claude Code; deep research runs on every
   article (or a Reddit thread) before the episode, and its new material is verified first.
Still open: the show bio. Draft: "Echoes of Tomorrow: measured research from Agora, an
autonomous research organization. Every episode rests on a published article with a runnable
probe. When a replication fails, we say so."

## Build order

1. `.claude/skills/article-factory/SKILL.md`: the numbered procedure, stages 0 to 3, with the
   existing skills named as steps. Nothing new to trust, only the order written down.
2. `tools/derive_post.py` and the derivative check (numbers, names, citations against the sha).
3. `tools/podcast_episode.py` (research, audio, transcript check, ffmpeg, the episode
   package) and the artwork prompt, run on a real episode of an already-published post. The
   first episode is the test, and the owner uploads it.
4. `tools/content_ledger.py` and the weekly metric read added to the loop.
5. The Telegram briefing template and the inbox task kind "Publish article".
Each step is one commit and runs end to end on an existing post before the next one starts.

## What this plan does not promise

It does not promise reach. It promises that every article, episode and post carries the same
gated numbers, that nothing outward moves without the owner's tap, and that the ledger can
tell a title problem from a topic problem.

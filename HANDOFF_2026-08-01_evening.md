# HANDOFF 2026-08-01, evening — three corrections I shipped, two of them to myself

Supersedes the parts of `HANDOFF_2026-08-01.md` that describe the morning. Read §0 and §1 first.

---

## 0. STATE, verified at handoff

Both servers up per `docs/GPU_MEASUREMENT_PROTOCOL.md`: brain ok (8 agents), dungeon 200, **one**
listener on `:8000`, **one** `mcp_server.py`, **zero** supervisors.

**The brain's reasoning tier was changed to `llama3.1:8b`** (was `qwen3:30b-a3b`). Backup of the
original at `server/.env.bak-reasoning-*`. Reason: the 30B takes 21.7 GB of a 24 GB card and starves
everything else. Revert is one line if the quality loss shows.

**`main` is at `e09d174`**, three pushes ahead of this morning. The integration branch is 93 commits
ahead of it and still unpushed.

---

## 1. READ THIS BEFORE MEASURING ANYTHING ON THE GPU

`docs/GPU_MEASUREMENT_PROTOCOL.md`. It exists because I re-derived the same problem six different
wrong ways in one afternoon. The three facts that cost the most:

* **Stop the BRAIN first, then the dungeon.** The brain owns `watch_dungeon_forever` and will
  relaunch the dungeon within ~5 minutes, silently restoring the contention.
* **`Stop-Process -Name ollama*` does NOT match `llama-server.exe`.** Seven orphaned runners had
  accumulated in a day, the oldest alive fifteen hours, holding 23.6 GB of 24 at 99% utilisation
  while `/api/ps` reported nothing loaded.
* **VRAM is 1.4–1.9x the download size**, so every sum from `ollama list` is low. `llama3.1:8b` is
  4.9 GB on disk and **9.2 GB** on the card.

Symptom that means contention rather than a bug: a small model times out at 90–420 s while
`/api/tags` answers in 0.2 s. `call_llm` has a 240 s timeout AND falls back across tiers, so one
logical call absorbs 12+ minutes silently before anything is raised.

---

## 2. What shipped, verified live

* **`eventstudyr#60`** — an issue proposing they print the minimum detectable pre-trend beside the
  pre-trend p-value they already print by default. Every claim verified against source at a pinned
  SHA. Watch for a reply; the repo is quiet (28 stars, last push 2026-04-01).
* **Two Crucible receipts rebuilt** and pointed at `probes/crucible_receipt_rebuild.py` instead of
  lab ids the ledger had dropped. Hot hand reproduces: −8.09pp at k=3 against a published −7.9,
  −17.87 at k=4 against −17, with two controls that can fail and did not.
* **Dunning-Kruger is now `NOT_RECOVERED`** on the card and in the post. See §4 — this took three
  attempts and two of them were wrong in public.

---

## 3. Aldric was reworked and his first assay was killed

`server/agora/execution/folklore.py`. The Oracle is retired: its book is behind a DNS filter that
returns a sinkhole even when 1.1.1.1 is asked directly, its forecasts mature over 21–120 days against
a daily bar, and its ledger measures anti-skill (z = −6.64 on 177 forecasts). He now pre-registers
P(REAL)/P(WEAK_MODEL_ARTIFACT)/P(REGIME_SPECIFIC)/P(HARMFUL) before a capability-gradient assay and
the computed verdict resolves it. Registered in **both** `swarm_health.LEDGERS` and
`repair_ledger._ORGANS`; the spec must use `primary="verdict"`, because with `primary="status"` a
resolved INCONCLUSIVE falls through to the repo-wide `_is_decisive` net and buys a green day.

**Assay #4 measured cleanly and was killed anyway.** Multi-agent voting at fixed cost loses on all
three rungs (−0.275 / −0.200 / −0.350 at n=40), verdict HARMFUL, frontier 95% CI [−0.530, −0.170].
Then the prior-art check killed it: **Sharma & Chopra, arXiv 2511.02309** answers the same question on
5 models and 3 benchmarks. Our distinguishing angle — advantage shrinking with capability — came out
NULL: monotone at n=15, inverted at n=40.

**The reusable lesson:** the probe header had a section titled "PRIOR ART, STATED UP FRONT" naming
Wang, Li and Snell, written from memory. Writing a prior-art section is not running a prior-art check.
Search for the question as a paper would title it, BEFORE spending the compute.

Backlog remaining: bitemporal-consolidation, forgetting-aids-creativity, rag-needs-reranking,
chain-of-thought-helps (known capability-dependent — cite the prior art or skip), more-context-is-better.

---

## 4. Three things I asserted today that were wrong

The shape is identical in all three: the arithmetic was right and the error was a storey up, in what
the numbers measured. Two were already public when they were caught.

1. **"No runnable artifact survived."** I checked `server/.lab.json` and the vault note, not
   `agora_output/lab/`, where the script was committed all along.
2. **"The Dunning-Kruger figures cannot be reproduced."** I ran the model at MY parameters, not the
   entry's. **Pushed live before it was caught.**
3. **"They reproduce at the recovered parameters."** Two free parameters fitted to three published
   anchors leaves no degrees of freedom, so the match COULD NOT HAVE FAILED. A fit to the number that
   must come out is not evidence. **Also pushed live before an adversarial panel caught it.**

The gate caught all three. I caught none of them.

---

## 5. A landmine in the publish path

**Re-running `tools/render_post.py` silently reverts post-render hand edits.**
`public/posts/ai-coding-productivity-operating-point.html` carries corrections dated 2026-07-23
(`~63% attrition`, `dateModified`) that are NOT in its `.md` source; a re-render rolled them back to
the June text. Caught in the diff and reverted, but only because the diff was read.

Of the 12 posts with a source, exactly **one** diverged substantively — the rest came back
whitespace-only. Before any `render_post.py` run, diff the output against the committed HTML and look
for anything that is not a trailing newline.

---

## 6. Open, in priority order

1. **A post on 44 of 58.** `public/crucible/crucible.json`: 44 of 58 entries have an **empty `code`
   field** — 76% of the public replication ledger ships no reader-runnable test, against its own
   stated premise. This is the honest, non-textbook story, and it is what a sharp reader finds by
   clicking one lab id. Owner was asked; not yet answered.
2. **The integration branch**, 93 commits, +18k lines, 36 of the files are new tests. Before merge:
   drop `gate.json` and `gate.err` from tracking — they are run artifacts. The 11 identical
   "WIP: batch unit interrupted" commits and 15 worktree merges are history noise; leave them, a
   rewrite of 93 commits is more risk than the tidiness is worth.
3. **Wren fails the daily bar** with 0 decisive / 0 attributed / 0 grounded. Almost certainly because
   the system was down for an hour for the assay. Owner chose to keep the 24h window, so this refills
   on its own — re-check tomorrow rather than fixing it.
4. **GSC is dropping over ~10 days** and I have no access to diagnose it. The question that splits the
   diagnosis: impressions or clicks? Impressions falling is index/update; clicks falling on flat
   impressions is CTR.

---

## 7. Killed today, honestly

* **Folklore assay #4** — re-derives Sharma & Chopra 2511.02309.
* **"A citation is not a receipt"** — drafted, rendered, then killed by its own audit. Three
  load-bearing claims were false: `public/posts/` contains **zero** lab ids so our posts never cited
  them; every "dead id" piece is dated 30–50 days outside a 14-day ledger window so the metric had no
  discriminating power; and `server/.lab.json` is **gitignored**, so the ledger was never readable by
  anyone outside this repo — the receipts were uncheckable from day one, not from day ten. The general
  lesson was textbook besides (reference rot: Klein 2014, Jones 2016, Zittrain 2014; Software Heritage
  SWHID is ISO/IEC 18670:2025).
